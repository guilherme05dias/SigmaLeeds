const express = require('express');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcodeTerminal = require('qrcode-terminal');
const QRCode = require('qrcode');
const fs = require('fs');

const app = express();
app.use(express.json());

let isReady = false;
let currentQR = null;

// Cliente WhatsApp invisível, armazenando os arquivos de sessão na pasta local (.wwebjs_auth)
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { 
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'] 
    }
});

// Ao gerar QR Code
client.on('qr', async (qr) => {
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

// Quando o WhatsApp estiver conectado com sucesso
client.on('ready', () => {
    console.log('✅ SIGMA HUB - WhatsApp Automação 100% OK e Pronto para uso!');
    isReady = true;
    currentQR = null; // Limpa o QR após conectar
});

// Quando perder conexão
client.on('disconnected', (reason) => {
    console.log('🔴 WhatsApp Descontectado:', reason);
    isReady = false;
});

// Inicia o cliente
client.initialize();

// ==========================================
// ROTAS DE API (O Python vai disparar daqui)
// ==========================================

// Rota de Status (o Python precisa saber se já conectou para habilitar envios)
app.get('/status', (req, res) => {
    res.json({ connected: isReady, qr: currentQR });
});

// Força o envio do QR atual (se existir)
app.get('/qr', (req, res) => {
    res.json({ qr: currentQR });
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
            const media = MessageMedia.fromFilePath(filePath);
            
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

// Inicia o Servidor Local Invisível
const PORT = 3001;
app.listen(PORT, () => {
    console.log(`🚀 Motor Node.js (API Invisível) rodando na porta ${PORT}`);
});
