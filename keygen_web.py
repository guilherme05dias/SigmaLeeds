"""
Mini UI web local para gerar licencas ZapManager Pro.

Uso:
    python keygen_web.py

Requisitos:
    private_key.pem na mesma pasta deste script (a chave privada do operador).

Abre automaticamente em http://127.0.0.1:7070 no navegador padrao.
Historico das ultimas 50 chaves emitidas e salvo em keygen_history.json.
"""
import json
import time
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from keygen import generate_license_key

PORT = 9876
SCRIPT_DIR = Path(__file__).parent
PRIVATE_KEY_PATH = SCRIPT_DIR / "private_key.pem"
HISTORY_FILE = SCRIPT_DIR / "keygen_history.json"
MAX_HISTORY = 50

# Single-tier desde v4.2.5: todo cliente recebe a mesma licenca.
# O plan ainda existe no payload da chave por compatibilidade com licencas
# antigas, mas todos novos usam "pro".
FIXED_PLAN = "pro"
PLANS = ["pro", "starter", "agency"]   # aceitos pelo validador para compat retroativa
DEFAULT_DAYS = 365

app = FastAPI(title="ZapManager Pro - Keygen Web")


def load_private_key_safe():
    if not PRIVATE_KEY_PATH.exists():
        return None
    return serialization.load_pem_private_key(PRIVATE_KEY_PATH.read_bytes(), password=None)


def load_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_history(entries):
    HISTORY_FILE.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def render_history_rows(history):
    if not history:
        return (
            '<tr><td colspan="5" class="empty">Nenhuma chave gerada ainda. '
            'Cole um Hardware ID acima e clique em Gerar.</td></tr>'
        )
    rows = []
    for h in history:
        hwid_short = h["hwid"][:16] + ("..." if len(h["hwid"]) > 16 else "")
        customer = h.get("customer") or "—"
        rows.append(
            f'<tr>'
            f'<td>{h["issued_at_human"]}</td>'
            f'<td>{customer}</td>'
            f'<td>{h["days"]} dias (ate {h["expires_at_human"]})</td>'
            f'<td title="{h["hwid"]}"><code>{hwid_short}</code></td>'
            f'<td><button class="btn-copy-small" '
            f'onclick="copyKey(this, \'{h["key"]}\')">Copiar</button></td>'
            f'</tr>'
        )
    return "".join(rows)


HTML_TEMPLATE = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>ZapManager Pro — Keygen</title>
<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>
<style>
:root {
    --bg: #0e1117;
    --bg-card: #161b22;
    --bg-input: #1c2129;
    --border: #2f343c;
    --text: #e5e7eb;
    --text-muted: #9ba3af;
    --brand: #4d8cff;
    --brand-dark: #2c6cde;
    --success: #1f8a3e;
    --success-bg: #143d24;
    --warn-bg: #3a2e15;
    --warn: #f0b942;
    --danger: #cf1322;
    --danger-bg: #3a1d28;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    font-family: -apple-system, system-ui, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    font-size: 14px;
    line-height: 1.5;
}
.container { max-width: 900px; margin: 0 auto; padding: 32px 24px 80px; }
header { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; }
header .badge { background: var(--brand); color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; }
h1 { margin: 0; font-size: 22px; font-weight: 600; }
.subtitle { color: var(--text-muted); margin: 0 0 24px; font-size: 13px; }
.card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 24px; margin-bottom: 20px; }
.card h2 { margin: 0 0 16px; font-size: 16px; display: flex; align-items: center; gap: 8px; }
.form-grid { display: grid; grid-template-columns: 1fr 140px 1fr; gap: 12px; margin-bottom: 12px; }
.form-grid .col-full { grid-column: 1 / -1; }
label { display: block; font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
input, select, textarea {
    width: 100%; padding: 8px 10px; background: var(--bg-input);
    border: 1px solid var(--border); border-radius: 6px;
    color: var(--text); font-family: inherit; font-size: 13px;
    transition: border 120ms;
}
input:focus, select:focus, textarea:focus { outline: none; border-color: var(--brand); }
input[type="text"]#hwid { font-family: 'Courier New', monospace; font-size: 12px; }
.actions { display: flex; gap: 8px; align-items: center; margin-top: 16px; }
.btn {
    padding: 8px 16px; border-radius: 6px; border: 1px solid transparent;
    font-size: 13px; font-weight: 500; cursor: pointer; height: 36px;
    display: inline-flex; align-items: center; gap: 6px;
    transition: background 120ms;
}
.btn-primary { background: var(--brand); color: white; }
.btn-primary:hover { background: var(--brand-dark); }
.btn-primary:disabled { background: #555; cursor: not-allowed; }
.btn-ghost { background: transparent; color: var(--text-muted); border-color: var(--border); }
.btn-ghost:hover { background: var(--bg-input); color: var(--text); }
.btn svg { width: 14px; height: 14px; }
.result {
    margin-top: 16px; padding: 16px; border-radius: 6px;
    background: var(--success-bg); border: 1px solid var(--success);
    display: none;
}
.result.show { display: block; }
.result.error { background: var(--danger-bg); border-color: var(--danger); }
.result .key-box {
    background: var(--bg-input); padding: 12px; border-radius: 6px;
    margin: 8px 0; word-break: break-all; font-family: 'Courier New', monospace;
    font-size: 11px; line-height: 1.4; max-height: 120px; overflow-y: auto;
    border: 1px solid var(--border);
}
.result .meta { font-size: 12px; color: var(--text-muted); margin-top: 8px; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; padding: 10px 8px; background: var(--bg-input); color: var(--text-muted); font-weight: 500; border-bottom: 1px solid var(--border); }
td { padding: 10px 8px; border-bottom: 1px solid var(--border); }
td.empty { text-align: center; color: var(--text-muted); padding: 24px; font-style: italic; }
td code { background: var(--bg-input); padding: 2px 6px; border-radius: 4px; font-size: 11px; }
.btn-copy-small { padding: 4px 8px; height: 24px; font-size: 11px; background: transparent; color: var(--brand); border: 1px solid var(--border); border-radius: 4px; cursor: pointer; }
.btn-copy-small:hover { background: var(--bg-input); }
.warn-banner { background: var(--warn-bg); border: 1px solid var(--warn); padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; display: flex; gap: 10px; align-items: flex-start; }
.warn-banner svg { color: var(--warn); flex-shrink: 0; margin-top: 2px; }
.warn-banner.hide { display: none; }
.hint { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
</style>
</head>
<body>
<div class="container">
    <header>
        <i data-lucide="key-round" style="width:24px;height:24px;color:var(--brand)"></i>
        <h1>ZapManager Pro — Gerador de Licença</h1>
        <span class="badge">v1.0</span>
    </header>
    <p class="subtitle">Geração local de chaves ZMPRO. A chave privada nunca sai dessa máquina.</p>

    <div id="warn-no-key" class="warn-banner hide">
        <i data-lucide="alert-triangle" size="16"></i>
        <div>
            <strong>private_key.pem não encontrado.</strong><br>
            Coloque a chave privada em <code>{{KEY_PATH}}</code> antes de gerar.
        </div>
    </div>

    <div class="card">
        <h2><i data-lucide="plus-circle"></i> Nova chave</h2>
        <form id="gen-form" autocomplete="off">
            <div class="form-grid">
                <div class="col-full">
                    <label for="hwid">Hardware ID</label>
                    <input type="text" id="hwid" name="hwid" required
                           placeholder="cole aqui o hardware ID enviado pelo cliente" autofocus>
                    <div class="hint">String hexadecimal (geralmente 32 ou 64 caracteres).</div>
                </div>
                <div>
                    <label for="days">Validade (dias)</label>
                    <input type="number" id="days" name="days" value="365" min="1" max="36500">
                    <div class="hint">36500 = eterno</div>
                </div>
                <div>
                    <label for="customer">Cliente (opcional)</label>
                    <input type="text" id="customer" name="customer" placeholder="ex: João Silva">
                </div>
            </div>
            <div class="actions">
                <button type="submit" class="btn btn-primary" id="btn-generate">
                    <i data-lucide="key"></i> Gerar chave
                </button>
                <button type="button" class="btn btn-ghost" onclick="setDays(36500)">365×100 (eterno)</button>
                <button type="button" class="btn btn-ghost" onclick="setDays(365)">1 ano</button>
                <button type="button" class="btn btn-ghost" onclick="setDays(30)">30 dias</button>
            </div>
        </form>

        <div id="result" class="result">
            <div id="result-msg"></div>
            <div class="key-box" id="result-key"></div>
            <div class="meta" id="result-meta"></div>
            <div class="actions" id="result-actions" style="display:none">
                <button type="button" class="btn btn-primary" onclick="copyResultKey()">
                    <i data-lucide="copy"></i> Copiar chave
                </button>
            </div>
        </div>
    </div>

    <div class="card">
        <h2><i data-lucide="check-circle"></i> O que vai nessa licença</h2>
        <ul style="margin:0; padding-left:20px; line-height:1.8; color:var(--text);">
            <li>Contas WhatsApp: ilimitado</li>
            <li>Disparos/dia: sem limite hard. Aviso configurável de segurança anti-banimento.</li>
            <li>Templates: ilimitado</li>
            <li>Anexo global + por contato</li>
            <li>Exportar relatório (.xlsx)</li>
            <li>Histórico completo de campanhas</li>
        </ul>
        <div class="hint" style="margin-top:12px">Todos os clientes recebem a mesma licença (single-tier). O cliente final ajusta o limite diário de segurança nas configurações do app.</div>
    </div>

    <div class="card">
        <h2><i data-lucide="history"></i> Últimas {{MAX_HISTORY}} chaves emitidas</h2>
        <table>
            <thead>
                <tr>
                    <th>Emitida em</th>
                    <th>Cliente</th>
                    <th>Validade</th>
                    <th>Hardware ID</th>
                    <th></th>
                </tr>
            </thead>
            <tbody id="history-body">
                {{HISTORY_ROWS}}
            </tbody>
        </table>
    </div>
</div>

<script>
function setDays(d) { document.getElementById('days').value = d; }
function setText(id, t) { document.getElementById(id).textContent = t; }

async function copyKey(btn, key) {
    try {
        await navigator.clipboard.writeText(key);
        const original = btn.textContent;
        btn.textContent = 'Copiado!';
        setTimeout(() => { btn.textContent = original; }, 1500);
    } catch (e) {
        alert('Falha ao copiar: ' + e.message);
    }
}

function copyResultKey() {
    const key = document.getElementById('result-key').textContent;
    copyKey(document.querySelector('#result-actions button'), key);
}

document.getElementById('gen-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const btn = document.getElementById('btn-generate');
    const data = new FormData(ev.target);
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader"></i> Gerando...';
    lucide.createIcons();

    const result = document.getElementById('result');
    const msg = document.getElementById('result-msg');
    const keyBox = document.getElementById('result-key');
    const meta = document.getElementById('result-meta');
    const actions = document.getElementById('result-actions');

    try {
        const res = await fetch('/generate', { method: 'POST', body: data });
        const json = await res.json();
        if (json.success) {
            result.classList.remove('error');
            result.classList.add('show');
            msg.textContent = 'Chave gerada com sucesso. Expira em ' + json.expires_at_human + '.';
            keyBox.textContent = json.key;
            meta.textContent = 'Validade: ' + json.days + ' dias  ·  Expira em ' + json.expires_at_human + '  ·  Salva no histórico.';
            actions.style.display = 'flex';
            // Reload history table
            setTimeout(() => location.reload(), 500);
        } else {
            result.classList.add('show', 'error');
            msg.textContent = 'Erro: ' + (json.error || 'desconhecido');
            keyBox.textContent = '';
            meta.textContent = '';
            actions.style.display = 'none';
        }
    } catch (e) {
        result.classList.add('show', 'error');
        msg.textContent = 'Erro de rede: ' + e.message;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="key"></i> Gerar chave';
        lucide.createIcons();
    }
});

// Check on boot if private_key exists
fetch('/status').then(r => r.json()).then(s => {
    if (!s.private_key_present) {
        document.getElementById('warn-no-key').classList.remove('hide');
        document.getElementById('btn-generate').disabled = true;
    }
});

lucide.createIcons();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    history = load_history()
    html = (HTML_TEMPLATE
            .replace("{{HISTORY_ROWS}}", render_history_rows(history))
            .replace("{{KEY_PATH}}", str(PRIVATE_KEY_PATH))
            .replace("{{MAX_HISTORY}}", str(MAX_HISTORY)))
    return HTMLResponse(html)


@app.get("/status")
async def status():
    return {"private_key_present": PRIVATE_KEY_PATH.exists()}


@app.post("/generate")
async def generate(
    hwid: str = Form(...),
    days: int = Form(DEFAULT_DAYS),
    customer: str = Form(""),
):
    hwid = hwid.strip()
    plan = FIXED_PLAN
    if not hwid:
        return JSONResponse({"success": False, "error": "Hardware ID e obrigatorio"})
    if days < 1 or days > 36500:
        return JSONResponse({"success": False, "error": "Validade fora do range (1 a 36500 dias)"})

    priv = load_private_key_safe()
    if priv is None:
        return JSONResponse({
            "success": False,
            "error": f"private_key.pem nao encontrado em {PRIVATE_KEY_PATH}"
        })

    key = generate_license_key(priv, hwid, plan, days)
    now = int(time.time())
    expires_at = now + days * 86400
    entry = {
        "key": key,
        "hwid": hwid,
        "plan": plan,
        "days": days,
        "customer": customer.strip(),
        "issued_at": now,
        "issued_at_human": datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M"),
        "expires_at": expires_at,
        "expires_at_human": datetime.fromtimestamp(expires_at).strftime("%Y-%m-%d"),
    }
    history = load_history()
    history.insert(0, entry)
    history = history[:MAX_HISTORY]
    save_history(history)

    return {
        "success": True,
        "key": key,
        "plan": plan,
        "days": days,
        "expires_at_human": entry["expires_at_human"],
    }


def open_browser_delayed():
    time.sleep(1.2)
    try:
        webbrowser.open(f"http://127.0.0.1:{PORT}")
    except Exception:
        pass


if __name__ == "__main__":
    if not PRIVATE_KEY_PATH.exists():
        print(f"AVISO: private_key.pem nao encontrado em {PRIVATE_KEY_PATH}")
        print("       A UI vai abrir mas o botao Gerar ficara desabilitado")
        print("       ate voce colocar a chave privada na pasta.")
    print(f"Keygen Web rodando em http://127.0.0.1:{PORT}")
    print("Pressione Ctrl+C para encerrar.")
    threading.Thread(target=open_browser_delayed, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
