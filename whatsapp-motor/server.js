const express = require('express');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcodeTerminal = require('qrcode-terminal');
const QRCode = require('qrcode');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

// C3: only serve attachments that live inside data/attachments
const ATTACHMENTS_ROOT = path.resolve('./data/attachments');

let isReady = false;
let currentQR = null;
let initAttempts = 0;
let watchdogTimer = null;

const appDataDir = path.join(process.env.LOCALAPPDATA || process.env.USERPROFILE, 'ZapManagerPro');
if (!fs.existsSync(appDataDir)) {
    fs.mkdirSync(appDataDir, { recursive: true });
}

// Procura pelo Chrome ou Edge instalado na máquina do usuário
function getChromePath() {
    const paths = [
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
    ];
    for (let p of paths) {
        if (fs.existsSync(p)) return p;
    }
    return null; // Tenta o padrão do puppeteer se não achar
}

// Cliente WhatsApp invisível, armazenando os arquivos de sessão na pasta local (.wwebjs_auth)
const client = new Client({
    authStrategy: new LocalAuth({ dataPath: appDataDir }),
    puppeteer: {
        headless: true,
        executablePath: getChromePath(),
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
    }
});

function clearSessionWatchdog() {
    if (watchdogTimer) {
        clearTimeout(watchdogTimer);
        watchdogTimer = null;
    }
}

function armSessionWatchdog() {
    clearSessionWatchdog();
    watchdogTimer = setTimeout(() => {
        if (!currentQR && !isReady) {
            initAttempts += 1;
            console.log(`[WA] Watchdog: nenhum QR/ready em 45s (tentativa ${initAttempts}/2)`);

            if (initAttempts >= 2) {
                console.error('[WA] Watchdog: sessao corrompida apos 2 tentativas. Aguardando intervencao manual.');
                return;
            }

            const sessionPath = path.join(appDataDir, 'session');
            try {
                fs.rmSync(sessionPath, { recursive: true, force: true });
            } catch (err) {
                console.error('[WA] Watchdog: falha ao remover session:', err.message);
            }

            try {
                client.destroy();
            } catch (err) {
                console.error('[WA] Watchdog: falha ao destruir client:', err.message);
            }

            setTimeout(() => {
                client.initialize();
                armSessionWatchdog();
            }, 1500);
        }
    }, 45000);
}

// Ao gerar QR Code
client.on('qr', async (qr) => {
    clearSessionWatchdog();
    initAttempts = 0;
    console.log('SCANEAR QR CODE - Acesse o console e scaneie.');
    qrcodeTerminal.generate(qr, { small: true });

    // Gera versão Base64 para a interface web
    try {
        currentQR = await QRCode.toDataURL(qr);
        isReady = false;
    } catch (err) {
        console.error('Falha ao gerar QR Base64:', err);
    }
});

// Quando a autenticação for bem sucedida (QR lido)
client.on('authenticated', () => {
    console.log('Autenticado com sucesso! Aguardando o carregamento dos chats...');
    currentQR = null; // Limpa o QR para a UI mostrar "carregando"
});

// Enquanto carrega a tela do WhatsApp
client.on('loading_screen', (percent, message) => {
    console.log('Carregando WhatsApp:', percent, '%', message);
    currentQR = null;
});

// Quando o WhatsApp estiver conectado com sucesso
client.on('ready', () => {
    clearSessionWatchdog();
    initAttempts = 0;
    console.log('✅ SIGMA HUB - WhatsApp Automação 100% OK e Pronto para uso!');
    isReady = true;
    currentQR = null; // Garante que limpou o QR
});

// Quando perder conexão
client.on('disconnected', (reason) => {
    console.log('[WA] Disconnected:', reason);
    isReady = false;

    // Attempt automatic reconnect after 5 seconds
    setTimeout(() => {
        console.log('[WA] Attempting to reinitialize after disconnect...');
        try {
            client.initialize();
            armSessionWatchdog();
        } catch (err) {
            console.error('[WA] Reinitialize failed:', err.message);
        }
    }, 5000);
});

// Inicia o cliente
client.initialize();
armSessionWatchdog();

// ==========================================
// ROTAS DE API (O Python vai disparar daqui)
// ==========================================

// Rota de Status (o Python precisa saber se já conectou para habilitar envios)
app.get('/status', (req, res) => {
    res.json({
        connected: isReady,
        status: isReady ? 'connected' : 'disconnected',
        qr: currentQR
    });
});

app.get('/ping', (req, res) => {
    res.json({ ok: true });
});

// Força o envio do QR atual (se existir)
app.get('/qr', (req, res) => {
    res.json({ qr: currentQR });
});


app.post('/disconnect', async (req, res) => {
    try {
        if (!isReady) {
            return res.json({ success: true, message: 'Already disconnected.' });
        }
        await client.logout();   // ends the WhatsApp Web session
        isReady = false;
        currentQR = null;
        console.log('[WA] Session logged out by user request.');
        res.json({ success: true, message: 'Disconnected successfully.' });
    } catch (err) {
        console.error('[WA] Logout error:', err.message);
        // Even if logout throws, mark as not ready
        isReady = false;
        currentQR = null;
        res.json({ success: true, message: 'Session cleared (logout error ignored).' });
    }
});

app.post('/reset-session', async (req, res) => {
    try {
        clearSessionWatchdog();
        try {
            await client.destroy();
        } catch {}

        isReady = false;
        currentQR = null;

        const sessionPath = path.join(appDataDir, 'session');
        try {
            fs.rmSync(sessionPath, { recursive: true, force: true });
        } catch {}

        initAttempts = 0;
        setTimeout(() => {
            client.initialize();
            armSessionWatchdog();
        }, 1000);

        console.log('[WA] Session reset requested. Waiting for new QR.');
        res.json({ success: true });
    } catch (err) {
        console.error('[WA] reset-session error:', err.message);
        res.status(500).json({ success: false, error: err.message });
    }
});

// Envio Poderoso (Aceita Mensagem, Arquivo ou Ambos)
app.post('/send', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({ error: 'WhatsApp ainda não está logado ou não está pronto.' });
    }

    let { number, message, filePath } = req.body;

    // Formata o número (só pega DDD e números do Brasil para DDI 55)
    let zapNumber = number.replace(/\D/g, '');
    if (!zapNumber.startsWith('55')) {
        zapNumber = '55' + zapNumber;
    }

    try {
        // Resolve o LID (ID interno real) do contato para evitar erro "No LID for user"
        const contactId = await client.getNumberId(zapNumber);
        if (!contactId) {
            return res.status(400).json({ error: 'invalid: O número não possui WhatsApp registrado.' });
        }

        const chatId = contactId._serialized;
        let sentMessage;

        // SE TEM UM ANEXO (Não há risco de figurinhas aqui)
        if (filePath && fs.existsSync(filePath)) {
            // C3: reject any path that resolves outside the allowed attachments directory
            const absolutePath = path.resolve(filePath);
            if (!absolutePath.startsWith(ATTACHMENTS_ROOT + path.sep) && absolutePath !== ATTACHMENTS_ROOT) {
                console.warn(`[Security] Blocked filePath outside attachments root: ${absolutePath}`);
                return res.status(403).json({ error: 'Access denied' });
            }

            const media = MessageMedia.fromFilePath(absolutePath);

            // Se tiver texto associado, ele vai como LEGENDA.
            if (message && message.trim() !== '') {
                sentMessage = await client.sendMessage(chatId, media, { caption: message });
                console.log(`[FOTO+LEGENDA] Enviada ao número ${zapNumber}`);
            } else {
                // Envia só a foto/documento solto sem legenda
                sentMessage = await client.sendMessage(chatId, media);
                console.log(`[FOTO SOZINHA] Enviada ao número ${zapNumber}`);
            }
        }

        // SE É SÓ UMA MENSAGEM DE TEXTO COMUM
        else if (message && message.trim() !== '') {
            sentMessage = await client.sendMessage(chatId, message);
            console.log(`[TEXTO] Enviado ao número ${zapNumber}`);
        } else {
            return res.status(400).json({ error: 'Faltam argumentos para enviar (message ou filePath).' });
        }

        res.json({ success: true, id: sentMessage.id.id });

    } catch (error) {
        console.error(`Falha no envio para ${zapNumber}:`, error.message);
        res.status(500).json({ error: error.message });
    }
});

// C2: bind to 127.0.0.1 only — prevents LAN access to the WhatsApp engine
const PORT = 3001;
app.listen(PORT, '127.0.0.1', () => {
    console.log(`🚀 Motor Node.js (API Invisível) rodando em 127.0.0.1:${PORT}`);
});
