const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  notifyTender: (payload) => ipcRenderer.invoke('tender-notify', payload),
});

window.addEventListener('DOMContentLoaded', () => {
  console.log('Preload ready');
});
