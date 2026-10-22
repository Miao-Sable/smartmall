# SmartMall Windows 桌面版（Electron 壳）

把同一套 Vue 前端用 Electron 壳打包成 Windows 便携版 `.exe`，双击直接打开，完全脱离浏览器。

与 PWA / APK 并存，共用同一个后端。

---

## 产物

- `frontend/release/智慧购物 0.2.0.exe`（约 97MB，单文件便携版，无需安装）

## 运行前提

exe 直连**本机后端** `http://localhost:8000`，所以打开前先启动后端：

```bash
cd backend
venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

后端起来后，双击 exe 即可。首次扫码会请求摄像头权限，允许即可。

## 重新打包

```bash
cd frontend
npm run electron:build
```

脚本依次：类型检查 → `vite build --mode desktop`（加载 `.env.desktop`）→ electron-builder 打 portable exe。

## 换后端地址

编辑 `frontend/.env.desktop`：

```
VITE_API_BASE_URL=http://localhost:8000
```

改成实际后端地址（如 `http://192.168.x.x:8000`）后重新打包。给别的电脑用，就把它改成那台电脑能访问到的后端 IP。

## 结构

| 文件/目录 | 作用 |
|---|---|
| `electron/main.cjs` | Electron 主进程（开窗、加载 dist、放行摄像头权限） |
| `electron/icon.ico` | 应用图标 |
| `electron-dist/` | 预解压的 Electron 运行时（`electronDist`，跳过下载+解压的锁文件坑，不入库） |
| `.env.desktop` | 桌面版构建的后端地址 |

> 说明：Capacitor 8 已移除官方 Electron 平台，故桌面版用纯 Electron 壳而非 `cap add electron`，效果一致且更轻。
