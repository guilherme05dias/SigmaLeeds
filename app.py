import os
import time
import queue
import threading
import asyncio
import webbrowser
import requests as http_requests

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from whatsapp_automation import AutomationEngine
from database import init_db
from database.services.campaign_service import (
    create_campaign, import_contacts_from_xlsx,
    get_pending_contacts, update_contact_status,
    get_campaign_stats, get_campaign_history,
    export_campaign_to_xlsx, reset_processing_contacts
)
from database.services.blacklist_service import (
    add_to_blacklist, is_blacklisted, detect_optout_keywords, get_blacklist
)
from database.services.config_service import get_config, set_config
from database.services.account_service import (
    get_all_accounts, update_account_status
)
from license.manager import check_license, get_current_plan_limits, activate_license
from api.models import (
    StartCampaignRequest, ImportContactsRequest,
    ActivateLicenseRequest, AddBlacklistRequest,
    SaveConfigRequest, CreateTemplateRequest
)
from database.services.template_service import create_template, get_all_templates, update_template, delete_template, render_template

app = FastAPI(title="ZapManager Pro", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

log_queue = queue.Queue()
engine = AutomationEngine(log_queue)
run_thread = None
is_running = False
stop_requested = False
was_stopped = False
last_params = None
progress_state = {"total": 0, "processed": 0, "pending": 0, "status": "Aguardando"}
current_attachment = None
current_excel = None
current_campaign_id = None
node_process = None

@app.on_event("startup")
async def startup():
    init_db()
    global node_process
    
    # Iniciar Node.js em background
    import subprocess
    import sys
    
    node_script = os.path.join(os.path.dirname(__file__), "whatsapp-motor", "server.js")
    if os.path.exists(node_script):
        flags = 0
        if os.name == 'nt':
            flags = 0x08000000  # CREATE_NO_WINDOW
        node_process = subprocess.Popen(
            ["node", node_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=os.path.dirname(node_script),
            creationflags=flags
        )

@app.on_event("shutdown")
async def shutdown_event():
    global node_process
    if node_process:
        try:
            node_process.terminate()
            node_process.wait(timeout=2)
        except:
            pass

def _validate_number(raw_num):
    if raw_num is None: return None
    num = "".join(filter(str.isdigit, str(raw_num)))
    if not num: return None
    if 10 <= len(num) <= 11: num = "55" + num
    if len(num) < 12 or len(num) > 13: return None
    return num

def _run_automation(campaign_id, params, resume=False):
    global is_running, stop_requested, was_stopped, engine, progress_state, last_params

    is_running = True
    stop_requested = False
    was_stopped = False
    last_params = params

    progress_state["status"] = "Em andamento"

    log_queue.put(("Verificando Motor de Automação...", "INFO"))
    if not engine.start():
        log_queue.put(("Falha crítica: Motor WhatsApp não responde.", "ERROR"))
        is_running = False
        progress_state["status"] = "Erro"
        return
    
    log_queue.put(("Motor pronto. Iniciando disparos...", "INFO"))

    import random

    if resume:
        reset_processing_contacts(campaign_id)

    pending_contacts = get_pending_contacts(campaign_id)
    count = 0
    
    for contact in pending_contacts:
        if stop_requested or count >= params['limit']:
            break

        row_id = contact['id']
        nome = contact['name'] or "Cliente"
        empresa = contact['company'] or ""
        raw_num = contact['phone']
        
        num = _validate_number(raw_num)
        if not num:
            update_contact_status(row_id, "INVÁLIDO", f"Número fora do padrão: {raw_num}")
            log_queue.put((f"[C-{row_id}] {nome}: número inválido ({raw_num})", "WARN"))
            progress_state["pending"] = max(0, progress_state["pending"] - 1)
            continue

        update_contact_status(row_id, "EM_PROCESSAMENTO")

        msg_cur = params['msg'].replace("{nome}", nome).replace("{empresa}", empresa)
        att = params.get('attachment', '')

        log_queue.put((f"[C-{row_id}] Enviando para {nome} ({num[-4:]}...)...", "INFO"))

        try:
            if att and os.path.exists(att):
                res = engine.send_with_attachment(num, msg_cur, att)
            else:
                res = engine.send_message(num, msg_cur)
        except Exception as e:
            res = "ERRO"
            log_queue.put((f"Exceção no envio: {e}", "ERROR"))

        if res == "SUCESSO":
            update_contact_status(row_id, "ENVIADO")
            count += 1
            progress_state["processed"] += 1
            progress_state["pending"] = max(0, progress_state["pending"] - 1)
            log_queue.put((f"✔ {nome} — ENVIADO ({count}/{params['limit']})", "SUCCESS"))
        elif res == "INVALIDO" or res == "INVÁLIDO":
            update_contact_status(row_id, "INVÁLIDO", "WhatsApp informou número inválido")
            log_queue.put((f"✘ {nome} — INVÁLIDO", "WARN"))
            progress_state["pending"] = max(0, progress_state["pending"] - 1)
        else:
            update_contact_status(row_id, "ERRO", "Falha técnica na entrega")
            log_queue.put((f"✘ {nome} — ERRO técnico", "ERROR"))
            progress_state["pending"] = max(0, progress_state["pending"] - 1)

        if not stop_requested and count < params['limit']:
            delay = random.randint(params['min'], params['max'])
            log_queue.put((f"Aguardando {delay}s antes do próximo...", "INFO"))
            import time
            for _ in range(delay):
                if stop_requested:
                    break
                time.sleep(1)

    if stop_requested:
        log_queue.put(("Campanha pausada pelo usuário. Clique em RETOMAR para continuar.", "WARN"))
        progress_state["status"] = "Pausada"
        was_stopped = True
    else:
        log_queue.put(("✔ Campanha finalizada com sucesso!", "SUCCESS"))
        progress_state["status"] = "Concluída"
        was_stopped = False
        if not params.get('keep_open', False):
            engine.stop()
        else:
            log_queue.put(("Navegador mantido aberto.", "INFO"))

    is_running = False

@app.get("/")
async def serve_index():
    return FileResponse("templates/index.html")

@app.get("/api/logs")
async def logs_stream():
    async def event_generator():
        while True:
            try:
                msg, level = log_queue.get_nowait()
                safe_msg = msg.replace('\n', ' ')
                yield f"data: {level}|{safe_msg}\n\n"
            except queue.Empty:
                await asyncio.sleep(0.5)
                yield ": keep-alive\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Compatibility with frontend
@app.post("/api/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    global current_campaign_id, progress_state, current_excel
    if not file.filename.endswith('.xlsx'):
        return JSONResponse({"error": "Invalid file type. Apenas .xlsx permitidos."}, status_code=400)
    
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(path, "wb") as f:
        f.write(await file.read())
        
    try:
        campaign_name = f"Campanha {file.filename} - {time.strftime('%Y%m%d%H%M')}"
        cid = create_campaign(campaign_name, "")
        if cid < 0:
            return JSONResponse({"error": "Erro ao criar campanha no banco de dados"}, status_code=500)
            
        res = import_contacts_from_xlsx(cid, path)
        if len(res["errors"]) > 0 and res["imported"] == 0:
            return JSONResponse({"error": "Falha total na importacao: " + str(res["errors"])}, status_code=400)
            
        current_campaign_id = cid
        current_excel = file.filename
        
        pending_count = len(get_pending_contacts(cid))
        
        progress_state = {"total": pending_count, "processed": 0, "pending": pending_count, "status": "Planilha Carregada"}
        return {"message": "File uploaded", "pending": pending_count, "filename": file.filename}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/clear-excel")
async def clear_excel():
    global current_campaign_id, progress_state, current_excel
    if is_running:
        return JSONResponse({"error": "Não é possível remover durante uma campanha ativa."}, status_code=400)
    current_campaign_id = None
    current_excel = None
    progress_state = {"total": 0, "processed": 0, "pending": 0, "status": "Aguardando"}
    log_queue.put(("Planilha removida. Pronto para nova campanha.", "INFO"))
    return {"message": "Planilha removida"}

@app.post("/api/upload-attachment")
async def upload_attachment(file: UploadFile = File(...)):
    global current_attachment
    if not file: return JSONResponse({"error": "No file"}, status_code=400)
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(path, "wb") as f:
        f.write(await file.read())
    current_attachment = path
    return {"message": "Attachment saved", "filename": file.filename}

@app.post("/api/clear-attachment")
async def clear_attachment():
    global current_attachment
    current_attachment = None
    return {"message": "Cleared"}

@app.post("/api/start")
async def legacy_start_campaign(request: Request):
    global is_running, run_thread
    if is_running:
        return JSONResponse({"error": "A campanha já está ativa"}, status_code=400)
    if not current_campaign_id:
        return JSONResponse({"error": "É necessário enviar uma planilha .xlsx primeiro"}, status_code=400)
        
    data = await request.json()
    
    # Validações de licença
    license_status = check_license()
    if license_status["status"] in ["expired", "invalid"]:
        return JSONResponse({"error": license_status["message"]}, status_code=400)
        
    limits = get_current_plan_limits()
    
    params = {
        "msg": data.get("msg", ""),
        "limit": int(data.get("limit", 100)),
        "min": int(data.get("min", 15)),
        "max": int(data.get("max", 30)),
        "keep_open": data.get("keep_open", False),
        "attachment": current_attachment
    }
    
    # Atualiza a mensagem na campanha real
    import sqlite3
    try:
        from database.schema import get_connection
        conn = get_connection()
        with conn:
            conn.execute("UPDATE campaigns SET message_template = ? WHERE id = ?", (params["msg"], current_campaign_id))
        conn.close()
    except: pass
    
    run_thread = threading.Thread(target=_run_automation, args=(current_campaign_id, params))
    run_thread.daemon = True
    run_thread.start()
    
    return {"message": "Campanha iniciada com sucesso"}

@app.post("/api/stop")
async def stop_campaign():
    global stop_requested
    if is_running:
        stop_requested = True
        return {"message": "Campanha sendo pausada..."}
    return {"message": "O sistema já está parado"}

@app.post("/api/resume")
async def legacy_resume_campaign(request: Request):
    global is_running, run_thread, was_stopped
    if is_running: return JSONResponse({"error": "A campanha já está ativa"}, status_code=400)
    if not was_stopped: return JSONResponse({"error": "Não há campanha pausada para retomar"}, status_code=400)
    if not current_campaign_id: return JSONResponse({"error": "Planilha não está mais carregada"}, status_code=400)

    data = await request.json()
    params = last_params.copy() if last_params else {}
    if data.get("msg"): params["msg"] = data["msg"]
    if data.get("limit"): params["limit"] = int(data["limit"])
    if current_attachment: params["attachment"] = current_attachment

    was_stopped = False
    run_thread = threading.Thread(target=_run_automation, args=(current_campaign_id, params,), kwargs={"resume": True})
    run_thread.daemon = True
    run_thread.start()

    return {"message": "Campanha retomada com sucesso"}

@app.get("/api/status")
async def get_status():
    st = {
        "is_running": is_running,
        "was_stopped": was_stopped,
        "progress": progress_state,
        "attachment": os.path.basename(current_attachment) if current_attachment else None,
        "excel": current_excel
    }
    return st

@app.get("/api/connector")
async def get_connector_status():
    try:
        resp = http_requests.get("http://127.0.0.1:3001/status", timeout=2).json()
        return resp
    except:
        return {"connected": False, "qr": None, "waiting": True}

# REST APIs Obrigatórias do Prompt
@app.post("/api/campaign/start")
async def rest_start_campaign(req: StartCampaignRequest):
    license_status = check_license()
    if license_status["status"] in ["expired", "invalid"]:
        return {"success": False, "error": license_status["message"]}
        
    global is_running, run_thread, current_campaign_id
    if is_running: return {"success": False, "error": "A campanha já está ativa"}
    
    current_campaign_id = req.campaign_id
    params = {
        "msg": "", # To be fetched from db or default
        "limit": req.limit if req.limit else 999999,
        "min": req.min_interval,
        "max": req.max_interval,
        "keep_open": False,
        "attachment": None
    }
    
    run_thread = threading.Thread(target=_run_automation, args=(current_campaign_id, params))
    run_thread.daemon = True
    run_thread.start()
    return {"success": True, "message": "Campanha iniciada com sucesso"}

@app.post("/api/campaign/stop")
async def rest_stop_campaign():
    global stop_requested
    if is_running:
        stop_requested = True
        return {"success": True, "message": "Campanha sendo pausada..."}
    return {"success": False, "error": "O sistema já está parado"}

@app.get("/api/campaign/history")
async def rest_get_history():
    return get_campaign_history()

@app.post("/api/contacts/import")
async def rest_import_contacts(req: ImportContactsRequest):
    res = import_contacts_from_xlsx(req.campaign_id, req.xlsx_path)
    if len(res["errors"]) > 0 and res["imported"] == 0:
        return {"success": False, "error": str(res["errors"])}
    return {"success": True, "data": res}

@app.get("/api/blacklist")
async def rest_list_blacklist():
    return get_blacklist()

@app.post("/api/blacklist/add")
async def rest_add_blacklist(req: AddBlacklistRequest):
    if add_to_blacklist(req.phone, req.reason):
        return {"success": True}
    return {"success": False, "error": "Contact is already blacklisted"}

@app.get("/api/accounts")
async def rest_get_accounts():
    return get_all_accounts()

@app.post("/api/accounts/update_status")
async def rest_update_account_status(request: Request):
    data = await request.json()
    status = data.get("status", "connected")
    accounts = get_all_accounts()
    if not accounts:
        from database.services.account_service import create_account
        acc_id = create_account(label="Principal", profile_path="session")
    else:
        acc_id = accounts[0]['id']
    update_account_status(acc_id, status)
    return {"success": True}

@app.get("/api/license")
async def rest_license_status():
    return check_license()

@app.post("/api/license/activate")
async def rest_activate_license(req: ActivateLicenseRequest):
    res = activate_license(req.key)
    return {"success": res["status"] == "active", "data": res}

@app.get("/api/templates")
async def rest_get_templates():
    return get_all_templates()

@app.post("/api/templates")
async def rest_create_template(req: CreateTemplateRequest):
    t_id = create_template(req.name, req.content)
    if t_id > 0: return {"success": True, "id": t_id}
    return {"success": False, "error": "Failed"}

@app.put("/api/templates/{id}")
async def rest_update_template(id: int, req: CreateTemplateRequest):
    if update_template(id, req.name, req.content):
        return {"success": True}
    return {"success": False, "error": "Failed"}

@app.delete("/api/templates/{id}")
async def rest_delete_template(id: int):
    if delete_template(id): return {"success": True}
    return {"success": False, "error": "Failed"}

@app.get("/api/config")
async def rest_get_config():
    return {"success": True, "data": {}}

@app.post("/api/config")
async def rest_set_config(req: SaveConfigRequest):
    for k, v in req.configs.items():
        set_config(k, v)
    return {"success": True}

if __name__ == '__main__':
    def get_local_ip():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def find_free_port(start=5050, end=5099):
        import socket
        for p in range(start, end):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('0.0.0.0', p))
                    return p
            except OSError:
                continue
        return start

    port = find_free_port()
    print(f"Iniciando ZapManager Pro (FastAPI) em porta {port}...")
    
    threading.Thread(target=engine.start, daemon=True).start()
    
    def open_browser():
        import socket
        time.sleep(1.5)
        for _ in range(10):
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=1):
                    break
            except OSError:
                time.sleep(0.5)
        webbrowser.open(f"http://127.0.0.1:{port}")

    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run(app, host="0.0.0.0", port=port)
