# SmartMall 安卓 APK 打包指南

项目已用 [Capacitor](https://capacitorjs.com/) 集成安卓原生壳（`frontend/android/`），可从同一套 Vue 前端打出安卓安装包（`.apk`）。

**PWA 与 APK 并存、共用同一后端**：PWA 是「浏览器打开 → 添加到主屏幕」，APK 是「直接安装成独立 App」，两者调的是同一个后端接口。

---

## 1. 前置环境

| 项 | 要求 | 本机现状 |
|---|---|---|
| Node.js | >= 20 | ✅ v24 |
| JDK | 17+（Capacitor 8 建议 21） | ❌ 只有 JDK 8 |
| Android SDK | 最新（通过 Android Studio 安装，或命令行 sdkmanager） | ❌ 未装 |
| Gradle | 无需单独装（工程自带 gradlew） | ✅ 已随工程生成 |

> 最简单：装 [Android Studio](https://developer.android.com/studio)，它会带上 SDK + 合适的 JDK。

---

## 2. 打包步骤

### 2.1 构建前端（关键：指定后端地址）

APK 内**没有 Nginx 反代**，前端必须用绝对地址访问后端，所以要带着 `VITE_API_BASE_URL` 构建：

```bash
# Git Bash / Linux / macOS
VITE_API_BASE_URL=https://你的后端域名 npm run build

# Windows cmd / PowerShell
set VITE_API_BASE_URL=https://你的后端域名 && npm run build
```

- 测试阶段后端可能是局域网：`http://192.168.x.x:8000`（需后端 CORS 放行，见 §3）。
- 生产必须用 `https://`。

### 2.2 同步到安卓工程

```bash
npx cap sync android
```

（把 `frontend/dist/` 拷进 `android/app/src/main/assets/public/`。）

### 2.3 打 debug 包（可直接安装）

```bash
cd android
gradlew assembleDebug        # Windows cmd 用 gradlew.bat assembleDebug
```

产物：`android/app/build/outputs/apk/debug/app-debug.apk`

把这个 `.apk` 传到手机，允许「安装未知来源应用」即可安装。

> 也可用 Android Studio 打开 `frontend/android/` 目录，点 Run 直接装到连着的手机/模拟器。

---

## 3. 必须处理的三件事

### 3.1 后端 CORS

APK 的 WebView 请求后端时来源是 `capacitor://localhost` / `https://localhost`，与浏览器不同。若报 CORS 错误，把后端 `CORS_ORIGINS` 放宽：

```
CORS_ORIGINS=["*"]
```

（演示/测试可临时用 `*`；正式上线再收窄到你的域名。）

### 3.2 摄像头扫码

`AndroidManifest.xml` 已加 `CAMERA` 权限，`html5-qrcode` 扫码可用。首次扫码系统会弹权限请求，允许即可。

### 3.3 明文 HTTP（仅测试）

`AndroidManifest.xml` 已加 `android:usesCleartextTraffic="true"`，所以测试阶段能连 `http://IP:8000`。**生产改用 HTTPS 后，建议移除该属性**（在 `frontend/android/app/src/main/AndroidManifest.xml`）。

---

## 4. 已做好的定制

- **应用名**：智慧购物（`app_name`）
- **图标**：蓝底白色条码（已替换 Capacitor 默认 logo，含传统图标 + 自适应图标）
- **appId**：`com.smartmall.app`（上架前需改成你自己的反向域名，改 `frontend/capacitor.config.ts` 后重新 `npx cap sync`）

---

## 5. 签名与上架（可选，正式分发才需要）

debug 包自带调试签名，能装能用，但不能上应用商店。正式发布：

1. 生成签名：`keytool -genkey -v -keystore smartmall.keystore -alias smartmall -keyalg RSA -keysize 2048 -validity 10000`
2. 在 `android/app/build.gradle` 配 `signingConfigs`（release 用该 keystore）
3. `gradlew assembleRelease` 打出 `app-release.apk`

上架还需要：改 appId、升版本号、隐私政策、软著等（超出本仓库范围）。
