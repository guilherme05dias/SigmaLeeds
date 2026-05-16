const { app, BrowserWindow, Menu, shell, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

const PORT_RANGE_START = 5050;
const PORT_RANGE_END = 5099;

let mainWindow = null;
let splashWindow = null;
let pythonProcess = null;
let detectedPort = null;

const isDev = !app.isPackaged;
const projectRoot = path.join(__dirname, '..');

// ── Iniciar Python (FastAPI) ───────────────────────────────────
function startPython() {
    if (isDev) {
        pythonProcess = spawn('python', ['app.py'], {
            cwd: projectRoot,
            windowsHide: true,
            stdio: 'pipe',
            env: {
                ...process.env,
                ZAP_NO_BROWSER: '1'
            }
        });
    } else {
        const exe = path.join(process.resourcesPath, 'engine', 'app.exe');
        const nodeExe = path.join(process.resourcesPath, 'node', 'node.exe');
        pythonProcess = spawn(exe, [], {
            cwd: path.dirname(exe),
            windowsHide: true,
            stdio: 'pipe',
            env: {
                ...process.env,
                ZAP_NO_BROWSER: '1',
                ZAP_NODE_EXE: nodeExe
            }
        });
    }
    pythonProcess.stderr?.on('data', d => console.log('[Python]', d.toString()));
    pythonProcess.stdout?.on('data', d => console.log('[Python]', d.toString()));
    pythonProcess.on('exit', code => console.log('[Python] exited with code', code));
}

// ── Health check: testa uma porta específica ──────────────────
// Probes / (public, no auth) and accepts any 2xx — avoids 401 from session middleware
function checkPort(port) {
    return new Promise(resolve => {
        const req = http.get(`http://127.0.0.1:${port}/`, res => {
            resolve(res.statusCode >= 200 && res.statusCode < 300);
            res.resume();
        });
        req.on('error', () => resolve(false));
        req.setTimeout(800, () => { req.destroy(); resolve(false); });
    });
}

// ── Scan do range de portas ───────────────────────────────────
async function scanForServer() {
    for (let port = PORT_RANGE_START; port <= PORT_RANGE_END; port++) {
        if (await checkPort(port)) return port;
    }
    return null;
}

// ── Aguardar o servidor subir em alguma porta do range ────────
async function waitForServer(maxAttempts = 60) {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        const port = await scanForServer();
        if (port) return port;
        await new Promise(r => setTimeout(r, 1000));
    }
    throw new Error('Servidor não respondeu em 60s');
}

// ── Splash screen ─────────────────────────────────────────────
function createSplash() {
    splashWindow = new BrowserWindow({
        width: 400,
        height: 280,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        resizable: false,
        icon: path.join(projectRoot, 'resources', 'icon.ico'),
        webPreferences: { nodeIntegration: false }
    });
    splashWindow.loadFile(path.join(__dirname, 'splash.html'));
}

// ── Janela principal ──────────────────────────────────────────
function createMainWindow(port) {
    const allowedOrigin = `http://127.0.0.1:${port}`;

    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        minWidth: 1024,
        minHeight: 680,
        title: 'ZapManager Pro v4.2.3',
        icon: path.join(projectRoot, 'resources', 'icon.ico'),
        show: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
            // Never allow loading local files from renderer
            webSecurity: true
        }
    });

    Menu.setApplicationMenu(null);

    // M-B4: Block navigation to any URL outside the detected Python server
    mainWindow.webContents.on('will-navigate', (event, url) => {
        if (!url.startsWith(allowedOrigin)) {
            event.preventDefault();
            console.warn(`[Security] Blocked navigation to: ${url}`);
        }
    });

    // M-B4: Same guard for redirects inside the page (hash/history navigation)
    mainWindow.webContents.on('did-start-navigation', (event, url) => {
        if (!url.startsWith(allowedOrigin)) {
            event.preventDefault();
            console.warn(`[Security] Blocked in-page navigation to: ${url}`);
        }
    });

    mainWindow.loadURL(allowedOrigin);

    mainWindow.once('ready-to-show', () => {
        if (splashWindow) {
            splashWindow.close();
            splashWindow = null;
        }
        mainWindow.show();
    });

    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}


// ── Lifecycle ─────────────────────────────────────────────────
app.whenReady().then(async () => {
    createSplash();
    startPython();

    try {
        detectedPort = await waitForServer();
        createMainWindow(detectedPort);
    } catch (err) {
        if (splashWindow) splashWindow.close();
        dialog.showErrorBox(
            'ZapManager Pro — Erro de inicialização',
            'O servidor não iniciou corretamente.\n\nVerifique se Python está instalado e tente novamente.'
        );
        app.quit();
    }
});

app.on('window-all-closed', () => {
    killProcesses();
    if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', killProcesses);

function killProcesses() {
    if (pythonProcess && pythonProcess.pid) {
        try {
            if (process.platform === 'win32') {
                // /T = tree completa, /F = força kill
                require('child_process').spawnSync(
                    'taskkill',
                    ['/PID', String(pythonProcess.pid), '/T', '/F'],
                    { stdio: 'ignore' }
                );
            } else {
                // Unix: mata group process inteiro
                try { process.kill(-pythonProcess.pid, 'SIGTERM'); } catch {}
                setTimeout(() => {
                    try { process.kill(-pythonProcess.pid, 'SIGKILL'); } catch {}
                }, 3000);
            }
        } catch (e) {
            console.error('[killProcesses] Erro:', e.message);
        }
        pythonProcess = null;
    }
}
