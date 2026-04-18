// ZapManager Pro v4.0 - Core Script
let currentCampaignId = null;
window.importedContacts = [];

// --- Page Navigation ---
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(p => p.classList.remove('active'));
    
    const activePage = document.getElementById(pageId);
    if (activePage) activePage.classList.add('active');
    
    const navId = pageId.replace('page-', 'nav-');
    const navItem = document.getElementById(navId);
    if (navItem) navItem.classList.add('active');

    if (pageId === 'page-history') loadHistory();
    if (pageId === 'page-license') loadLicense();
}

// --- Contact Import & Flow ---
async function handleImport(file) {
    const uploadArea = document.getElementById('upload-area');
    if (!uploadArea) return;
    
    const fd = new FormData();
    fd.append('file', file);
    
    uploadArea.innerHTML = '<p><i data-lucide="loader" class="animate-spin" size="16"></i> Processando planilha...</p>';
    lucide.createIcons();

    try {
        const res = await fetch('/api/contacts/import', { method: 'POST', body: fd });
        const data = await res.json();
        
        if (data.success) {
            currentCampaignId = data.data.campaign_id;
            window.importedContacts = data.contacts;
            
            renderSummaryCards(data.data);
            renderContactsTable(data.contacts);
            renderVariableChips(data.contacts);
            updatePreview();
            
            uploadArea.classList.add('hidden');
            document.getElementById('import-summary').classList.remove('hidden');
        } else {
            alert(data.error || "Erro ao importar.");
            resetUploadArea();
        }
    } catch (e) {
        console.error(e);
        alert("Erro de conexão.");
        resetUploadArea();
    }
}

function resetUploadArea() {
    const area = document.getElementById('upload-area');
    if (area) {
        area.innerHTML = '<p>Arraste o arquivo .xlsx aqui ou <span class="link">clique para selecionar</span></p><p style="font-size:11px; color:var(--color-text-tertiary); margin-top:4px">nome, número, empresa e campos personalizados</p>';
        area.classList.remove('hidden');
    }
    document.getElementById('import-summary').classList.add('hidden');
}

function renderSummaryCards(summary) {
    const sumTotal = document.getElementById('sumTotal');
    const sumReady = document.getElementById('sumReady');
    const sumInvalid = document.getElementById('sumInvalid');
    const sumBlacklist = document.getElementById('sumBlacklist');
    
    if (sumTotal) sumTotal.textContent = summary.total || 0;
    if (sumReady) sumReady.textContent = summary.imported || 0;
    if (sumInvalid) sumInvalid.textContent = (summary.errors || []).length;
    if (sumBlacklist) sumBlacklist.textContent = summary.skipped_blacklist || 0;
}

function renderVariableChips(contacts) {
    const wrap = document.getElementById('var-chips');
    if (!wrap || !contacts || contacts.length === 0) return;
    
    const defaultVars = ['nome', 'empresa', 'numero', 'adicional1', 'adicional2', 'adicional3'];
    let extraVars = [];
    try {
        const extra = JSON.parse(contacts[0].extra_fields || '{}');
        extraVars = Object.keys(extra);
    } catch(e) {}
    
    const allVars = [...new Set([...defaultVars, ...extraVars])];
    wrap.innerHTML = allVars.map(v => `
        <span class="var-chip" onclick="insertVar('{${v}}')">{${v}}</span>
    `).join('');
}

// --- Table & Editing ---
function renderContactsTable(contacts) {
    const body = document.getElementById('contactsBody');
    if (!body) return;
    
    body.innerHTML = contacts.map((c, i) => {
        const isInvalid = c.status === 'INVÁLIDO' || !c.phone;
        const isBlacklist = c.status === 'BLACKLIST';
        const rowClass = isInvalid ? 'invalid' : isBlacklist ? 'blacklisted' : '';
        
        return `
        <tr class="${rowClass}" data-id="${c.id}">
            <td style="width:32px;padding:8px;color:var(--color-text-tertiary);font-size:12px">${i + 1}</td>
            <td class="editable-name" onclick="makeEditable(this, ${c.id}, 'name')"
                style="cursor:pointer" title="Clique para editar">
                ${c.name || '—'}
            </td>
            <td class="editable-phone phone" onclick="makeEditable(this, ${c.id}, 'phone')"
                style="cursor:pointer" title="Clique para editar">
                ${c.phone || '<span style="color:var(--color-danger-text)">Inválido</span>'}
            </td>
            <td style="color:var(--color-text-secondary)">${c.company || '—'}</td>
            <td>${getStatusBadge(c.status)}</td>
            <td style="width:40px;text-align:center">
                <button onclick="removeContact(${c.id}, this)"
                    style="background:none;border:none;cursor:pointer;
                           color:var(--color-text-tertiary);font-size:14px;
                           padding:2px 6px;border-radius:4px"
                    title="Remover contato">✕</button>
            </td>
        </tr>`;
    }).join('');
    
    lucide.createIcons();
}

function getStatusBadge(status) {
    const map = {
        'PENDENTE':  ['#FFF7E6', '#D46B08', 'Pendente'],
        'ENVIADO':   ['#F6FFED', '#389E0D', 'Enviado'],
        'ERRO':      ['#FFF1F0', '#CF1322', 'Erro'],
        'INVÁLIDO':  ['#FFF1F0', '#CF1322', 'Inválido'],
        'BLACKLIST': ['#F5F5F5', '#8C8C8C', 'Blacklist'],
    };
    const [bg, color, label] = map[status] || map['PENDENTE'];
    return `<span style="background:${bg};color:${color};padding:2px 8px;
                border-radius:20px;font-size:11px;font-weight:500;display:inline-block">${label}</span>`;
}

function makeEditable(cell, contactId, field) {
    if (cell.querySelector('input')) return;
    
    const original = cell.textContent.trim();
    const input = document.createElement('input');
    input.value = (original === '—' || original === 'Inválido') ? '' : original;
    input.className = "inline-edit-input";
    input.style.cssText = `
        width: 100%; border: 1.5px solid var(--color-brand);
        border-radius: 4px; padding: 2px 6px; font-size: 13px;
        background: var(--color-bg-surface); color: var(--color-text-primary);
        outline: none;
    `;
    cell.innerHTML = '';
    cell.appendChild(input);
    input.focus();
    input.select();
    
    async function save() {
        const newValue = input.value.trim();
        if (field === 'phone') {
            const res = await fetch('/api/contacts/validate-phone', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ phone: newValue })
            });
            const data = await res.json();
            const row = cell.closest('tr');
            
            if (data.valid) {
                cell.textContent = data.normalized;
                row.classList.remove('invalid');
                await updateContact(contactId, { phone: data.normalized });
            } else {
                cell.innerHTML = `<span style="color:var(--color-danger-text)">${newValue || 'Inválido'}</span>`;
                row.classList.add('invalid');
            }
        } else {
            cell.textContent = newValue || '—';
            await updateContact(contactId, { [field]: newValue });
        }
        // Atualiza objeto global para o preview
        const contact = window.importedContacts.find(c => c.id === contactId);
        if (contact) contact[field] = cell.textContent.trim();
        updatePreview();
    }
    
    input.addEventListener('blur', save);
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') input.blur();
        if (e.key === 'Escape') { cell.textContent = original; }
    });
}

async function updateContact(contactId, fields) {
    await fetch(`/api/contacts/${contactId}/update`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(fields)
    });
}

async function removeContact(contactId, btn) {
    if (!confirm("Remover este contato da lista?")) return;
    const row = btn.closest('tr');
    await fetch(`/api/contacts/${contactId}/remove`, { method: 'DELETE' });
    row.style.opacity = '0.3';
    setTimeout(() => {
        row.remove();
        window.importedContacts = window.importedContacts.filter(c => c.id !== contactId);
        updatePreview();
    }, 300);
}

// --- Message & Preview ---
const msgInput = document.getElementById('message-input');
const msgPreview = document.getElementById('message-preview');

if (msgInput) msgInput.addEventListener('input', updatePreview);

function updatePreview() {
    if (!msgInput || !msgPreview) return;
    let text = msgInput.value;
    if (!text) {
        msgPreview.innerHTML = '<span style="color:var(--color-text-tertiary)">Digite sua mensagem para preview...</span>';
        return;
    }
    
    // Pega o primeiro contato para o preview
    const c = window.importedContacts[0] || { name: 'João Silva', phone: '5511999998888', company: 'Exemplo LTDA' };
    
    let preview = text
        .replace(/{nome}/g, `<strong>${c.name || 'Cliente'}</strong>`)
        .replace(/{empresa}/g, `<strong>${c.company || 'Empresa'}</strong>`)
        .replace(/{numero}/g, `<strong>${c.phone || 'Número'}</strong>`);
    
    // Substituir campos extras se houver
    if (c.extra_fields) {
        try {
            const extra = JSON.parse(c.extra_fields);
            Object.keys(extra).forEach(k => {
                const reg = new RegExp(`{${k}}`, 'g');
                preview = preview.replace(reg, `<strong>${extra[k]}</strong>`);
            });
        } catch(e) {}
    }
        
    msgPreview.innerHTML = preview.replace(/\n/g, '<br>');
}

function insertVar(variable) {
    const ta = document.getElementById('message-input');
    if (!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    ta.value = ta.value.slice(0, start) + variable + ta.value.slice(end);
    ta.selectionStart = ta.selectionEnd = start + variable.length;
    ta.focus();
    updatePreview();
}

// --- Campaign Controls ---
async function startCampaign() {
    if (!window.importedContacts.length) return alert("Importe uma planilha primeiro.");
    
    const params = {
        campaign_id: currentCampaignId,
        message: document.getElementById('message-input').value,
        limit: 9999,
        min_interval: parseInt(document.getElementById('min-delay').value),
        max_interval: parseInt(document.getElementById('max-delay').value)
    };
    
    const res = await fetch('/api/campaign/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(params)
    });
    
    const data = await res.json();
    if (data.success || data.message) {
        document.getElementById('btnStart').disabled = true;
        document.getElementById('btnStop').disabled = false;
        document.getElementById('campaign-progress').classList.remove('hidden');
    } else {
        alert(data.error);
    }
}

async function stopCampaign() {
    await fetch('/api/campaign/stop', { method: 'POST' });
    document.getElementById('btnStart').disabled = false;
    document.getElementById('btnStop').disabled = true;
}

// Status Polling
setInterval(async () => {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.is_running) {
            const p = data.progress;
            const pct = Math.round((p.processed / (p.total || 1)) * 100);
            const bar = document.getElementById('progressBar');
            if (bar) bar.style.width = pct + '%';
            
            const pctText = document.getElementById('progPct');
            if (pctText) pctText.textContent = pct + '%';
            
            const sentText = document.getElementById('progSent');
            if (sentText) sentText.textContent = p.sent;
            
            const failedText = document.getElementById('progFailed');
            if (failedText) failedText.textContent = p.failed;
            
            const totalText = document.getElementById('progTotalCap');
            if (totalText) totalText.textContent = `Total: ${p.total}`;
        }
    } catch(e){}
}, 2000);

// --- SSE Logs ---
const logSource = new EventSource('/api/logs');
logSource.onmessage = (e) => {
    const box = document.getElementById('monitor-logs');
    if (!box) return;
    const parts = e.data.split('|');
    if (parts.length >= 2) {
        const level = parts[0].toLowerCase();
        const msg = parts.slice(1).join('|');
        const div = document.createElement('div');
        div.style.marginBottom = '4px';
        div.innerHTML = `<span style="color:#666">[${new Date().toLocaleTimeString()}]</span> <span class="log-${level}">${msg}</span>`;
        box.appendChild(div);
        box.scrollTop = box.scrollHeight;
    }
};

function clearLogs() { 
    const box = document.getElementById('monitor-logs');
    if (box) box.innerHTML = ''; 
}

// --- Utils ---
function toggleDelay() {
    const panel = document.getElementById('delay-panel');
    const icon = document.getElementById('delay-arrow-icon');
    if (!panel) return;
    panel.classList.toggle('hidden');
    if (panel.classList.contains('hidden')) icon.style.transform = 'rotate(0deg)';
    else icon.style.transform = 'rotate(90deg)';
}

async function loadHistory() {
    const res = await fetch('/api/campaigns/history');
    const list = await res.json();
    const body = document.getElementById('historyBody');
    if (!body) return;
    body.innerHTML = list.map(h => `
        <tr>
            <td><strong>${h.name}</strong></td>
            <td>${h.created_at}</td>
            <td>${h.total}</td>
            <td><span style="color:var(--color-success-text)">${h.sent}</span> / <span style="color:var(--color-danger-text)">${h.failed}</span></td>
            <td><button class="btn-primary" style="height:28px; font-size:11px; width:auto; padding:0 8px;" onclick="window.location.href='/api/campaign/${h.id}/export'">Relatório</button></td>
        </tr>
    `).join('');
}

async function loadLicense() {
    const res = await fetch('/api/license');
    const data = await res.json();
    const plan = document.getElementById('license-plan-name');
    const rem = document.getElementById('license-remaining');
    if (plan) plan.textContent = data.plan || "Plano Ativo";
    if (rem) rem.textContent = data.message || "Licença Vitalícia";
}

// Connector
function openConnector() {
    document.getElementById('connectorModal').classList.remove('hidden');
    checkConnector();
}
function closeConnector() { document.getElementById('connectorModal').classList.add('hidden'); }
async function checkConnector() {
    const res = await fetch('/api/connector');
    const data = await res.json();
    const qrl = document.getElementById('qrLoading');
    const qrc = document.getElementById('qrContainer');
    const qrs = document.getElementById('connSuccess');
    
    if (data.connected) {
        if (qrl) qrl.classList.add('hidden');
        if (qrc) qrc.classList.add('hidden');
        if (qrs) qrs.classList.remove('hidden');
    } else if (data.qr) {
        if (qrl) qrl.classList.add('hidden');
        if (qrc) qrc.classList.remove('hidden');
        const img = document.getElementById('qrImage');
        if (img) img.src = data.qr;
    }
}

// Drag & Drop Listeners
const dropZone = document.getElementById('upload-area');
const fileInput = document.getElementById('fileExcel');

if (fileInput) {
    fileInput.addEventListener('change', (e) => { if (e.target.files.length) handleImport(e.target.files[0]); });
}

if (dropZone) {
    dropZone.addEventListener('dragover', (e) => { 
        e.preventDefault(); 
        dropZone.classList.add('drag-over'); 
    });

    dropZone.addEventListener('dragleave', () => { 
        dropZone.classList.remove('drag-over'); 
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) handleImport(e.dataTransfer.files[0]);
    });
}
