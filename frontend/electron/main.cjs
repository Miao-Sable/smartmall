// 智慧购物 Windows 桌面壳（Electron 主进程）
const { app, BrowserWindow, session } = require('electron')
const path = require('path')

function createWindow() {
  const win = new BrowserWindow({
    width: 420,
    height: 860,
    minWidth: 360,
    minHeight: 640,
    title: '智慧购物',
    icon: path.join(__dirname, 'icon.ico'),
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      // 关闭同源策略：允许 file:// 页面请求 http://localhost:8000 后端
      webSecurity: false,
    },
  })

  // 移除顶部 File/Edit/View/Window 菜单栏
  win.removeMenu()

  win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
}

app.whenReady().then(() => {
  // 放行摄像头等媒体权限（html5-qrcode 扫码用 getUserMedia）
  session.defaultSession.setPermissionRequestHandler((_webContents, permission, callback) => {
    const allowed = ['media', 'camera', 'videoCapture', 'audioCapture'].includes(permission)
    callback(allowed)
  })

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
