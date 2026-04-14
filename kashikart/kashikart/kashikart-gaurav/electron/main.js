const { app, BrowserWindow, ipcMain, Notification } = require('electron');
const path = require('path');
const isDev = process.env.NODE_ENV === 'development';

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, '../public/icon.png'), // add icon
    titleBarStyle: 'hiddenInset', // mac
  });

  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }
}

ipcMain.handle('tender-notify', (_event, payload = {}) => {
  if (!Notification.isSupported()) return false;

  const {
    title = 'New tender fetched',
    body = 'A new tender is available.',
    silent = false,
  } = payload;

  const iconPath = path.join(app.getAppPath(), 'public', 'vite.svg');

  const notification = new Notification({
    title,
    body,
    silent,
    icon: iconPath,
  });

  notification.show();
  return true;
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
