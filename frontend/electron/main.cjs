// 智慧购物 Windows 桌面壳（Electron 主进程）
const { app, BrowserWindow, session } = require('electron')
const path = require('path')
const fs = require('fs')
const { spawn, spawnSync } = require('child_process')

const BACKEND_PORT = 8000
let backendProcess = null

// 打包后后端 exe 随 app 放在 resources/backend/backend.exe
function backendExePath() {
  return path.join(process.resourcesPath, 'backend', 'backend.exe')
}

async function isBackendUp() {
  try {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), 1200)
    const res = await fetch(`http://127.0.0.1:8000/api/health`, { signal: ctrl.signal })
    clearTimeout(timer)
    return res.ok
  } catch (_) {
    return false
  }
}

function startBackend() {
  const exe = backendExePath()
  if (!fs.existsSync(exe)) {
    // 开发模式（未打包后端 exe）时跳过，依赖手动启动的后端
    console.log('[backend] not bundled, skip auto-start')
    return
  }
  const logPath = path.join(app.getPath('userData'), 'backend.log')
  const logStream = fs.createWriteStream(logPath, { flags: 'a' })
  logStream.write(`\n--- start ${new Date().toISOString()} ---\n`)
  backendProcess = spawn(exe, [], { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] })
  backendProcess.stdout.pipe(logStream)
  backendProcess.stderr.pipe(logStream)
  backendProcess.on('error', (err) => logStream.write('spawn error: ' + err + '\n'))
  backendProcess.on('exit', (code) => { logStream.write(`exited code=${code}\n`); backendProcess = null })
}

function stopBackend() {
  if (!backendProcess) return
  try {
    // /T 连子进程一起杀（PyInstaller onefile 会有引导进程 + 实际服务进程）
    spawnSync('taskkill', ['/PID', String(backendProcess.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true })
  } catch (_) { /* ignore */ }
  backendProcess = null
}

async function ensureBackend() {
  if (await isBackendUp()) return
  startBackend()
  // 等待就绪（onefile 解压 + uvicorn 启动需几秒）
  for (let i = 0; i < 50; i++) {
    await new Promise((r) => setTimeout(r, 300))
    if (await isBackendUp()) return
  }
}

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
      // 关闭同源策略：允许 file:// 页面请求 http://127.0.0.1:8000 后端
      webSecurity: false,
    },
  })

  // 移除顶部 File/Edit/View/Window 菜单栏
  win.removeMenu()
  win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  return win
}

app.whenReady().then(async () => {
  // 放行摄像头等媒体权限（html5-qrcode 扫码用 getUserMedia）
  session.defaultSession.setPermissionRequestHandler((_webContents, permission, callback) => {
    const allowed = ['media', 'camera', 'videoCapture', 'audioCapture'].includes(permission)
    callback(allowed)
  })

  // 拉起本地后端（若未运行），不阻塞窗口创建
  const backendUp = ensureBackend().catch((e) => console.error('backend ensure failed', e))
  createWindow()
  await backendUp

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('before-quit', stopBackend)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
