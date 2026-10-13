import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Vant from 'vant'
import 'vant/lib/index.css'

import App from './App.vue'
import router from './router'
import './styles/index.css'
import { initOfflineSync } from './utils/offlineSync'

const app = createApp(App)

app.use(createPinia())
app.use(router)
// Vant 组件库（MVP 阶段完整引入，后续可按需引入减小体积）
app.use(Vant)

app.mount('#app')

// 离线扫描补传：联网后自动同步积压的离线记录
initOfflineSync()
