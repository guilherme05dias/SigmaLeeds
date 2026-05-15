import os
import io
from datetime import datetime
from contextlib import asynccontextmanager
import time
import hashlib
import threading
import asyncio
import webbrowser
import requests as http_requests

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import logging.handlers
import os

def _setup_logging():
    os.makedirs("data", exist_ok=True)
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Handler de arquivo com rotação: máx 5MB, 3 backups
    file_handler = logging.handlers.RotatingFileHandler(
        "data/zapmanager.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    file_handler.setLevel(logging.DEBUG)

    # Handler de console (apenas WARNING+ para não poluir)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    console_handler.setLevel(logging.WARNING)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # Evita duplicar handlers se chamado mais de uma vez
    if not root.handlers:
        root.addHandler(file_handler)
        root.addHandler(console_handler)
    
    return logging.getLogger("zapmanager")

logger = _setup_logging()

from whatsapp_automation import AutomationEngine
from database import init_db
from database.services.campaign_service import (
    create_campaign, import_contacts_from_xlsx,
    get_pending_contacts, update_contact_status,
    get_campaign_stats, get_campaign_history,
    export_campaign_to_xlsx, reset_processing_contacts,
    normalize_phone, update_campaign_message,
    get_today_sent_count
)
from database.services.blacklist_service import (
    add_to_blacklist, is_blacklisted, detect_optout_keywords, get_blacklist
)
from database.services.config_service import get_config, set_config
from database.services.template_xlsx import build_template_workbook
from database.services.account_service import (
    get_all_accounts, update_account_status
)
from license.manager import check_license, get_current_plan_limits, activate_license, get_daily_limit
from license.hardware import get_hardware_id
from api.models import (
    StartCampaignRequest, ImportContactsRequest,
    ActivateLicenseRequest, AddBlacklistRequest,
    SaveConfigRequest, CreateTemplateRequest,
    SendWindowConfigRequest
)
from database.services.template_service import create_template, get_all_templates, update_template, delete_template, render_template
from database.services.send_window import (
    DEFAULT_SEND_WINDOW,
    is_within_window,
    normalize_send_window_config,
    seconds_until_window_opens,
)
from automation_state import CampaignRunner

import re
from pathlib import Path
import secrets
from fastapi.responses import Response

import subprocess
import ctypes
import ctypes.wintypes
import threading as _threading
import urllib.request as _urlreq

def _spawn_node_with_job(node_script_path: str):
    """
    Spawna Node.js vinculado ao processo Python via Job Object.
    Quando Python morre (qualquer motivo), Windows mata Node.
    """
    node_dir = os.path.dirname(os.path.abspath(node_script_path))
    node_exe = os.environ.get("ZAP_NODE_EXE") or "node"

    CREATE_NO_WINDOW = 0x08000000

    proc = subprocess.Popen(
        [node_exe, "server.js"],
        cwd=node_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    _threading.Thread(
        target=_forward_node_logs,
        args=(proc,),
        daemon=True
    ).start()

    if os.name == 'nt':
        try:
            # Cria Job Object com flag KILL_ON_JOB_CLOSE
            PROCESS_ALL_ACCESS = 0x1F0FFF
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

            h_job = ctypes.windll.kernel32.CreateJobObjectW(None, None)
            global _node_job_handle
            _node_job_handle = h_job


            # Monta struct JOBOBJECT_BASIC_LIMIT_INFORMATION (simplificado)
            # LimitFlags fica no offset 44 (JOBOBJECT_EXTENDED_LIMIT_INFORMATION)
            class JOBOBJECT_BASIC_LIMIT_INFO(ctypes.Structure):
                _fields_ = [
                    ("PerProcessUserTimeLimit", ctypes.c_int64),
                    ("PerJobUserTimeLimit",     ctypes.c_int64),
                    ("LimitFlags",             ctypes.c_uint32),
                    ("MinimumWorkingSetSize",   ctypes.c_size_t),
                    ("MaximumWorkingSetSize",   ctypes.c_size_t),
                    ("ActiveProcessLimit",      ctypes.c_uint32),
                    ("Affinity",               ctypes.c_size_t),
                    ("PriorityClass",          ctypes.c_uint32),
                    ("SchedulingClass",        ctypes.c_uint32),
                ]

            class IO_COUNTERS(ctypes.Structure):
                _fields_ = [(f, ctypes.c_uint64) for f in
                    ("ReadOp","WriteOp","OtherOp","ReadBytes","WriteBytes","OtherBytes")]

            class JOBOBJECT_EXTENDED_LIMIT_INFO(ctypes.Structure):
                _fields_ = [
                    ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFO),
                    ("IoInfo",                IO_COUNTERS),
                    ("ProcessMemoryLimit",    ctypes.c_size_t),
                    ("JobMemoryLimit",        ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed",     ctypes.c_size_t),
                ]

            info = JOBOBJECT_EXTENDED_LIMIT_INFO()
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

            JobObjectExtendedLimitInformation = 9
            ctypes.windll.kernel32.SetInformationJobObject(
                h_job,
                JobObjectExtendedLimitInformation,
                ctypes.byref(info),
                ctypes.sizeof(info)
            )

            h_proc = ctypes.windll.kernel32.OpenProcess(
                PROCESS_ALL_ACCESS, False, proc.pid
            )
            ctypes.windll.kernel32.AssignProcessToJobObject(h_job, h_proc)
            ctypes.windll.kernel32.CloseHandle(h_proc)
            # NÃO fechar h_job — manter aberto para KILL_ON_JOB_CLOSE funcionar

        except Exception as e:
            print(f"[WARN] Job Object falhou (não crítico): {e}")

    return proc

def _should_forward_node_log(line: str) -> bool:
    prefixes = ("[WA]", "[Watchdog]", "Falha", "Error", "SCANEAR QR", "Autenticado")
    return line.startswith(prefixes)

def _forward_node_logs(proc: subprocess.Popen) -> None:
    if not proc.stdout:
        return
    for raw_line in proc.stdout:
        line = raw_line.strip()
        if not line or not _should_forward_node_log(line):
            continue
        level = "ERROR" if line.startswith(("Error", "Falha")) or " error:" in line.lower() else "INFO"
        publish_log_threadsafe(f"[NODE] {line}", level)

_node_health_failures = 0
_node_health_lock = _threading.Lock()

def _node_health_check_loop(node_script_path: str):
    """Verifica se Node responde a cada 30s. Respawna se falhar 3x."""
    global node_process, _node_health_failures
    import time
    while True:
        time.sleep(30)
        try:
            _urlreq.urlopen("http://127.0.0.1:3001/ping", timeout=5)
            with _node_health_lock:
                _node_health_failures = 0
        except Exception:
            with _node_health_lock:
                _node_health_failures += 1
                failures = _node_health_failures
            
            try:
                publish_log_threadsafe(f"[WARN] Node não respondeu ({failures}/3)", "WARN")
            except Exception:
                pass
            
            if failures >= 3:
                try:
                    publish_log_threadsafe("[RESPAWN] Reiniciando processo Node...", "WARN")
                except Exception:
                    pass
                
                try:
                    if node_process:
                        node_process.terminate()
                except Exception:
                    pass
                node_process = _spawn_node_with_job(node_script_path)
                with _node_health_lock:
                    _node_health_failures = 0

SESSION_TOKEN = secrets.token_urlsafe(32)

UPLOAD_ROOT = Path(os.path.abspath("data/attachments"))
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

def safe_filename(name: str, max_len: int = 80) -> str:
    base = os.path.basename(name or "arquivo")
    base = base.replace("\\", "_").replace("/", "_")
    base = re.sub(r'[^A-Za-z0-9._-]', '_', base)
    base = base.lstrip(".")
    if not base or base in ("", ".", ".."):
        base = "arquivo"
    return base[:max_len]

def resolve_under(root: Path, filename: str) -> Path:
    target = (root / filename).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise ValueError(f"Path traversal bloqueado: {filename}")
    return target

from collections import deque
import asyncio as _asyncio

LOG_BUFFER: deque = deque(maxlen=500)
LOG_SUBSCRIBERS: set = set()
_log_main_loop: _asyncio.AbstractEventLoop | None = None

def publish_log(msg: str, level: str = "INFO"):
    """Publica log para todos os subscribers (chamar do event loop)."""
    import time as _time
    entry = {
        "id": int(_time.time() * 1000),
        "level": level,
        "msg": str(msg)[:500]
    }
    LOG_BUFFER.append(entry)
    for q in list(LOG_SUBSCRIBERS):
        try:
            q.put_nowait(entry)
        except Exception:
            pass

def publish_log_threadsafe(msg: str, level: str = "INFO"):
    """Publica log de dentro de threads (sem event loop)."""
    if _log_main_loop and _log_main_loop.is_running():
        _asyncio.run_coroutine_threadsafe(
            _publish_log_async(msg, level),
            _log_main_loop
        )
    else:
        import time as _time
        LOG_BUFFER.append({
            "id": int(_time.time() * 1000),
            "level": level,
            "msg": str(msg)[:500]
        })

async def _publish_log_async(msg: str, level: str):
    publish_log(msg, level)

class _LogShim:
    def put(self, item):
        publish_log_threadsafe(item[0], item[1])

# Module level handles
_node_job_handle = None
node_process = None
runner = CampaignRunner()
engine = AutomationEngine(_LogShim())

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _log_main_loop
    try:
        _log_main_loop = _asyncio.get_event_loop()
    except Exception:
        pass
    # Startup logic
    init_db()
    
    from database.services.campaign_service import reset_stuck_contacts
    reset_stuck_contacts()
    print("[BOOT] Sanitization: EM_PROCESSAMENTO -> PENDENTE complete.")
    
    global node_process
    
        # Iniciar Node.js em background
    import subprocess
    import sys
    
    node_script = os.path.join(os.path.dirname(__file__), "whatsapp-motor", "server.js")
    if os.path.exists(node_script):
        node_process = _spawn_node_with_job(node_script)
        
        _threading.Thread(
            target=_node_health_check_loop,
            args=(node_script,),
            daemon=True
        ).start()
    
    yield
    
    # Shutdown logic
    if node_process:
        try:
            node_process.terminate()
            node_process.wait(timeout=2)
        except:
            pass

app = FastAPI(title="ZapManager Pro", version="4.0.0", lifespan=lifespan)

@app.middleware("http")
async def require_session(request: Request, call_next):
    public_paths = {"/", "/favicon.ico"}
    if (request.url.path in public_paths or
            request.url.path.startswith("/static/")):
        return await call_next(request)
    token = (request.headers.get("X-Session-Token") or
             request.query_params.get("token"))
    if token != SESSION_TOKEN:
        return JSONResponse({"success": False, "error": "Unauthorized"}, status_code=401)
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1", "http://localhost"],
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost):\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-Session-Token"],
)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def _validate_number(raw_num):
    return normalize_phone(raw_num)

def _get_send_window_config() -> dict:
    try:
        return normalize_send_window_config(get_config("send_window", DEFAULT_SEND_WINDOW))
    except ValueError:
        logger.exception("Invalid send_window config; using default")
        return dict(DEFAULT_SEND_WINDOW)

def _get_send_window_state() -> dict:
    config = _get_send_window_config()
    now = datetime.now()
    wait_s = seconds_until_window_opens(now, config)
    return {
        "allowed": is_within_window(now, config),
        "seconds_until_open": wait_s,
        "config": config,
    }

def _wait_for_send_window() -> bool:
    while not runner.stop_requested:
        state = _get_send_window_state()
        if state["allowed"]:
            return True

        wait_s = max(1, int(state["seconds_until_open"]))
        wait_min = max(1, wait_s // 60)
        msg = f"Aguardando janela de horário ({wait_min} min)"
        runner.update_progress(status=msg)
        publish_log_threadsafe(f"[JANELA] Fora do horário de envio. {msg}.", "WARN")

        if runner.stop_event.wait(timeout=min(wait_s, 60)):
            return False

    return False

def _run_automation():
    try:
        campaign_id = runner.campaign_id
        params = runner.params or {}

        runner.update_progress(status="Em andamento")

        publish_log_threadsafe("Verificando Motor de Automação...", "INFO")
        if not engine.start():
            publish_log_threadsafe("Falha crítica: Motor WhatsApp não responde.", "ERROR")
            runner.update_progress(status="Erro")
            return

        publish_log_threadsafe("Motor pronto. Iniciando disparos...", "INFO")

        import random

        # Always reset any contacts stuck in EM_PROCESSAMENTO from a previous crash,
        # regardless of whether this is a fresh start or a resume.
        reset_processing_contacts(campaign_id)

        pending_contacts = get_pending_contacts(campaign_id)
        count = 0
        recent_results = []

        for contact in pending_contacts:
            if runner.stop_requested or count >= params['limit']:
                break

            if not _wait_for_send_window():
                break

            # Verificação de limite diário por plano
            daily_limit = get_daily_limit()
            if daily_limit and daily_limit < 999999:
                sent_today = get_today_sent_count()
                if sent_today >= daily_limit:
                    msg = f"[LIMITE] Limite diário de {daily_limit} envios atingido para seu plano. Campanha pausada."
                    logger.warning(msg)
                    publish_log_threadsafe(msg, "WARN")
                    runner.update_progress(status="Limite diário atingido")
                    break

            row_id = contact['id']
            nome = contact['name'] or "Cliente"
            empresa = contact['company'] or ""
            raw_num = contact['phone']

            num = _validate_number(raw_num)
            if not num:
                update_contact_status(row_id, "INVÁLIDO", f"Número fora do padrão: {raw_num}")
                publish_log_threadsafe(f"[C-{row_id}] {nome}: número inválido ({raw_num})", "WARN")
                runner.update_progress(
                    pending=max(0, runner.progress.pending - 1),
                    invalid=runner.progress.invalid + 1,
                )
                continue

            update_contact_status(row_id, "EM_PROCESSAMENTO")

            msg_cur = render_template(params['msg'], contact)

            # Prioridade: anexo individual > anexo global > sem anexo
            # Sempre buscar o anexo individual do banco — nunca confiar no cache em memória
            from database.services.campaign_service import get_contact_attachment
            contact_att = get_contact_attachment(contact['id'])
            global_att = params.get('attachment', '')
            att = None
            if contact_att and os.path.exists(contact_att):
                att = contact_att
            elif global_att and os.path.exists(global_att):
                att = global_att

            publish_log_threadsafe(f"[C-{row_id}] Enviando para {nome} ({num[-4:]}...)...", "INFO")

            try:
                if att:
                    res = engine.send_with_attachment(num, msg_cur, att)
                else:
                    res = engine.send_message(num, msg_cur)
            except Exception as e:
                res = "ERRO"
                publish_log_threadsafe(f"Exceção no envio: {e}", "ERROR")

            if res == "SUCESSO":
                update_contact_status(row_id, "ENVIADO")
                count += 1
                runner.update_progress(
                    processed=runner.progress.processed + 1,
                    pending=max(0, runner.progress.pending - 1),
                    sent=runner.progress.sent + 1,
                )
                publish_log_threadsafe(f"✔ {nome} — ENVIADO ({count}/{params['limit']})", "SUCCESS")
            elif res == "INVALIDO" or res == "INVÁLIDO":
                update_contact_status(row_id, "INVÁLIDO", "WhatsApp informou número inválido")
                publish_log_threadsafe(f"✘ {nome} — INVÁLIDO", "WARN")
                runner.update_progress(
                    pending=max(0, runner.progress.pending - 1),
                    invalid=runner.progress.invalid + 1,
                )
            else:
                # Before marking as ERRO, check if disconnect caused the failure
                _wa_reconnected = False
                try:
                    _node_status = http_requests.get(
                        "http://127.0.0.1:3001/status", timeout=3
                    ).json()
                    if not _node_status.get("connected", True):
                        _disc_msg = "[AVISO] WhatsApp desconectado. Aguardando reconexão (max 60s)..."
                        logger.warning(_disc_msg)
                        publish_log_threadsafe(_disc_msg, "WARN")
                        runner.update_progress(status="Aguardando reconexão...")
                        for _attempt in range(12):
                            runner.stop_event.wait(timeout=5)
                            if runner.stop_requested:
                                break
                            try:
                                _recheck = http_requests.get(
                                    "http://127.0.0.1:3001/status", timeout=3
                                ).json()
                                if _recheck.get("connected", False):
                                    publish_log_threadsafe("[INFO] WhatsApp reconectado. Retomando campanha...", "INFO")
                                    runner.update_progress(status="Em andamento")
                                    _wa_reconnected = True
                                    break
                            except Exception:
                                pass
                        else:
                            publish_log_threadsafe("[ERRO] Reconexão não foi possível em 60s. Campanha pausada.", "ERROR")
                            runner.update_progress(status="Pausado — sem conexão")
                            runner.stop_event.set()
                except Exception as _check_err:
                    logger.warning(f"Could not check Node status after failure: {_check_err}")

                update_contact_status(row_id, "ERRO", "Falha técnica na entrega")
                publish_log_threadsafe(f"✘ {nome} — ERRO técnico", "ERROR")
                runner.update_progress(
                    pending=max(0, runner.progress.pending - 1),
                    failed=runner.progress.failed + 1,
                )


            # Circuit Breaker
            if res == "SUCESSO":
                recent_results.append("ENVIADO")
            elif res in ("INVALIDO", "INVÁLIDO"):
                recent_results.append("INVÁLIDO")
            else:
                recent_results.append("ERRO")

            if len(recent_results) > 20:
                recent_results.pop(0)
            if len(recent_results) >= 10:
                error_rate = recent_results.count("ERRO") / len(recent_results)
                if error_rate >= 0.10:
                    msg = f"[CIRCUIT BREAKER] Error rate {round(error_rate*100)}% in last {len(recent_results)} sends. Pausing for 30 minutes."
                    logger.warning(msg)
                    publish_log_threadsafe(msg, "WARN")
                    runner.stop_event.wait(timeout=1800)
                    recent_results.clear()
                    if not runner.stop_event.is_set():
                        msg2 = "[CIRCUIT BREAKER] Pause complete. Resuming campaign."
                        logger.info(msg2)
                        publish_log_threadsafe(msg2, "INFO")

            if not runner.stop_requested and count < params['limit']:
                delay = random.randint(params['min'], params['max'])
                publish_log_threadsafe(f"Aguardando {delay}s antes do próximo...", "INFO")
                import time
                for _ in range(delay):
                    if runner.stop_requested:
                        break
                    time.sleep(1)

        if runner.stop_requested:
            publish_log_threadsafe("Campanha pausada pelo usuário. Clique em RETOMAR para continuar.", "WARN")
            runner.update_progress(status="Pausada")
            runner.was_stopped = True
        else:
            publish_log_threadsafe("✔ Campanha finalizada com sucesso!", "SUCCESS")
            runner.update_progress(status="Concluída")
            runner.was_stopped = False
            if not params.get('keep_open', False):
                engine.stop()
            else:
                publish_log_threadsafe("Navegador mantido aberto.", "INFO")

    except Exception:
        logger.exception("[WORKER] Unhandled exception in _run_automation")
        publish_log_threadsafe("[ERRO] Exceção interna no worker. Campanha encerrada.", "ERROR")
        runner.update_progress(status="Erro interno")

    finally:
        publish_log_threadsafe("[INFO] Worker thread encerrado.", "INFO")


@app.get("/")
async def serve_index():
    html = Path("templates/index.html").read_text(encoding="utf-8")
    html = html.replace(
        "</head>",
        f'<meta name="zap-token" content="{SESSION_TOKEN}"></head>'
    )
    return Response(html, media_type="text/html")

@app.get("/api/logs")
async def logs_stream(request: Request):
    q: _asyncio.Queue = _asyncio.Queue(maxsize=200)
    LOG_SUBSCRIBERS.add(q)

    last_id = 0
    try:
        last_id = int(request.headers.get("last-event-id", 0))
    except (ValueError, TypeError):
        last_id = 0
    replay = [e for e in LOG_BUFFER if e["id"] > last_id]
    for entry in replay:
        await q.put(entry)

    async def generate():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    entry = await _asyncio.wait_for(q.get(), timeout=20)
                    safe_msg = str(entry["msg"]).replace("\n", " ")
                    yield (
                        f"id: {entry['id']}\n"
                        f"data: {entry['level']}|{safe_msg}\n\n"
                    )
                except _asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            LOG_SUBSCRIBERS.discard(q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )

@app.get("/api/template/contacts.xlsx")
async def download_contacts_template():
    buffer = io.BytesIO()
    workbook = build_template_workbook()
    workbook.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="contatos_modelo.xlsx"'},
    )

# Compatibility with frontend
@app.post("/api/contacts/import")
async def import_contacts(file: UploadFile = File(...)):
    if runner.is_running:
        return JSONResponse(
            {"success": False, "error": "Cannot modify contacts while a campaign is running."},
            status_code=409
        )
    if not file.filename.endswith('.xlsx'):
        return JSONResponse({"success": False, "error": "Invalid file type. Apenas .xlsx permitidos."}, status_code=400)

    content = await file.read()
    safe = safe_filename(file.filename)
    target = resolve_under(UPLOAD_ROOT, f"excel_{safe}")
    target.write_bytes(content)
    path = str(target)

    try:
        from database.services.campaign_service import get_campaign_details
        campaign_name = f"Campanha {file.filename} - {time.strftime('%Y%m%d%H%M')}"
        cid = create_campaign(campaign_name, "")
        if cid < 0:
            return JSONResponse({"success": False, "error": "Erro ao criar campanha no banco de dados"}, status_code=500)

        res = import_contacts_from_xlsx(cid, path)
        if len(res["errors"]) > 0 and res["imported"] == 0:
            return JSONResponse({"success": False, "error": "Falha total na importacao: " + str(res["errors"])}, status_code=400)

        runner.set_excel(file.filename, cid)

        details = get_campaign_details(cid)
        pending_count = len(get_pending_contacts(cid))

        runner.reset_progress(total=pending_count, pending=pending_count)
        runner.update_progress(status="Planilha Carregada")
        
        return {
            "success": True, 
            "data": {
                "campaign_id": cid,
                "total": res["total"],
                "imported": res["imported"],
                "skipped_blacklist": res["skipped_blacklist"],
                "duplicates_detected": res["duplicates_detected"],
                "duplicate_phones": res.get("duplicate_phones", []),
                "errors": res["errors"][:50],
                "error_count": len(res["errors"])
            },
            "contacts": details["contacts"] if details else []
        }
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

# Alias para compatibilidade legada
@app.post("/api/upload-excel")
async def upload_excel_legacy(file: UploadFile = File(...)):
    return await import_contacts(file)

@app.post("/api/clear-excel")
async def clear_excel():
    if runner.is_running:
        return JSONResponse({"success": False, "error": "Não é possível remover durante uma campanha ativa."}, status_code=400)
    runner.set_excel(None, None)
    runner.set_attachment(None)
    runner.reset_progress(total=0, pending=0)
    runner.update_progress(status="Aguardando")
    publish_log_threadsafe("Planilha removida. Pronto para nova campanha.", "INFO")
    return {"success": True, "data": {"message": "Planilha removida"}}

@app.post("/api/upload-attachment")
async def upload_attachment(file: UploadFile = File(...)):
    if not file: return JSONResponse({"success": False, "error": "No file"}, status_code=400)
    content = await file.read()
    safe = safe_filename(file.filename)
    target = resolve_under(UPLOAD_ROOT, f"global_{safe}")
    target.write_bytes(content)
    path = str(target)
    runner.set_attachment(path)
    return {"success": True, "data": {"message": "Attachment saved", "filename": file.filename}}

@app.post("/api/clear-attachment")
async def clear_attachment():
    runner.set_attachment(None)
    return {"success": True, "data": {"message": "Cleared"}}

@app.post("/api/start")
async def legacy_start_campaign(request: Request):
    if runner.is_running:
        return JSONResponse({"success": False, "error": "A campanha já está ativa"}, status_code=400)
    if not runner.campaign_id:
        return JSONResponse({"success": False, "error": "É necessário enviar uma planilha .xlsx primeiro"}, status_code=400)

    data = await request.json()

    license_status = check_license()
    if license_status["status"] in ["expired", "invalid"]:
        return JSONResponse({"success": False, "error": license_status["message"]}, status_code=400)

    limits = get_current_plan_limits()

    _lo = max(15, min(45, int(data.get("min", 15))))
    _hi = max(_lo, min(45, int(data.get("max", 30))))

    params = {
        "msg": data.get("msg", ""),
        "limit": int(data.get("limit", 100)),
        "min": _lo,
        "max": _hi,
        "keep_open": data.get("keep_open", False),
        "attachment": runner.attachment,
    }

    try:
        from database.schema import get_connection
        conn = get_connection()
        with conn:
            conn.execute("UPDATE campaigns SET message_template = ? WHERE id = ?", (params["msg"], runner.campaign_id))
        conn.close()
    except Exception:
        logger.exception("Failed to update campaign message template")

    started = runner.start(
        campaign_id=runner.campaign_id,
        params=params,
        target_fn=_run_automation,
    )
    if not started:
        return JSONResponse({"success": False, "error": "Campanha já em execução"}, status_code=400)

    return {"message": "Campanha iniciada com sucesso"}

@app.post("/api/stop")
async def stop_campaign():
    if runner.is_running:
        runner.stop()
        return {"success": True, "data": {"message": "Campanha sendo pausada..."}}
    return {"success": True, "data": {"message": "O sistema já está parado"}}

@app.post("/api/resume")
async def legacy_resume_campaign(request: Request):
    if runner.is_running:
        return JSONResponse({"success": False, "error": "A campanha já está ativa"}, status_code=400)
    if not runner.was_stopped:
        return JSONResponse({"success": False, "error": "Não há campanha pausada para retomar"}, status_code=400)
    if not runner.campaign_id:
        return JSONResponse({"success": False, "error": "Planilha não está mais carregada"}, status_code=400)

    data = await request.json()
    params = runner.params.copy() if runner.params else {}
    if data.get("msg"): params["msg"] = data["msg"]
    if data.get("limit"): params["limit"] = int(data["limit"])
    if runner.attachment: params["attachment"] = runner.attachment
    params["resume"] = True

    started = runner.start(
        campaign_id=runner.campaign_id,
        params=params,
        target_fn=_run_automation,
    )
    if not started:
        return JSONResponse({"success": False, "error": "Campanha já em execução"}, status_code=400)

    return {"message": "Campanha retomada com sucesso"}

@app.get("/api/status")
async def get_status():
    snap = runner.snapshot()
    
    # Obter status do motor Node
    connected = False
    try:
        resp = http_requests.get("http://127.0.0.1:3001/status", timeout=1).json()
        connected = resp.get("connected", False)
    except:
        pass

    return {
        "success": True,
        "is_running": snap["is_running"],
        "was_stopped": snap["was_stopped"],
        "campaign_id": snap["campaign_id"],
        "attachment": os.path.basename(runner.attachment) if runner.attachment else None,
        "excel": runner.excel_path,
        "connected": connected,
        "progress": {
            "total": snap.get("total", 0),
            "processed": snap.get("processed", 0),
            "pending": snap.get("pending", 0),
            "sent": snap.get("sent", 0),
            "failed": snap.get("failed", 0),
            "invalid": snap.get("invalid", 0),
            "status": snap.get("status", "Aguardando"),
        }
    }

@app.get("/api/connector")
async def get_connector_status():
    try:
        node_resp = http_requests.get("http://127.0.0.1:3001/status", timeout=2).json()
        return {
            "success": True,
            "data": {
                "connected": bool(node_resp.get("connected", False)),
                "status": node_resp.get("status", "unknown"),
                "qr": node_resp.get("qr"),
                "node_online": True,
            }
        }
    except Exception as e:
        logger.warning(f"Node motor unreachable: {e}")
        return {
            "success": True,
            "data": {
                "connected": False,
                "status": "node_offline",
                "qr": None,
                "node_online": False,
            }
        }

@app.get("/api/onboarding/status")
async def onboarding_status():
    value = get_config("onboarding_completed", "0")
    completed = value is True or value == 1 or str(value) == "1"
    return {"success": True, "data": {"completed": completed}}

@app.post("/api/onboarding/complete")
async def onboarding_complete():
    set_config("onboarding_completed", "1")
    return {"success": True, "data": {"completed": True}}

@app.post("/api/whatsapp/disconnect")
async def whatsapp_disconnect():
    """Desconecta a sessão atual do WhatsApp Web."""
    if runner.is_running:
        return JSONResponse(
            {"success": False,
             "error": "Não é possível desconectar durante uma campanha ativa."},
            status_code=409
        )
    try:
        resp = http_requests.post(
            "http://127.0.0.1:3001/disconnect",
            timeout=10
        )
        data = resp.json()
        logger.info("WhatsApp session disconnected by user.")
        return {"success": True, "message": data.get("message", "Desconectado.")}
    except Exception as e:
        logger.exception("Failed to disconnect WhatsApp session")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )

@app.post("/api/whatsapp/reset")
async def whatsapp_reset():
    """Reseta a sessão local do WhatsApp e força a geração de novo QR Code."""
    if runner.is_running:
        return JSONResponse(
            {"success": False, "error": "Pare a campanha antes de resetar a sessão."},
            status_code=409
        )
    try:
        resp = http_requests.post("http://127.0.0.1:3001/reset-session", timeout=15)
        return resp.json()
    except Exception as e:
        logger.exception("Failed to reset WhatsApp session")
        return JSONResponse({"success": False, "error": str(e)}, status_code=502)

# REST APIs Obrigatórias do Prompt
@app.post("/api/campaign/start")
async def rest_start_campaign(req: StartCampaignRequest):
    license_status = check_license()
    if license_status["status"] in ["expired", "invalid"]:
        return {"success": False, "error": license_status["message"]}

    update_campaign_message(req.campaign_id, req.message)

    daily_limit = get_daily_limit()
    today_sent = get_today_sent_count()
    remaining = daily_limit - today_sent

    if remaining <= 0:
        return {
            "success": False,
            "error": f"Limite diário atingido ({daily_limit} envios). Tente novamente amanhã."
        }

    effective_limit = min(req.limit if req.limit else 999999, remaining)

    lo = max(15, min(45, req.min_interval or 15))
    hi = max(lo, min(45, req.max_interval or 30))

    params = {
        "msg": req.message,
        "limit": effective_limit,
        "min": lo,
        "max": hi,
        "keep_open": False,
        "attachment": runner.attachment,
    }

    started = runner.start(
        campaign_id=req.campaign_id,
        params=params,
        target_fn=_run_automation,
    )
    if not started:
        return {"success": False, "error": "Campanha já em execução"}
    return {"success": True, "campaign_id": req.campaign_id, "message": "Campanha iniciada com sucesso"}

@app.post("/api/campaign/stop")
async def rest_stop_campaign():
    if runner.is_running:
        runner.stop()
        return {"success": True, "message": "Campanha sendo pausada..."}
    return {"success": False, "error": "O sistema já está parado"}

@app.post("/api/contacts/{contact_id}/attachment")
async def upload_contact_attachment(contact_id: int, file: UploadFile = File(...)):
    """Salva PDF individual para um contato específico."""
    try:
        if not file.filename.lower().endswith('.pdf'):
            return {"success": False, "error": "Apenas arquivos PDF são permitidos."}

        from database.schema import get_connection
        conn = get_connection()
        contact = conn.execute(
            "SELECT id, campaign_id FROM campaign_contacts WHERE id = ?",
            (contact_id,)
        ).fetchone()
        conn.close()
        if not contact:
            return {"success": False, "error": "Contato não encontrado."}

        content = await file.read()
        if not content.startswith(b"%PDF-"):
            return {"success": False, "error": "Arquivo não é PDF válido."}

        file_hash = hashlib.md5(content).hexdigest()[:8]

        safe = safe_filename(file.filename)
        target = resolve_under(UPLOAD_ROOT, f"contato_{contact_id}_{file_hash}_{safe}")
        target.write_bytes(content)
        path = str(target)

        from database.services.campaign_service import update_contact_attachment
        update_contact_attachment(contact_id, path)

        return {"success": True, "path": path, "filename": file.filename}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/api/contacts/{contact_id}/attachment")
async def remove_contact_attachment(contact_id: int):
    """Remove o anexo individual de um contato."""
    try:
        from database.services.campaign_service import (
            get_contact_attachment, update_contact_attachment
        )
        path = get_contact_attachment(contact_id)
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        update_contact_attachment(contact_id, None)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/campaign/{campaign_id}/details")
async def get_details(campaign_id: int):
    """Retorna metadados e lista de contatos de uma campanha específica."""
    from database.services.campaign_service import get_campaign_details
    data = get_campaign_details(campaign_id)
    if not data:
        return {"success": False, "error": "Campanha não encontrada"}
    return {"success": True, "data": data}

@app.post("/api/campaign/{campaign_id}/retry")
async def retry_failed(campaign_id: int, req: dict = None):
    """Reseta contatos com ERRO para PENDENTE e reinicia disparos."""
    if runner.is_running:
        return {"success": False, "error": "Já existe uma campanha em execução"}

    from database.services.campaign_service import reset_failed_contacts, get_campaign_details
    count = reset_failed_contacts(campaign_id)

    if count == 0:
        return {"success": False, "error": "Nenhum contato com erro encontrado para esta campanha"}

    data = get_campaign_details(campaign_id)
    camp = data["campaign"]

    params = {
        "msg": camp["message_template"],
        "limit": 999999,
        "min": 15,
        "max": 45,
        "keep_open": False,
        "attachment": camp["attachment_path"],
    }

    if req:
        if "min_interval" in req: params["min"] = req["min_interval"]
        if "max_interval" in req: params["max"] = req["max_interval"]

    started = runner.start(
        campaign_id=campaign_id,
        params=params,
        target_fn=_run_automation,
    )
    if not started:
        return {"success": False, "error": "Campanha já em execução"}

    return {"success": True, "data": {"message": f"{count} contatos resetados. Disparos reiniciados."}}

@app.get("/api/campaign/{campaign_id}/export")
async def export_campaign(campaign_id: int):
    """Exporta resultado da campanha em .xlsx para download."""
    license_status = check_license()
    if license_status["status"] in ["expired", "invalid"]:
        return {"success": False, "error": license_status["message"]}
    
    output_path = f"data/relatorio_campanha_{campaign_id}.xlsx"
    try:
        file_path = export_campaign_to_xlsx(campaign_id, output_path)
        if not file_path:
            return {"success": False, "error": "Falha ao gerar o arquivo."}
            
        return FileResponse(
            path=file_path,
            filename=f"relatorio_campanha_{campaign_id}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/contacts/validate-phone")
async def validate_phone_endpoint(data: dict):
    """Valida e normaliza um número de telefone."""
    from database.services.campaign_service import normalize_phone
    phone = data.get("phone", "")
    normalized = normalize_phone(phone)
    return {"valid": normalized is not None, "normalized": normalized or phone}

@app.get("/api/campaigns/history")
async def rest_get_history():
    campaigns = get_campaign_history()
    for c in campaigns:
        stats = get_campaign_stats(c["id"])
        c.update(stats)
        # Calcula taxa de entrega: (enviados / (total - invalidos - blacklist)) * 100
        total_valid = max(0, c.get("total", 0) - c.get("invalid", 0) - c.get("blacklist", 0))
        delivery_rate = round((c.get("sent", 0) / total_valid) * 100) if total_valid > 0 else 0
        c["delivery_rate"] = delivery_rate
        c["total_valid"] = total_valid
    return {"success": True, "data": campaigns}



@app.post("/api/contacts/{contact_id}/update")
async def update_contact(contact_id: int, data: dict):
    """Atualiza nome ou número de um contato."""
    if runner.is_running:
        return JSONResponse(
            {"success": False, "error": "Cannot modify contacts while a campaign is running."},
            status_code=409
        )
    from database.schema import get_connection
    try:
        with get_connection() as conn:
            if 'phone' in data:
                conn.execute("UPDATE campaign_contacts SET phone=? WHERE id=?",
                            (data['phone'], contact_id))
            if 'name' in data:
                conn.execute("UPDATE campaign_contacts SET name=? WHERE id=?",
                            (data['name'], contact_id))
            conn.commit()
        return {"success": True, "data": None}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/api/contacts/{contact_id}/remove")
async def remove_contact(contact_id: int):
    """Remove contato da campanha."""
    if runner.is_running:
        return JSONResponse(
            {"success": False, "error": "Cannot modify contacts while a campaign is running."},
            status_code=409
        )
    from database.schema import get_connection
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM campaign_contacts WHERE id=?", (contact_id,))
            conn.commit()
        return {"success": True, "data": None}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/blacklist")
async def rest_list_blacklist():
    return {"success": True, "data": get_blacklist()}

@app.post("/api/blacklist/add")
async def rest_add_blacklist(req: AddBlacklistRequest):
    if add_to_blacklist(req.phone, req.reason):
        return {"success": True, "data": None}
    return {"success": False, "error": "Contact is already blacklisted"}

@app.get("/api/accounts")
async def rest_get_accounts():
    return {"success": True, "data": get_all_accounts()}

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
    return {"success": True, "data": None}

@app.get("/api/license/status")
async def rest_license_status():
    res = check_license()
    res["hardware_id"] = get_hardware_id()
    return {"success": True, "data": res}

@app.post("/api/license/activate")
async def rest_activate_license(req: ActivateLicenseRequest):
    res = activate_license(req.key)
    ok = res.get("valid") is True
    return {
        "success": ok,
        "data": res,
        "error": None if ok else res.get("error_message", "Chave inválida")
    }

@app.get("/api/templates")
async def rest_get_templates():
    return {"success": True, "data": get_all_templates()}

@app.post("/api/templates")
async def rest_create_template(req: CreateTemplateRequest):
    t_id = create_template(req.name, req.content)
    if t_id > 0: return {"success": True, "data": {"id": t_id}}
    return {"success": False, "error": "Failed"}

@app.put("/api/templates/{id}")
async def rest_update_template(id: int, req: CreateTemplateRequest):
    if update_template(id, req.name, req.content):
        return {"success": True, "data": None}
    return {"success": False, "error": "Failed"}

@app.delete("/api/templates/{id}")
async def rest_delete_template(id: int):
    if delete_template(id): return {"success": True, "data": None}
    return {"success": False, "error": "Failed"}

@app.get("/api/config/send-window")
async def rest_get_send_window():
    return {"success": True, "data": _get_send_window_config(), "state": _get_send_window_state()}

@app.post("/api/config/send-window")
async def rest_set_send_window(req: SendWindowConfigRequest):
    try:
        config = normalize_send_window_config(req.dict())
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)
    set_config("send_window", config)
    return {"success": True, "data": config, "state": _get_send_window_state()}

@app.get("/api/config")
async def rest_get_config():
    return {"success": True, "data": {}}

@app.post("/api/config")
async def rest_set_config(req: SaveConfigRequest):
    for k, v in req.configs.items():
        set_config(k, v)
    return {"success": True, "data": None}

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

    if os.environ.get("ZAP_NO_BROWSER") != "1":
        threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run(app, host="127.0.0.1", port=port)
