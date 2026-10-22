# SmartMall Windows 桌面版（Electron 壳）

把同一套 Vue 前端用 Electron 壳打包成 Windows 便携版 `.exe`，双击直接打开，完全脱离浏览器。后端（FastAPI）用 PyInstaller 打成 `backend.exe` 一并打进包里，**启动 exe 时自动拉起、退出时自动关闭**，无需手动开后端、无需目标机器装 Python。

与 PWA / APK 并存，共用同一套后端代码。

---

## 产物

- `frontend/release/智慧购物 0.2.0.exe`（单文件便携版，无需安装）
- 内含 `resources/backend/backend.exe`（PyInstaller 打包的 FastAPI 后端）

## 运行

直接双击 exe 即可：
1. Electron 启动，自动拉起内置后端 `backend.exe`（监听 `127.0.0.1:8000`）；
2. 等后端就绪后加载前端页面；
3. 关闭窗口时自动杀掉后端进程树。

首次使用会在 `%LOCALAPPDATA%\SmartMall\` 下新建数据库 `smartmall.db`（与开发环境仓库根的 `smartmall.db` 相互独立），注册一个新账号即可。

首次扫码会请求摄像头权限，允许即可。

## 重新打包（两步）

```bash
# 1) 打包后端为 backend.exe（PyInstaller）
cd frontend
npm run build:backend

# 2) 打包前端 exe（内含 backend.exe）
npm run electron:build
```

或一步到位：

```bash
cd frontend
npm run electron:build:all
```

说明：
- `build:backend` 在 `backend/` 下执行 PyInstaller，产物 `backend/dist/backend.exe`（不入库）；
- `electron:build` 依次：类型检查 → `vite build --mode desktop`（加载 `.env.desktop`）→ electron-builder 打 portable exe，并通过 `extraResources` 把 `backend.exe` 放进 `resources/backend/`。

## 换后端地址 / 端口

桌面版前端默认直连 `http://127.0.0.1:8000/api`，配置在 `frontend/.env.desktop`：

```
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

如需让 exe 连远程后端（而非内置后端），改此处后重新打包即可；此时内置后端端口未被占用时仍会自动启动，需在 `electron/main.cjs` 中关闭自动拉起逻辑。

## 结构

| 文件/目录 | 作用 |
|---|---|
| `electron/main.cjs` | Electron 主进程：开窗、加载 dist、放行摄像头权限、**自动拉起/关闭 backend.exe** |
| `electron/icon.ico` | 应用图标 |
| `electron-dist/` | 预解压的 Electron 运行时（`electronDist`，跳过下载+解压的锁文件坑，不入库） |
| `.env.desktop` | 桌面版构建的后端地址 |
| `backend/run_server.py` | PyInstaller 打包入口（启动 uvicorn，监听 127.0.0.1:8000） |
| `backend/dist/backend.exe` | PyInstaller 产物（不入库，由 `npm run build:backend` 生成） |

> 说明：Capacitor 8 已移除官方 Electron 平台，故桌面版用纯 Electron 壳而非 `cap add electron`，效果一致且更轻。
