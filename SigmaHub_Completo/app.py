import os
import time
import queue
import threading
import urllib.parse
from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename
import requests as http_requests

# Importando os módulos core que preparamos para o robô Selenium
from whatsapp_automation import ConfigService, ExcelService, AutomationEngine

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Estado Global na memória do servidor
log_queue = queue.Queue()
engine = AutomationEngine(log_queue)
excel_service = None
run_thread = None
is_running = False
stop_requested = False
was_stopped = False
last_params = None
progress_state = {"total": 0, "processed": 0, "pending": 0, "status": "Aguardando"}
current_attachment = None
current_excel = None


def _validate_number(raw_num):
    if raw_num is None: return None
    num = "".join(filter(str.isdigit, str(raw_num)))
    if not num: return None
    if 10 <= len(num) <= 11: num = "55" + num
    if len(num) < 12 or len(num) > 13: return None
    return num

def _run_automation(params, resume=False):
    global is_running, stop_requested, was_stopped, engine, progress_state, last_params

    is_running = True
    stop_requested = False
    was_stopped = False
    last_params = params

    progress_state["status"] = "Em andamento"

    progress_state["status"] = "Em andamento"

    # Inicia o motor se ainda não estiver pronto (garantia extra)
    log_queue.put(("Verificando Motor de Automação...", "INFO"))
    if not engine.start():
        log_queue.put(("Falha crítica: Motor WhatsApp não responde.", "ERROR"))
        is_running = False
        progress_state["status"] = "Erro"
        return
    
    log_queue.put(("Motor pronto. Iniciando disparos...", "INFO"))



    # Cria backup da planilha antes de iniciar (apenas no início, não ao retomar)
    if not resume:
        try:
            bkp = excel_service.create_backup()
            log_queue.put((f"Backup criado: {os.path.basename(bkp)}", "INFO"))
        except Exception as e:
            log_queue.put((f"Backup falhou (continuando): {e}", "WARN"))

    count = 0
    sheet = excel_service.sheet
    cols = excel_service.cols

    for row in range(2, sheet.max_row + 1):
        if stop_requested or count >= params['limit']:
            break

        # Lê status atual da linha
        status_val = str(sheet.cell(row=row, column=cols['status']).value).strip().upper()
        if status_val not in ('PENDENTE', 'NONE', '', 'NAN'):
            continue

        # Lê dados da linha
        nome = str(sheet.cell(row=row, column=cols['nome']).value or "Cliente").strip()
        raw_num = sheet.cell(row=row, column=cols['numero']).value
        empresa = ""
        if cols.get('empresa'):
            empresa = str(sheet.cell(row=row, column=cols['empresa']).value or "").strip()

        num = _validate_number(raw_num)
        if not num:
            excel_service.update_row(row, "INVALIDO", f"Número fora do padrão: {raw_num}")
            log_queue.put((f"[Linha {row}] {nome}: número inválido ({raw_num})", "WARN"))
            progress_state["pending"] = max(0, progress_state["pending"] - 1)
            continue

        # Marca como em processamento
        excel_service.update_row(row, "EM_PROCESSAMENTO")

        msg_cur = params['msg'].replace("{nome}", nome).replace("{empresa}", empresa)
        att = params.get('attachment', '')

        log_queue.put((f"[Linha {row}] Enviando para {nome} ({num[-4:]}...)...", "INFO"))

        try:
            if att and os.path.exists(att):
                res = engine.send_with_attachment(num, msg_cur, att)
            else:
                res = engine.send_message(num, msg_cur)
        except Exception as e:
            res = "ERRO"
            log_queue.put((f"Exceção na linha {row}: {e}", "ERROR"))

        if res == "SUCESSO":
            excel_service.update_row(row, "ENVIADO", sent=True)
            count += 1
            progress_state["processed"] += 1
            progress_state["pending"] = max(0, progress_state["pending"] - 1)
            log_queue.put((f"✔ {nome} — ENVIADO ({count}/{params['limit']})", "SUCCESS"))
        elif res == "INVALIDO":
            excel_service.update_row(row, "INVALIDO", "WhatsApp informou número inválido")
            log_queue.put((f"✘ {nome} — INVÁLIDO", "WARN"))
            progress_state["pending"] = max(0, progress_state["pending"] - 1)
        else:
            excel_service.update_row(row, "ERRO", "Falha técnica na entrega")
            log_queue.put((f"✘ {nome} — ERRO técnico", "ERROR"))
            progress_state["pending"] = max(0, progress_state["pending"] - 1)

        # Delay entre disparos
        if not stop_requested and count < params['limit']:
            import random
            delay = random.randint(params['min'], params['max'])
            log_queue.put((f"Aguardando {delay}s antes do próximo...", "INFO"))
            for _ in range(delay):
                if stop_requested:
                    break
                time.sleep(1)

    if stop_requested:
        log_queue.put(("Campanha pausada pelo usuário. Clique em RETOMAR para continuar.", "WARN"))
        progress_state["status"] = "Pausada"
        was_stopped = True
        # NÃO fecha o engine/Chrome para permitir retomada
    else:
        log_queue.put(("✔ Campanha finalizada com sucesso!", "SUCCESS"))
        progress_state["status"] = "Concluída"
        was_stopped = False
        if not params.get('keep_open', False):
            engine.stop()
        else:
            log_queue.put(("Navegador mantido aberto.", "INFO"))

    is_running = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload-excel', methods=['POST'])
def upload_excel():
    global excel_service, progress_state, current_excel
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and file.filename.endswith('.xlsx'):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        try:
            excel_service = ExcelService(path)
            current_excel = filename
            recovered = excel_service.recover_stuck_rows()
            if recovered:
                log_queue.put((f"{recovered} contatos recuperados para pendente", "WARN"))
            pending = excel_service.count_pending()
            
            progress_state = {"total": pending, "processed": 0, "pending": pending, "status": "Planilha Carregada"}
            return jsonify({"message": "File uploaded", "pending": pending, "filename": filename})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Invalid file type. Apenas .xlsx permitidos."}), 400

@app.route('/api/clear-excel', methods=['POST'])
def clear_excel():
    global excel_service, current_excel, progress_state
    if is_running:
        return jsonify({"error": "Não é possível remover durante uma campanha ativa."}), 400
    excel_service = None
    current_excel = None
    progress_state = {"total": 0, "processed": 0, "pending": 0, "status": "Aguardando"}
    log_queue.put(("Planilha removida. Pronto para nova campanha.", "INFO"))
    return jsonify({"message": "Planilha removida"})

@app.route('/api/upload-attachment', methods=['POST'])
def upload_attachment():
    global current_attachment
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        current_attachment = path
        return jsonify({"message": "Attachment saved", "filename": filename})
    return jsonify({"error": "Upload failed"}), 400
    
@app.route('/api/clear-attachment', methods=['POST'])
def clear_attachment():
    global current_attachment
    current_attachment = None
    return jsonify({"message": "Cleared"})

@app.route('/api/start', methods=['POST'])
def start_campaign():
    global is_running, run_thread
    if is_running:
        return jsonify({"error": "A campanha já está ativa"}), 400
    if not excel_service:
        return jsonify({"error": "É necessário enviar uma planilha .xlsx primeiro"}), 400
        
    data = request.json
    params = {
        "msg": data.get("msg", ""),
        "limit": int(data.get("limit", 100)),
        "min": int(data.get("min", 15)),
        "max": int(data.get("max", 30)),
        "keep_open": data.get("keep_open", False),
        "attachment": current_attachment
    }
    
    run_thread = threading.Thread(target=_run_automation, args=(params,))
    run_thread.daemon = True
    run_thread.start()
    
    return jsonify({"message": "Campanha iniciada com sucesso"})

@app.route('/api/stop', methods=['POST'])
def stop_campaign():
    global stop_requested
    if is_running:
        stop_requested = True
        return jsonify({"message": "Campanha sendo pausada..."})
    return jsonify({"message": "O sistema já está parado"})

@app.route('/api/resume', methods=['POST'])
def resume_campaign():
    global is_running, run_thread, was_stopped
    if is_running:
        return jsonify({"error": "A campanha já está ativa"}), 400
    if not was_stopped:
        return jsonify({"error": "Não há campanha pausada para retomar"}), 400
    if not excel_service:
        return jsonify({"error": "Planilha não está mais carregada"}), 400

    # Usa os mesmos parâmetros da última execução, com atualização do attachment
    data = request.json or {}
    params = last_params.copy() if last_params else {}
    if data.get("msg"):
        params["msg"] = data["msg"]
    if data.get("limit"):
        params["limit"] = int(data["limit"])
    if current_attachment:
        params["attachment"] = current_attachment

    was_stopped = False
    run_thread = threading.Thread(target=_run_automation, args=(params,), kwargs={"resume": True})
    run_thread.daemon = True
    run_thread.start()

    return jsonify({"message": "Campanha retomada com sucesso"})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "is_running": is_running,
        "was_stopped": was_stopped,
        "progress": progress_state,
        "attachment": os.path.basename(current_attachment) if current_attachment else None,
        "excel": current_excel
    })

@app.route('/api/connector', methods=['GET'])
def get_connector_status():
    try:
        # Consulta o motor Node.js sobre o status e QR
        resp = http_requests.get("http://127.0.0.1:3001/status", timeout=2).json()
        return jsonify(resp)
    except:
        return jsonify({"connected": False, "qr": None, "waiting": True})


@app.route('/api/logs')
def stream_logs():
    def generate():
        while True:
            try:
                msg, level = log_queue.get(timeout=0.5)
                safe_msg = msg.replace('\n', ' ')
                yield f"data: {level}|{safe_msg}\n\n"
            except queue.Empty:
                yield ": keep-alive\n\n"
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    import socket
    import sys
    import webbrowser
    
    # Previne crash caso rode no pythonw
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')

    print("Iniciando SigmaHub (Web Localhost)...")

    def get_local_ip():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def find_free_port(start=5050, end=5099):
        for p in range(start, end):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('0.0.0.0', p))
                    return p
            except OSError:
                continue
        return start

    port = find_free_port()
    local_ip = get_local_ip()
    url = f"http://{local_ip}:{port}"
    print(f"Porta livre encontrada: {port}")
    print(f"Acesse na rede local através do link: {url}")

    # Inicia o motor Node.js em background imediatamente
    threading.Thread(target=engine.start, daemon=True).start()

    # Thread auxiliar para abrir o navegador limpo assim que o server subir
    def open_browser():
        # Da um pequeno atraso para o motor Flask compilar e iniciar
        time.sleep(1.5)
        # Tenta conectar para ter certeza que subiu
        for i in range(10):
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=1):
                    break
            except OSError:
                time.sleep(0.5)
        
        # Abre no browser padrao
        webbrowser.open(f"http://127.0.0.1:{port}")

    threading.Thread(target=open_browser, daemon=True).start()

    # Roda o Flask na main thread, permitindo acesso na rede local
    app.run(port=port, host='0.0.0.0', debug=False, use_reloader=False)

