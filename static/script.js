try { lucide.createIcons(); } catch(e) { console.warn("Lucide icons falhou:", e); }

// Elements
const uploadZone = document.getElementById('uploadZone');
const fileExcel = document.getElementById('fileExcel');
const excelFileName = document.getElementById('excelFileName');
const chkAttachment = document.getElementById('chkAttachment');
const attControls = document.getElementById('attControls');
const fileAtt = document.getElementById('fileAtt');
const attFileName = document.getElementById('attFileName');
const terminalBox = document.getElementById('terminalBox');
const btnStart = document.getElementById('btnStart');
const btnStop = document.getElementById('btnStop');
const btnResume = document.getElementById('btnResume');
const statusBadge = document.getElementById('statusBadge');
const pendingCount = document.getElementById('pendingCount');
const progressBar = document.getElementById('progressBar');

let currentPending = 0;
let initialTotal = 0;

// Setup EventSource for logs
const source = new EventSource('/api/logs');
source.onmessage = function(event) {
    const parts = event.data.split('|');
    if (parts.length >= 2) {
        const level = parts[0];
        const msg = parts.slice(1).join('|');
        const span = document.createElement('div');
        span.className = `log-${level}`;
        const time = new Date().toLocaleTimeString('pt-BR');
        span.textContent = `[${time}] ${msg}`;
        terminalBox.appendChild(span);
        terminalBox.scrollTop = terminalBox.scrollHeight;
        
        // Quick update status based on logs processamento
        if (msg.includes("Processando")) {
            currentPending = Math.max(0, currentPending - 1);
            updateProgress();
        }
    }
};

// Polling status
setInterval(async () => {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.progress.status === "Planilha Carregada" && initialTotal === 0) {
            initialTotal = data.progress.total;
            currentPending = data.progress.pending;
            updateProgress();
        }
        
        pendingCount.textContent = data.progress.pending;
        
        if (data.is_running) {
            btnStart.disabled = true;
            btnStop.disabled = false;
            btnResume.classList.add('hidden');
            statusBadge.textContent = "✔ Disparando Automático";
            statusBadge.className = "badge badge-running";
            uploadZone.style.pointerEvents = 'none';
            initialTotal = data.progress.total;
        } else if (data.was_stopped) {
            btnStart.disabled = true;
            btnStop.disabled = true;
            btnResume.classList.remove('hidden');
            statusBadge.textContent = "⏸ Campanha Pausada";
            statusBadge.className = "badge badge-paused";
            uploadZone.style.pointerEvents = 'none';
        } else {
            btnStart.disabled = false;
            btnStop.disabled = true;
            btnResume.classList.add('hidden');
            statusBadge.textContent = data.progress.status || "Aguardando";
            statusBadge.className = "badge badge-waiting";
            uploadZone.style.pointerEvents = 'auto';
        }
        
    } catch (e) {}
}, 2000);

function updateProgress() {
    pendingCount.textContent = currentPending;
    if (initialTotal > 0) {
        const proc = initialTotal - currentPending;
        const pct = Math.min(100, Math.round((proc / initialTotal)*100));
        progressBar.style.width = pct + "%";
    }
}

// Upload Excel
uploadZone.addEventListener('click', () => fileExcel.click());
uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('dragover'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    if(e.dataTransfer.files.length) handleExcelUpload(e.dataTransfer.files[0]);
});
fileExcel.addEventListener('change', (e) => {
    if(e.target.files.length) handleExcelUpload(e.target.files[0]);
});

async function handleExcelUpload(file) {
    const fd = new FormData();
    fd.append('file', file);
    excelFileName.innerHTML = "Carregando a planilha no motor...";
    try {
        const res = await fetch('/api/upload-excel', { method: 'POST', body: fd });
        const data = await res.json();
        if(res.ok) {
            excelFileName.innerHTML = `✔ ${data.filename} (${data.pending} em aberto)`;
            initialTotal = data.pending;
            currentPending = data.pending;
            updateProgress();
            document.getElementById('btnRemoveExcel').classList.remove('hidden');
        } else {
            alert(data.error);
            excelFileName.innerHTML = "Erro ao processar arquivo xlsx.";
        }
    } catch(e) { alert("Erro de rede com o servidor nativo"); }
}

async function removeExcel() {
    if(!confirm("Deseja remover a planilha carregada?")) return;
    try {
        const res = await fetch('/api/clear-excel', { method: 'POST' });
        const data = await res.json();
        if(res.ok) {
            excelFileName.innerHTML = "Nenhuma planilha carregada";
            document.getElementById('btnRemoveExcel').classList.add('hidden');
            initialTotal = 0;
            currentPending = 0;
            progressBar.style.width = "0%";
            pendingCount.textContent = "0";
            fileExcel.value = "";
        } else {
            alert(data.error);
        }
    } catch(e) {}
}

// Anexos
chkAttachment.addEventListener('change', (e) => {
    if(e.target.checked) attControls.classList.remove('hidden');
    else { attControls.classList.add('hidden'); fetch('/api/clear-attachment', {method:'POST'}); attFileName.textContent="Nenhum anexo"; }
});

async function uploadAttachment(input) {
    if(!input.files.length) return;
    const fd = new FormData();
    fd.append('file', input.files[0]);
    attFileName.textContent = "Guardando no cache...";
    try {
        const res = await fetch('/api/upload-attachment', { method:'POST', body: fd});
        const data = await res.json();
        if(res.ok) attFileName.textContent = data.filename;
        else attFileName.textContent = "Erro no upload interno";
    } catch(e) {}
}

async function clearAttachment() {
    await fetch('/api/clear-attachment', {method:'POST'});
    attFileName.textContent = "Nenhum anexo";
    fileAtt.value = "";
}

async function startCampaign() {
    const data = {
        msg: document.getElementById('txtMessage').value,
        limit: document.getElementById('inpLimit').value,
        min: document.getElementById('inpMin').value,
        max: document.getElementById('inpMax').value,
        keep_open: document.getElementById('chkKeepOpen').checked
    };
    const res = await fetch('/api/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    const d = await res.json();
    if(!res.ok) alert(d.error);
}

async function stopCampaign() {
    await fetch('/api/stop', {method:'POST'});
}

async function resumeCampaign() {
    const data = {
        msg: document.getElementById('txtMessage').value,
        limit: document.getElementById('inpLimit').value,
    };
    const res = await fetch('/api/resume', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    const d = await res.json();
    if(!res.ok) alert(d.error);
}

// WhatsApp Connector Logic

const connectorModal = document.getElementById('connectorModal');
const qrImage = document.getElementById('qrImage');
const qrContainer = document.getElementById('qrContainer');
const connStatusText = document.getElementById('connStatusText');
const connectedSuccess = document.getElementById('connectedSuccess');
const motorErr = document.getElementById('motorErr');
const connStatusWrap = document.getElementById('connStatusWrap');
const btnConnector = document.getElementById('btnConnector');

let connectorInterval = null;
let pollRetries = 0;

function openConnector() {
    connectorModal.classList.remove('hidden');
    pollRetries = 0;
    startConnectorPolling();
}

async function closeConnector() {
    connectorModal.classList.add('hidden');
    stopConnectorPolling();
    try {
        await fetch('/api/accounts/update_status', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({status: 'connected'})
        });
    } catch(e) {}
}

function retryConnection() {
    pollRetries = 0;
    showConnectorState('waiting');
    startConnectorPolling();
}

function startConnectorPolling() {
    if (connectorInterval) return;
    pollRetries = 0;
    pollConnector();
    connectorInterval = setInterval(pollConnector, 1000); // 1s interval as requested
}

function stopConnectorPolling() {
    if (connectorInterval) {
        clearInterval(connectorInterval);
        connectorInterval = null;
    }
}

async function pollConnector() {
    try {
        const res = await fetch('/api/connector');
        const data = await res.json();
        
        if (data.error) {
            showConnectorState('error');
            return;
        }

        if (data.connected) {
            showConnectorState('connected');
            btnConnector.innerHTML = '<i data-lucide="check"></i> WHATSAPP CONECTADO';
            btnConnector.classList.add('connected');
            
            // Fecha modal sozinho após um tempo, se estiver aberto, pois já conectou
            if(!connectorModal.classList.contains('hidden')){
                setTimeout(closeConnector, 1500);
            }
        } else if (data.qr) {
            const wasEmpty = !qrImage.getAttribute('src') || qrImage.getAttribute('src') === "";
            showConnectorState('qr');
            qrImage.src = data.qr;
            btnConnector.innerHTML = '<i data-lucide="smartphone"></i> ESCANEAR QR CODE';
            btnConnector.classList.remove('connected');
            
            // Abre automaticamente a janela para o usuário quando o QR chega do servidor
            if (wasEmpty && connectorModal.classList.contains('hidden')) {
                openConnector();
            }
        } else {
            pollRetries++;
            if (pollRetries > 10) {
                stopConnectorPolling();
                showConnectorState('error');
            } else {
                showConnectorState('waiting');
                btnConnector.innerHTML = '<i data-lucide="loader"></i> AGUARDANDO MOTOR...';
            }
        }
    } catch (e) {
        showConnectorState('error');
    }
}

function showConnectorState(state) {
    connStatusWrap.classList.remove('hidden');
    qrContainer.classList.add('hidden');
    connectedSuccess.classList.add('hidden');
    if (motorErr) motorErr.classList.add('hidden');

    const indicator = connStatusWrap.querySelector('.status-indicator');
    if (indicator) {
        indicator.className = 'status-indicator ' + state;
    }

    if (state === 'connected') {
        connStatusText.textContent = "Conectado";
        connectedSuccess.classList.remove('hidden');
        qrContainer.classList.add('hidden');
    } else if (state === 'qr') {
        connStatusText.textContent = "Aguardando Leitura...";
        qrContainer.classList.remove('hidden');
    } else if (state === 'error') {
        connStatusText.textContent = "Erro de Conexão";
        if (motorErr) motorErr.classList.remove('hidden');
        qrContainer.classList.add('hidden');
    } else {
        connStatusText.textContent = "Verificando motor...";
    }
}

// Initial check for connector status on load
pollConnector();

