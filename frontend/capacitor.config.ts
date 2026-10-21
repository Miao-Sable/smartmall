import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  // 应用唯一标识（上架应用商店前需改成你自己的反向域名）
  appId: 'com.smartmall.app',
  appName: '智慧购物',
  // Vite 构建产物目录（相对本文件所在目录 frontend/）
  webDir: 'dist',

  // 打包 APK 时前端不再有 Nginx 反代 /api，必须用绝对地址访问后端。
  // 构建前设置：VITE_API_BASE_URL=https://你的后端域名  再 npm run build
  // 详见 deploy/APK.md
}

export default config
