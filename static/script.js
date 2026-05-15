// ZapManager Pro v4.0 - Core Script
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

const getToken = () =>
    document.querySelector('meta[name="zap-token"]')
        ?.getAttribute('content') ?? '';

(function() {
    const _fetch = window.fetch.bind(window);
    window.fetch = function(url, opts) {
        opts = opts || {};
        opts.headers = Object.assign({}, opts.headers || {}, {
            'X-Session-Token': getToken()
        });
        return _fetch(url, opts);
    };
})();

/**
 * Wrapper central para todas as chamadas à API.
 * Injeta token, trata erros de rede e HTTP.
 */
async function api(path, opts = {}) {
    const isFormData = opts.body instanceof FormData;
    opts.headers = {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(opts.headers || {}),
    };
    if (getToken()) {
        opts.headers['X-Session-Token'] = getToken();
    }
    try {
        const res = await fetch(path, opts);
        const json = await res.json().catch(() => ({}));
        if (!res.ok) {
            const msg = json.error || `Erro HTTP ${res.status}`;
            showToast(msg, 'error');
            throw new Error(msg);
        }
        return json;
    } catch (e) {
        if (e.name === 'TypeError') {
            showToast('Sem conexão com o servidor', 'error');
        }
        throw e;
    }
}

/**
 * Versão silenciosa — não exibe toast em erro.
 * Usar para polling e operações em background.
 */
async function apiBg(path, opts = {}) {
    opts.headers = {
        'Content-Type': 'application/json',
        ...(opts.headers || {}),
    };
    if (getToken()) {
        opts.headers['X-Session-Token'] = getToken();
    }
    try {
        const res = await fetch(path, opts);
        return await res.json().catch(() => ({}));
    } catch {
        return {};
    }
}

let currentCampaignId = null;
window.importedContacts = [];
window.activeCampaignId = null;

function getFilename(path) {
    if (!path) return '';
    return path.split(/[\\/]/).pop();
}

async function uploadContactAttachment(contactId, input) {
    const file = input.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
        alert('Apenas arquivos PDF são permitidos.');
        input.value = '';
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const data = await api(`/api/contacts/${contactId}/attachment`, {
            method: 'POST',
            body: formData
        });

        if (data.success) {
            const contact = window.importedContacts?.find(c => c.id === contactId);
            if (contact) contact.attachment_path = data.path;
            renderContactsTable(window.importedContacts);
            showToast(`PDF "${data.filename}" anexado com sucesso.`, 'success');
        } else {
            alert('Erro ao anexar PDF: ' + data.error);
        }
    } catch (err) {
        alert('Erro ao enviar arquivo: ' + err.message);
    }
}

async function removeContactAttachment(contactId, btn) {
    try {
        const data = await api(`/api/contacts/${contactId}/attachment`, {
            method: 'DELETE'
        });
        if (data.success) {
            const contact = window.importedContacts?.find(c => c.id === contactId);
            if (contact) contact.attachment_path = null;
            renderContactsTable(window.importedContacts);
            showToast('Anexo removido.', 'info');
        }
    } catch (err) {
        alert('Erro ao remover anexo: ' + err.message);
    }
}

function showToast(message, type = 'info') {
    const colors = {
        success: { bg: 'var(--color-success-bg)', border: 'var(--color-success-text)', text: 'var(--color-success-text)' },
        info:    { bg: 'var(--color-brand-light)', border: 'var(--color-brand)', text: 'var(--color-brand)' },
        warning: { bg: 'var(--color-warning-bg)', border: 'var(--color-warning)', text: 'var(--color-warning)' },
        error:   { bg: 'var(--color-danger-bg)', border: 'var(--color-danger-text)', text: 'var(--color-danger-text)' },
    };
    const c = colors[type] || colors.info;
    const toast = document.createElement('div');
    toast.style.cssText = `
        position:fixed; bottom:24px; right:24px; z-index:9999;
        padding:12px 16px; border-radius:8px; font-size:13px;
        background:${c.bg}; border-left:3px solid ${c.border};
        color:${c.text}; font-weight:500;
        box-shadow:0 4px 12px rgba(0,0,0,0.1);
        max-width:320px;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

async function exportCampaign(campaignId) {
    if (!campaignId) {
        alert('Nenhuma campanha para exportar.');
        return;
    }
    const btn = document.getElementById('btn-export');
    try {
        if (btn) { btn.textContent = 'Gerando...'; btn.disabled = true; }

        const response = await fetch(`/api/campaign/${campaignId}/export`);
        if (!response.ok) throw new Error('Erro ao gerar relatório');

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `relatorio_campanha_${campaignId}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (err) {
        alert('Erro ao exportar: ' + err.message);
    } finally {
        if (btn) { btn.textContent = '↓ Exportar Relatório'; btn.disabled = false; }
    }
}

async function downloadTemplateWorkbook() {
    try {
        const response = await fetch('/api/template/contacts.xlsx');
        if (!response.ok) throw new Error('Erro ao baixar planilha modelo');

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'contatos_modelo.xlsx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('Planilha modelo baixada.', 'success');
        return true;
    } catch (err) {
        showToast(err.message || 'Erro ao baixar planilha modelo', 'error');
        return false;
    }
}

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
        const data = await api('/api/contacts/import', { method: 'POST', body: fd });
        
        if (data.success) {
            currentCampaignId = data.data.campaign_id;
            window.importedContacts = data.contacts;
            
            renderSummaryCards(data.data);
            showImportDiscardToast(data.data);
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
    const sumDuplicates = document.getElementById('sumDuplicates');
    const errorCount = summary.error_count ?? (summary.errors || []).length;

    if (sumTotal) sumTotal.textContent = summary.total || 0;
    if (sumReady) sumReady.textContent = summary.imported || 0;
    if (sumInvalid) sumInvalid.textContent = errorCount;
    if (sumBlacklist) sumBlacklist.textContent = summary.skipped_blacklist || 0;
    if (sumDuplicates) sumDuplicates.textContent = summary.duplicates_detected || 0;
}

function showImportDiscardToast(summary) {
    const errorCount = summary.error_count ?? (summary.errors || []).length;
    const parts = [];

    if (summary.duplicates_detected) parts.push(`${summary.duplicates_detected} duplicada(s) sera(o) enviada(s)`);
    if (errorCount) parts.push(`${errorCount} com erro`);
    if (summary.skipped_blacklist) parts.push(`${summary.skipped_blacklist} em blacklist`);

    if (parts.length) {
        const level = errorCount ? 'warning' : 'info';
        showToast(`Importacao: ${parts.join(', ')}.`, level);
        if (summary.errors && summary.errors.length) console.warn('Linhas com erro:', summary.errors);
    }
    if (summary.duplicate_phones && summary.duplicate_phones.length) {
        console.info('Numeros duplicados na lista:', summary.duplicate_phones);
    }
}

function renderVariableChips(contacts) {
    const wrap = document.getElementById('var-chips');
    if (!wrap || !contacts || contacts.length === 0) return;
    
    const defaultVars = ['nome', 'numero', 'empresa', 'adicional1', 'adicional2', 'adicional3'];
    let extraVars = [];
    try {
        const extra = JSON.parse(contacts[0].extra_fields || '{}');
        extraVars = Object.keys(extra);
    } catch(e) {}
    
    const allVars = [...new Set([...defaultVars, ...extraVars])];
    wrap.innerHTML = allVars.map(v => `
        <span class="var-chip" onclick="insertVar('{${escapeHtml(v)}}')">{${escapeHtml(v)}}</span>
    `).join('');
}

// --- Table & Editing ---
function renderContactsTable(contacts) {
    const body = document.getElementById('contactsBody');
    if (!body) return;

    const phoneCounts = contacts.reduce((counts, contact) => {
        if (contact.phone) counts.set(contact.phone, (counts.get(contact.phone) || 0) + 1);
        return counts;
    }, new Map());
    const duplicatePhones = new Set([...phoneCounts].filter(([, count]) => count > 1).map(([phone]) => phone));
    
    body.innerHTML = contacts.map((c, i) => {
        const isInvalid = c.status === 'INVÁLIDO' || !c.phone;
        const isBlacklist = c.status === 'BLACKLIST';
        const isDuplicate = c.phone && duplicatePhones.has(c.phone);
        const rowClasses = [];
        if (isInvalid) rowClasses.push('invalid');
        if (isBlacklist) rowClasses.push('blacklisted');
        if (isDuplicate) rowClasses.push('row-duplicate');
        const phoneValue = escapeHtml(c.phone) || '<span style="color:var(--color-danger-text)">Inválido</span>';
        const phoneClass = isDuplicate ? 'editable-phone phone duplicate-phone' : 'editable-phone phone';
        
        return `
        <tr class="${rowClasses.join(' ')}" data-id="${c.id}">
            <td style="width:32px;padding:8px;color:var(--color-text-tertiary);font-size:12px">${i + 1}</td>
            <td class="editable-name" onclick="makeEditable(this, ${c.id}, 'name')"
                style="cursor:pointer" title="Clique para editar">
                ${escapeHtml(c.name || '—')}
            </td>
            <td class="${phoneClass}" onclick="makeEditable(this, ${c.id}, 'phone')"
                style="cursor:pointer" title="Clique para editar">
                ${phoneValue}
            </td>
            <td style="color:var(--color-text-secondary)">${escapeHtml(c.company || '—')}</td>
            <td>${getStatusBadge(c.status)}</td>
            <td style="width:44px; text-align:center; padding:4px 8px;">
                <div style="position:relative; display:inline-block;">
                    <label title="${c.attachment_path ? 'Trocar PDF: ' + getFilename(c.attachment_path) : 'Anexar PDF'}"
                        style="cursor:pointer; display:flex; align-items:center; justify-content:center;
                               width:28px; height:28px; border-radius:4px;
                               background:${c.attachment_path ? 'var(--color-success-bg)' : 'var(--color-bg-tertiary)'};
                               border:1px solid ${c.attachment_path ? 'var(--color-success-text)' : 'var(--color-border)'};
                               transition:background 120ms ease;">
                        <input type="file" accept=".pdf"
                            style="display:none"
                            onchange="uploadContactAttachment(${c.id}, this)">
                        <span style="font-size:14px">📎</span>
                    </label>
                    ${c.attachment_path ? `
                    <button onclick="removeContactAttachment(${c.id}, this)"
                        title="Remover PDF"
                        style="position:absolute; top:-6px; right:-6px;
                               width:14px; height:14px; border-radius:50%;
                               background:var(--color-danger); color:white;
                               border:none; cursor:pointer; font-size:9px;
                               display:flex; align-items:center; justify-content:center;
                               line-height:1; padding:0;">✕</button>
                    ` : ''}
                </div>
            </td>
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
            const data = await apiBg('/api/contacts/validate-phone', {
                method: 'POST',
                body: JSON.stringify({ phone: newValue })
            });
            const row = cell.closest('tr');
            
            if (data.valid) {
                cell.textContent = data.normalized;
                row.classList.remove('invalid');
                await updateContact(contactId, { phone: data.normalized });
            } else {
                cell.innerHTML = `<span style="color:var(--color-danger-text)">${escapeHtml(newValue || 'Inválido')}</span>`;
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
    await api(`/api/contacts/${contactId}/update`, {
        method: 'POST',
        body: JSON.stringify(fields)
    });
}

async function removeContact(contactId, btn) {
    if (!confirm("Remover este contato da lista?")) return;
    const row = btn.closest('tr');
    await api(`/api/contacts/${contactId}/remove`, { method: 'DELETE' });
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

    const c = window.importedContacts[0] || { name: 'João Silva', phone: '5511999998888', company: 'Exemplo LTDA' };

    const spintaxRegex = /\{([^{}]+\|[^{}]*)\}/g;
    let processed = text;
    while (spintaxRegex.test(processed)) {
        processed = processed.replace(spintaxRegex, (_, group) => group.split('|')[0]);
    }

    // Convenção alinhada com database/services/template_service.py: placeholders usam 1 chave.
    const substitutions = {
        nome: c.name || 'Cliente',
        empresa: c.company || 'Empresa',
        numero: c.phone || 'Número',
    };

    if (c.extra_fields) {
        try {
            const extra = typeof c.extra_fields === 'string' ? JSON.parse(c.extra_fields) : c.extra_fields;
            Object.assign(substitutions, extra);
        } catch(e) {}
    }

    let safe = escapeHtml(processed);
    for (const [k, v] of Object.entries(substitutions)) {
        const escapedKey = k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const reg = new RegExp(`\\{${escapedKey}\\}`, 'g');
        safe = safe.replace(reg, `<strong>${escapeHtml(String(v))}</strong>`);
    }

    msgPreview.innerHTML = safe.replace(/\n/g, '<br>');
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
    
    const data = await api('/api/campaign/start', {
        method: 'POST',
        body: JSON.stringify(params)
    });
    if (data.success || data.message) {
        window.activeCampaignId = data.campaign_id || currentCampaignId;
        document.getElementById('btnStart').disabled = true;
        document.getElementById('btnStop').disabled = false;
        document.getElementById('campaign-progress').classList.remove('hidden');
    } else {
        alert(data.error);
    }
}

async function stopCampaign() {
    await api('/api/campaign/stop', { method: 'POST' });
    document.getElementById('btnStart').disabled = false;
    document.getElementById('btnStop').disabled = true;
}

// Status Polling
setInterval(async () => {
    try {
        const data = await apiBg('/api/status');
        if (data.progress) {
            const p = data.progress;
            const pct = Math.round((p.processed / (p.total || 1)) * 100);
            const bar = document.getElementById('progressBar');
            if (bar) bar.style.width = pct + '%';
            
            const pctText = document.getElementById('progPct');
            if (pctText) pctText.textContent = pct + '%';
            
            const sentText = document.getElementById('progSent');
            if (sentText) sentText.textContent = p.sent || 0;
            
            const failedText = document.getElementById('progFailed');
            if (failedText) failedText.textContent = p.failed || 0;
            
            const totalText = document.getElementById('progTotalCap');
            if (totalText) totalText.textContent = `Total: ${p.total || 0}`;
            
            const statusText = document.getElementById('progStatus');
            if (statusText) statusText.textContent = p.status || 'Aguardando';

            // Gerenciar visibilidade do card de progresso
            const progCard = document.getElementById('campaign-progress');
            if (progCard && (data.is_running || data.was_stopped || p.processed > 0)) {
                progCard.classList.remove('hidden');
            }
        }
    } catch(e){}
}, 2000);

// --- SSE Logs ---
const LOG_MAX_LINES = 200;
const logSource = new EventSource('/api/logs?token=' + (getToken() || ''));
logSource.onmessage = (e) => {
    const box = document.getElementById('monitor-logs');
    if (!box) return;
    const parts = e.data.split('|');
    if (parts.length >= 2) {
        const level = parts[0].toLowerCase();
        const msg = parts.slice(1).join('|');
        const div = document.createElement('div');
        div.classList.add('log-line');
        div.style.marginBottom = '4px';
        div.innerHTML = `<span style="color:#666">[${new Date().toLocaleTimeString()}]</span> <span class="log-${level}">${escapeHtml(msg)}</span>`;
        box.appendChild(div);

        // L-B1: Rolling window — keep last 200 lines
        while (box.childElementCount > LOG_MAX_LINES) {
            box.removeChild(box.firstChild);
        }

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

function toggleSendWindow() {
    const panel = document.getElementById('send-window-panel');
    const icon = document.getElementById('send-window-arrow-icon');
    if (!panel) return;
    panel.classList.toggle('hidden');
    if (icon) icon.style.transform = panel.classList.contains('hidden') ? 'rotate(0deg)' : 'rotate(90deg)';
}

async function loadSendWindowConfig() {
    const result = await apiBg('/api/config/send-window');
    if (result && result.data) {
        renderSendWindowConfig(result.data, result.state);
    }
}

function collectSendWindowConfig() {
    const days = [...document.querySelectorAll('.send-window-days input:checked')]
        .map(input => Number(input.value));
    return {
        enabled: Boolean(document.getElementById('send-window-enabled')?.checked),
        start: document.getElementById('send-window-start')?.value || '08:00',
        end: document.getElementById('send-window-end')?.value || '20:00',
        days
    };
}

function renderSendWindowConfig(config, state = {}) {
    const enabled = document.getElementById('send-window-enabled');
    const start = document.getElementById('send-window-start');
    const end = document.getElementById('send-window-end');
    if (!enabled || !start || !end || !config) return;

    enabled.checked = Boolean(config.enabled);
    start.value = config.start || '08:00';
    end.value = config.end || '20:00';

    const selected = new Set(config.days || []);
    document.querySelectorAll('.send-window-days input').forEach(input => {
        input.checked = selected.has(Number(input.value));
    });

    const summary = document.getElementById('send-window-summary');
    if (summary) {
        const daysText = formatSendWindowDays(config.days || []);
        const stateText = config.enabled
            ? (state.allowed ? 'envios liberados agora' : 'fora da janela atual')
            : 'janela desativada';
        summary.textContent = `${config.enabled ? 'Ativa' : 'Inativa'}: ${config.start}–${config.end}, ${daysText}. ${stateText}.`;
    }
}

function formatSendWindowDays(days) {
    const names = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];
    if (!days.length) return 'sem dias selecionados';
    return days.map(day => names[day]).filter(Boolean).join(', ');
}

async function saveSendWindowConfig() {
    try {
        const result = await api('/api/config/send-window', {
            method: 'POST',
            body: JSON.stringify(collectSendWindowConfig())
        });
        renderSendWindowConfig(result.data, result.state);
        showToast('Janela de envio salva.', 'success');
    } catch (err) {
        showToast(err.message || 'Erro ao salvar janela de envio', 'error');
    }
}

// --- History Logic ---
let historyCache = [];
let historyFiltersInitialized = false;

function initHistoryFilters() {
    if (historyFiltersInitialized) return;
    
    const searchInput = document.getElementById('historySearch');
    const dateFrom = document.getElementById('historyDateFrom');
    const dateTo = document.getElementById('historyDateTo');
    const sortSelect = document.getElementById('historySort');
    const statusSelect = document.getElementById('historyStatus');
    const clearBtn = document.getElementById('historyClearFilters');
    
    if (searchInput) searchInput.addEventListener('input', applyHistoryFilters);
    if (dateFrom) dateFrom.addEventListener('change', applyHistoryFilters);
    if (dateTo) dateTo.addEventListener('change', applyHistoryFilters);
    if (sortSelect) sortSelect.addEventListener('change', applyHistoryFilters);
    if (statusSelect) statusSelect.addEventListener('change', applyHistoryFilters);
    
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            if (dateFrom) dateFrom.value = '';
            if (dateTo) dateTo.value = '';
            if (sortSelect) sortSelect.value = 'date_desc';
            if (statusSelect) statusSelect.value = 'all';
            applyHistoryFilters();
        });
    }
    
    historyFiltersInitialized = true;
}

function applyHistoryFilters() {
    const query = document.getElementById('historySearch')?.value.toLowerCase() || '';
    const from = document.getElementById('historyDateFrom')?.value || '';
    const to = document.getElementById('historyDateTo')?.value || '';
    const sortMode = document.getElementById('historySort')?.value || 'date_desc';
    const statusCode = document.getElementById('historyStatus')?.value || 'all';
    
    const filtered = historyCache.filter(h => {
        // Text filter
        const matchesText = !query || 
            h.name.toLowerCase().includes(query) || 
            (h.created_at && h.created_at.toLowerCase().includes(query));
        
        // Date filter
        const itemDateStr = h.created_at ? h.created_at.split(' ')[0] : '';
        const matchesFrom = !from || (itemDateStr >= from);
        const matchesTo = !to || (itemDateStr <= to);
        
        // Status filter
        let matchesStatus = true;
        if (statusCode === 'successful') {
            matchesStatus = (h.sent > 0 && (h.failed || 0) === 0 && (h.pending || 0) === 0 && (h.invalid || 0) === 0);
        } else if (statusCode === 'failed') {
            matchesStatus = (h.failed || 0) > 0;
        } else if (statusCode === 'pending') {
            matchesStatus = (h.pending || 0) > 0;
        } else if (statusCode === 'invalid') {
            matchesStatus = (h.invalid || 0) > 0;
        }
        
        return matchesText && matchesFrom && matchesTo && matchesStatus;
    });
    
    const sorted = sortHistoryItems(filtered, sortMode);
    renderHistoryRows(sorted);
}

function sortHistoryItems(list, mode) {
    const items = [...list];
    
    switch (mode) {
        case 'date_desc':
            items.sort((a, b) => b.created_at.localeCompare(a.created_at));
            break;
        case 'date_asc':
            items.sort((a, b) => a.created_at.localeCompare(b.created_at));
            break;
        case 'rate_desc':
            items.sort((a, b) => (b.delivery_rate || 0) - (a.delivery_rate || 0));
            break;
        case 'rate_asc':
            items.sort((a, b) => (a.delivery_rate || 0) - (b.delivery_rate || 0));
            break;
        case 'failed_desc':
            items.sort((a, b) => (b.failed || 0) - (a.failed || 0));
            break;
        case 'failed_asc':
            items.sort((a, b) => (a.failed || 0) - (b.failed || 0));
            break;
    }
    
    return items;
}

function renderHistoryRows(list) {
    const body = document.getElementById('historyBody');
    const countEl = document.getElementById('historyResultCount');
    const emptyState = document.getElementById('historyEmptyState');
    const tableWrap = document.getElementById('historyTableWrap');
    
    if (!body) return;
    
    // Update count
    if (countEl) {
        if (list.length === 0) {
            countEl.textContent = 'Nenhuma campanha encontrada';
        } else {
            countEl.textContent = `${list.length} ${list.length === 1 ? 'campanha' : 'campanhas'}`;
        }
    }
    
    // Toggle empty state
    if (list.length === 0) {
        if (emptyState) emptyState.classList.remove('hidden');
        if (tableWrap) tableWrap.classList.add('hidden');
        return;
    } else {
        if (emptyState) emptyState.classList.add('hidden');
        if (tableWrap) tableWrap.classList.remove('hidden');
    }
    
    body.innerHTML = list.map(h => {
        // Compute status badge
        let badgeClass = 'idle';
        let badgeText = 'Idle';
        
        const sent = h.sent || 0;
        const failed = h.failed || 0;
        const pending = h.pending || 0;
        const invalid = h.invalid || 0;
        
        if (sent > 0 && failed === 0 && pending === 0 && invalid === 0) {
            badgeClass = 'successful';
            badgeText = 'Sucesso';
        } else if (failed > 0 || invalid > 0) {
            badgeClass = 'issues';
            badgeText = 'Problemas';
        } else if (pending > 0) {
            badgeClass = 'pending';
            badgeText = 'Pendente';
        }

        return `
        <tr>
            <td><strong>${escapeHtml(h.name)}</strong></td>
            <td><span class="status-badge ${badgeClass}">${badgeText}</span></td>
            <td>${h.created_at}</td>
            <td>${h.total_contacts}</td>
            <td><span style="color:var(--color-success-text)">${sent}</span> / <span style="color:var(--color-danger-text)">${failed}</span></td>
            <td><strong style="color: ${h.delivery_rate >= 80 ? 'var(--color-success-text)' : h.delivery_rate >= 50 ? '#d4b106' : 'var(--color-danger-text)'}">${h.delivery_rate ?? 0}%</strong></td>
            <td>
                <div style="display:flex; gap:4px">
                    <button onclick="openHistoryDetails(${h.id})"
                        style="padding:4px 8px; border-radius:4px;
                               border:1px solid var(--color-border);
                               background:var(--color-bg-primary);
                               color:var(--color-brand);
                               font-size:12px; cursor:pointer;"
                        title="Ver contatos e detalhes">
                        <i data-lucide="eye" size="12"></i>
                    </button>
                    <button onclick="exportCampaign(${h.id})"
                        style="padding:4px 12px; border-radius:4px;
                               border:1px solid var(--color-border);
                               background:var(--color-bg-primary);
                               color:var(--color-text-secondary);
                               font-size:12px; cursor:pointer;"
                        title="Exportar Excel">
                        ↓ Relatório
                    </button>
                </div>
            </td>
        </tr>
    `}).join('');
    lucide.createIcons();
}

async function loadHistory() {
    initHistoryFilters();
    const data = await apiBg('/api/campaigns/history');
    historyCache = data.data || [];
    applyHistoryFilters();
}

// --- History Details Modal Logic ---
window.viewingCampaignId = null;

async function openHistoryDetails(id) {
    window.viewingCampaignId = id;
    const modal = document.getElementById('historyDetailsModal');
    if (!modal) return;
    
    modal.classList.remove('hidden');
    document.getElementById('det-contacts-body').innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px">Carregando...</td></tr>';

    try {
        const result = await api(`/api/campaign/${id}/details`);
        
        if (result.success) {
            const { campaign, contacts } = result.data;
            
            document.getElementById('details-campaign-name').textContent = campaign.name;
            document.getElementById('details-campaign-date').textContent = `Iniciada em: ${campaign.created_at || '—'}`;
            
            // Stats
            document.getElementById('det-total').textContent = campaign.total_contacts;
            document.getElementById('det-sent').textContent = campaign.sent;
            document.getElementById('det-failed').textContent = campaign.failed;
            document.getElementById('det-invalid').textContent = campaign.invalid;

            // Render Table
            const body = document.getElementById('det-contacts-body');
            body.innerHTML = contacts.map(c => `
                <tr>
                    <td>${escapeHtml(c.name || '—')}</td>
                    <td class="phone">${escapeHtml(c.phone)}</td>
                    <td>${getStatusBadge(c.status)}</td>
                    <td style="font-size:11px; color:var(--color-text-secondary)">${escapeHtml(c.error_message || c.observation || '—')}</td>
                </tr>
            `).join('');
            
            // Toggle Retry button
            const btnRetry = document.getElementById('btn-retry-failed');
            if (campaign.failed > 0) {
                btnRetry.classList.remove('hidden');
            } else {
                btnRetry.classList.add('hidden');
            }
        }
    } catch (e) {
        alert("Erro ao carregar detalhes: " + e.message);
    }
}

function closeHistoryDetails() {
    document.getElementById('historyDetailsModal').classList.add('hidden');
}

async function retryFailedMessages() {
    const id = window.viewingCampaignId;
    if (!id) return;
    
    if (!confirm("Isso irá resetar os contatos com erro e iniciar os disparos imediatamente. Deseja continuar?")) return;

    try {
        // Pega as configurações de intervalo da tela principal como base
        const params = {
            min_interval: parseInt(document.getElementById('min-delay').value),
            max_interval: parseInt(document.getElementById('max-delay').value)
        };

        const data = await api(`/api/campaign/${id}/retry`, {
            method: 'POST',
            body: JSON.stringify(params)
        });

        if (data.success) {
            showToast(data.message, 'success');
            closeHistoryDetails();
            showPage('page-campaigns');
            // Ativa o acompanhamento do progresso
            window.activeCampaignId = id;
            document.getElementById('btnStart').disabled = true;
            document.getElementById('btnStop').disabled = false;
            document.getElementById('campaign-progress').classList.remove('hidden');
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert("Erro ao tentar re-envio: " + e.message);
    }
}

async function loadLicense() {
    const data = await apiBg('/api/license/status');
    renderLicenseData(data.data || data);
}

function renderLicenseData(data) {
  const badge = document.getElementById('license-badge');
  const isTrial = data.status === 'trial';
  const isValid = data.status === 'active' || data.status === 'trial';

  if (isTrial) {
    badge.textContent = 'Trial';
    badge.className = 'license-status-badge trial';
  } else if (data.status === 'active') {
    badge.textContent = 'Ativa';
    badge.className = 'license-status-badge active';
  } else {
    badge.textContent = data.status === 'expired' ? 'Expirada' : 'Inválida';
    badge.className = 'license-status-badge expired';
  }

  const planEl = document.getElementById('license-plan-name');
  if (planEl) {
    const planMap = { 'starter': 'Starter', 'pro': 'Pro', 'agency': 'Agency', 'trial': 'Versão Trial' };
    planEl.textContent = planMap[data.plan] || (data.plan ? data.plan.toUpperCase() : 'Não Ativado');
  }

  const hwEl = document.getElementById('license-hardware-id');
  if (hwEl) {
    hwEl.textContent = data.hardware_id || '—';
  }

  const expiryEl = document.getElementById('license-expires-on');
  const expiryText = document.getElementById('license-expiry-text');
  if (expiryEl && (data.expires_at || data.days_remaining !== undefined)) {
    if (data.expires_at) {
        const date = new Date(data.expires_at * 1000);
        expiryEl.textContent = date.toLocaleDateString('pt-BR');
    } else if (data.days_remaining !== undefined) {
        const date = new Date();
        date.setDate(date.getDate() + data.days_remaining);
        expiryEl.textContent = date.toLocaleDateString('pt-BR');
    }
    if (expiryText) expiryText.textContent = data.message || (isValid ? 'Sua licença está ativa.' : 'Licença expirada.');
  } else if (expiryEl) {
    expiryEl.textContent = '—';
  }

  const trialSection = document.getElementById('license-trial-section');
  if (trialSection) {
    if (isTrial && data.days_remaining !== undefined) {
      trialSection.style.display = 'block';
      const total = data.trial_days || 7;
      const remaining = data.days_remaining;
      const used = total - remaining;
      const pct = Math.max(0, Math.min(100, (used / total) * 100));
      const trialDaysEl = document.getElementById('license-trial-days');
      if (trialDaysEl) {
        trialDaysEl.textContent = remaining + ' dia' + (remaining !== 1 ? 's' : '') + ' restantes';
      }
      const progressBarEl = document.getElementById('license-progress-bar');
      if (progressBarEl) {
        progressBarEl.style.width = pct + '%';
      }
    } else {
      trialSection.style.display = 'none';
    }
  }
}

function copyHWID() {
    const hwid = document.getElementById('license-hardware-id').textContent;
    if (!hwid || hwid === '...') return;
    navigator.clipboard.writeText(hwid);
    const btn = document.querySelector('.btn-copy-hwid');
    const oldText = btn.textContent;
    btn.textContent = 'Copiado!';
    setTimeout(() => btn.textContent = oldText, 2000);
}

async function activateLicense() {
    const key = document.getElementById('license-key-input').value.trim();
    const feedback = document.getElementById('license-activate-feedback');
    if (!key) return;
    try {
        const data = await api('/api/license/activate', {
            method: 'POST',
            body: JSON.stringify({ key })
        });
        if (data.success) {
            feedback.style.color = 'var(--color-success-text)';
            feedback.textContent = 'Ativada com sucesso!';
            loadLicense();
        } else {
            feedback.style.color = 'var(--color-danger-text)';
            feedback.textContent = data.data?.error_message || 'Erro ao ativar';
        }
    } catch (e) {
        feedback.style.color = 'var(--color-danger-text)';
        feedback.textContent = 'Erro de comunicação';
    }
}

// Connector
function openConnector() {
    document.getElementById('connectorModal').classList.remove('hidden');
    checkConnector();
}
function closeConnector() { document.getElementById('connectorModal').classList.add('hidden'); }

async function checkConnector() {
    let res = await apiBg('/api/connector');
    const data = res.data;
    if (!data) return;
    
    const qrl = document.getElementById('qrLoading');
    const qrc = document.getElementById('qrContainer');
    const qrs = document.getElementById('connSuccess');
    const nodeOffline = document.getElementById('connectorNodeOffline');
    const sidebarBtn = document.querySelector('.nav-item[onclick="openConnector()"]');
    
    if (nodeOffline) {
        nodeOffline.classList.toggle('hidden', data.node_online !== false);
    }

    if (data.connected) {
        if (qrl) qrl.classList.add('hidden');
        if (qrc) qrc.classList.add('hidden');
        if (qrs) qrs.classList.remove('hidden');
        if (sidebarBtn) {
            sidebarBtn.style.color = 'var(--color-success-text)';
            sidebarBtn.title = 'WhatsApp Conectado';
        }
    } else if (data.qr) {
        if (qrl) qrl.classList.add('hidden');
        if (qrc) qrc.classList.remove('hidden');
        if (qrs) qrs.classList.add('hidden');
        const img = document.getElementById('qrImage');
        if (img) img.src = data.qr;
        if (sidebarBtn) {
            sidebarBtn.style.color = '';
            sidebarBtn.title = 'Conectar WhatsApp';
        }
    } else {
        if (qrl) {
            qrl.classList.remove('hidden');
            const p = qrl.querySelector('p');
            if (p) {
                p.textContent = data.node_online === false
                    ? 'Motor Node offline. Aguardando reinicialização...'
                    : 'Sincronizando chats (Pode levar até 1 minuto)...';
            }
        }
        if (qrc) qrc.classList.add('hidden');
        if (qrs) qrs.classList.add('hidden');
        if (sidebarBtn) {
            sidebarBtn.style.color = '';
            sidebarBtn.title = 'Conectar WhatsApp';
        }
    }
    
    // Polling if modal is open and not connected
    const modal = document.getElementById('connectorModal');
    if (modal && !modal.classList.contains('hidden') && !data.connected) {
        setTimeout(checkConnector, 2000);
    }
}

async function resetWhatsAppSession() {
    if (!confirm('Isto vai apagar a sessao salva e gerar um novo QR Code. Continuar?')) return;

    const data = await api('/api/whatsapp/reset', { method: 'POST' });
    if (data.success) {
        showToast('Sessao resetada. Aguardando novo QR...', 'info');
        const qrLoading = document.getElementById('qrLoading');
        const qrContainer = document.getElementById('qrContainer');
        const connSuccess = document.getElementById('connSuccess');
        if (qrLoading) qrLoading.classList.remove('hidden');
        if (qrContainer) qrContainer.classList.add('hidden');
        if (connSuccess) connSuccess.classList.add('hidden');
        setTimeout(checkConnector, 3000);
    } else {
        showToast(data.error || 'Falha ao resetar sessao', 'error');
    }
}

let onboardingStep = 1;
let onboardingTimer = null;
let onboardingAutoAdvanced = false;

async function initOnboarding() {
    const wizard = document.getElementById('onboardingWizard');
    if (!wizard) return;
    const result = await apiBg('/api/onboarding/status');
    const data = result.data || result;
    if (data.completed) return;
    openOnboardingWizard();
}

function openOnboardingWizard() {
    onboardingAutoAdvanced = false;
    const wizard = document.getElementById('onboardingWizard');
    if (!wizard) return;
    wizard.classList.remove('hidden');
    setOnboardingStep(1);
    if (window.lucide) lucide.createIcons();
}

function setOnboardingStep(step) {
    onboardingStep = Math.max(1, Math.min(4, step));
    const wizard = document.getElementById('onboardingWizard');
    if (!wizard) return;
    wizard.dataset.step = String(onboardingStep);

    document.querySelectorAll('.onboarding-step').forEach(el => {
        el.classList.toggle('active', el.dataset.step === String(onboardingStep));
    });
    document.querySelectorAll('.onboarding-dot').forEach(el => {
        el.classList.toggle('active', Number(el.dataset.dot) <= onboardingStep);
    });

    const back = document.getElementById('onboardingBackBtn');
    const next = document.getElementById('onboardingNextBtn');
    const finish = document.getElementById('onboardingFinishBtn');
    if (back) back.disabled = onboardingStep === 1;
    if (next) next.classList.toggle('hidden', onboardingStep === 4);
    if (finish) finish.classList.toggle('hidden', onboardingStep !== 4);

    if (onboardingStep === 2) {
        startOnboardingConnectorPoll();
        if (next) next.disabled = true;
    } else {
        stopOnboardingConnectorPoll();
        if (next) next.disabled = false;
    }

    if (onboardingStep === 3 && next) next.disabled = true;
    if (window.lucide) lucide.createIcons();
}

function nextOnboardingStep() {
    setOnboardingStep(onboardingStep + 1);
}

function previousOnboardingStep() {
    setOnboardingStep(onboardingStep - 1);
}

function startOnboardingConnectorPoll() {
    stopOnboardingConnectorPoll();
    checkOnboardingConnector();
    onboardingTimer = setInterval(checkOnboardingConnector, 2000);
}

function stopOnboardingConnectorPoll() {
    if (onboardingTimer) {
        clearInterval(onboardingTimer);
        onboardingTimer = null;
    }
}

async function checkOnboardingConnector() {
    const result = await apiBg('/api/connector');
    const data = result.data;
    if (!data) return;
    const loading = document.getElementById('onboardingQrLoading');
    const image = document.getElementById('onboardingQrImage');
    const connected = document.getElementById('onboardingQrConnected');
    const nodeOffline = document.getElementById('onboardingNodeOffline');
    const next = document.getElementById('onboardingNextBtn');

    if (nodeOffline) {
        nodeOffline.classList.toggle('hidden', data.node_online !== false);
    }

    if (data.connected) {
        if (loading) loading.classList.add('hidden');
        if (image) image.classList.add('hidden');
        if (connected) connected.classList.remove('hidden');
        if (nodeOffline) nodeOffline.classList.add('hidden');
        if (next) next.disabled = false;
        if (onboardingStep === 2 && !onboardingAutoAdvanced) {
            onboardingAutoAdvanced = true;
            setTimeout(() => setOnboardingStep(3), 800);
        }
        return;
    }

    if (data.qr && image) {
        image.src = data.qr;
        image.classList.remove('hidden');
        if (loading) loading.classList.add('hidden');
        if (connected) connected.classList.add('hidden');
        if (nodeOffline) nodeOffline.classList.add('hidden');
    } else {
        if (loading) loading.classList.remove('hidden');
        if (image) image.classList.add('hidden');
        if (connected) connected.classList.add('hidden');
    }
    if (next) next.disabled = true;
}

async function downloadOnboardingTemplate() {
    const ok = await downloadTemplateWorkbook();
    if (ok) setOnboardingStep(4);
}

async function completeOnboarding() {
    const result = await api('/api/onboarding/complete', { method: 'POST' });
    if (result.success) {
        stopOnboardingConnectorPoll();
        document.getElementById('onboardingWizard')?.classList.add('hidden');
        showToast('Configuração inicial concluída.', 'success');
    }
}

async function disconnectWhatsApp() {
    const btn = document.getElementById('disconnectWaBtn');
    if (!btn) return;
    btn.disabled = true;
    btn.textContent = 'Desconectando...';

    try {
        const data = await api('/api/whatsapp/disconnect', { method: 'POST' });
        if (data.success) {
            // Volta UI do modal para o estado inicial de carregamento
            const qrLoading = document.getElementById('qrLoading');
            const qrContainer = document.getElementById('qrContainer');
            const connSuccess = document.getElementById('connSuccess');
            if (qrLoading) qrLoading.classList.remove('hidden');
            if (qrContainer) qrContainer.classList.add('hidden');
            if (connSuccess) connSuccess.classList.add('hidden');

            // Atualiza sidebar
            const sidebarBtn = document.querySelector('.nav-item[onclick="openConnector()"]');
            if (sidebarBtn) {
                sidebarBtn.style.color = '';
                sidebarBtn.title = 'Conectar WhatsApp';
            }

            // Poll após 3s para pegar o novo QR gerado após logout
            setTimeout(checkConnector, 3000);
        } else {
            alert(data.error || 'Não foi possível desconectar.');
        }
    } catch (e) {
        alert('Erro de comunicação ao desconectar.');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="2.5">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
            </svg> Desconectar`;
        }
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

// --- Spintax Logic ---
let spintaxCursorPos = 0;

function openSpintaxModal() {
  const textarea = document.getElementById('message-input');
  spintaxCursorPos = textarea.selectionStart;
  const list = document.getElementById('spintax-options-list');
  list.innerHTML = '';
  for (let i = 0; i < 3; i++) addSpintaxOption();
  updateSpintaxPreview();
  document.getElementById('spintax-modal').style.display = 'flex';
}

function closeSpintaxModal() {
  document.getElementById('spintax-modal').style.display = 'none';
}

function addSpintaxOption() {
  const list = document.getElementById('spintax-options-list');
  const count = list.querySelectorAll('.spintax-option-row').length;
  const row = document.createElement('div');
  row.className = 'spintax-option-row';
  row.innerHTML = `
    <span class="option-number">${count + 1}.</span>
    <input type="text" class="spintax-input" placeholder="Opção ${count + 1}"
      oninput="updateSpintaxPreview()" />
    ${count >= 2 ? '<button type="button" class="btn-remove-option" onclick="removeSpintaxOption(this)">✕</button>' : ''}
  `;
  list.appendChild(row);
  const warning = document.getElementById('spintax-warning');
  warning.style.display = count + 1 > 6 ? 'block' : 'none';
  updateSpintaxPreview();
}

function removeSpintaxOption(btn) {
  btn.closest('.spintax-option-row').remove();
  renumberSpintaxOptions();
  updateSpintaxPreview();
}

function renumberSpintaxOptions() {
  document.querySelectorAll('.spintax-option-row').forEach((row, i) => {
    row.querySelector('.option-number').textContent = (i + 1) + '.';
    row.querySelector('.spintax-input').placeholder = 'Opção ' + (i + 1);
  });
}

function updateSpintaxPreview() {
  const inputs = [...document.querySelectorAll('.spintax-input')];
  const values = inputs.map(i => i.value.trim()).filter(v => v);
  const preview = document.getElementById('spintax-preview-text');
  if (values.length === 0) { preview.textContent = '—'; return; }

  const focused = document.activeElement;
  if (focused && focused.classList.contains('spintax-input') && focused.value.trim()) {
    preview.textContent = focused.value.trim();
  } else {
    preview.textContent = values[Math.floor(Math.random() * values.length)];
  }
}

function insertSpintax() {
  const inputs = [...document.querySelectorAll('.spintax-input')];
  const values = inputs.map(i => i.value.trim()).filter(v => v);
  if (values.length < 2) {
    alert('Adicione pelo menos 2 opções para criar uma variação.');
    return;
  }
  const syntax = '{' + values.join('|') + '}';
  const textarea = document.getElementById('message-input');
  const before = textarea.value.substring(0, spintaxCursorPos);
  const after = textarea.value.substring(spintaxCursorPos);
  textarea.value = before + syntax + after;
  textarea.dispatchEvent(new Event('input'));
  closeSpintaxModal();
  textarea.focus();
  textarea.setSelectionRange(
    spintaxCursorPos + syntax.length,
    spintaxCursorPos + syntax.length
  );
}

loadSendWindowConfig();
initOnboarding();
