const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let serverProcess;
let viteProcess;

// Function to start the Vite dev server
function startViteServer() {
  const isDev = process.env.NODE_ENV === 'development';
  if (isDev) {
    viteProcess = spawn('npx', ['vite'], {
      cwd: __dirname,
      stdio: 'inherit'
    });

    viteProcess.on('close', (code) => {
      console.log(`Vite server exited with code ${code}`);
    });

    viteProcess.on('error', (err) => {
      console.error('Failed to start Vite server:', err);
    });
  }
}

// Function to start the Python server
function startPythonServer() {
  const isDev = process.env.NODE_ENV === 'development';
  let serverPath, args;
  if (isDev) {
    serverPath = 'python';
    args = [path.join(__dirname, 'server', 'main.py')];
  } else {
    // Use the bundled executable
    const exeName = process.platform === 'win32' ? 'jarvis_server.exe' : 'jarvis_server';
    serverPath = path.join(process.resourcesPath, exeName);
    args = [];
  }
  serverProcess = spawn(serverPath, args, {
    cwd: isDev ? path.join(__dirname, 'server') : process.resourcesPath,
    stdio: 'inherit'
  });

  serverProcess.on('close', (code) => {
    console.log(`Python server exited with code ${code}`);
  });

  serverProcess.on('error', (err) => {
    console.error('Failed to start Python server:', err);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'public', 'favicon.ico')
  });

  // Load the Vite dev server or built app
  const isDev = process.env.NODE_ENV === 'development';
  if (isDev) {
    mainWindow.loadURL('http://localhost:11842');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }
}

app.whenReady().then(() => {
  startViteServer();
  startPythonServer();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (viteProcess) {
    viteProcess.kill();
  }
  if (serverProcess) {
    serverProcess.kill();
  }
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  if (viteProcess) {
    viteProcess.kill();
  }
  if (serverProcess) {
    serverProcess.kill();
  }
});