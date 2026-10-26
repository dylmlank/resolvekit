// ResolveKit Workflow Integration panel — Electron main process.
//
// The panel is UI only: it talks to the local ResolveKit backend (server.py)
// over a WebSocket, and the backend performs every DaVinci Resolve action via
// the Python scripting API. So this window needs no WorkflowIntegration.node
// binding and no Node integration in the renderer — a plain sandboxed window
// that reaches the backend with the browser WebSocket API.
//
// Security guide: https://www.electronjs.org/docs/tutorial/security

const { app, BrowserWindow } = require('electron');

let mainWindow = null;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 420,
        height: 720,
        useContentSize: true,
        webPreferences: {
            contextIsolation: true,
            nodeIntegration: false
        }
    });

    mainWindow.on('close', function () {
        app.quit();
    });

    mainWindow.loadFile('index.html');
}

app.whenReady().then(createWindow);

app.on('window-all-closed', function () {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
