<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { Html5Qrcode } from 'html5-qrcode'
import { createScanApi } from '@/api/scan'
import { useUserStore } from '@/stores/user'
import { analyzeLocal, isNetworkError, isOffline } from '@/utils/offline'
import { queueOfflineScan } from '@/utils/offlineSync'

const router = useRouter()
const userStore = useUserStore()
const barcode = ref('')
const scanning = ref(false)
const showProfileSwitch = ref(false)

let scanner: Html5Qrcode | null = null
let submitting = false

onMounted(() => {
  // 直接刷新进入扫码页时，确保档案已加载（activeProfile 才有效）
  void userStore.fetchProfiles()
})

const profileActions = computed(() =>
  userStore.profiles.map((p) => ({
    name: `${p.emoji || '👤'} ${p.name}${p.is_default ? '（默认）' : ''}`,
    id: p.id,
  })),
)

function onSelectProfile(action: { name: string; id: number }) {
  const p = userStore.profiles.find((x) => x.id === action.id)
  if (p) userStore.setActiveProfile(p.id)
  showProfileSwitch.value = false
}

async function startScan() {
  // 先切到扫描态并等容器可见；#qr-reader 用 v-show 常驻 DOM，构造函数才不会报「元素不存在」
  scanning.value = true
  await nextTick()
  try {
    scanner = new Html5Qrcode('qr-reader')
    await scanner.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 220, height: 220 } },
      (text) => void handleDecode(text),
      () => {
        // 逐帧识别失败的回调，静默处理
      },
    )
  } catch {
    scanner = null
    scanning.value = false
    showToast('无法打开摄像头，请检查权限或使用手动输入')
  }
}

async function stopScan() {
  if (!scanner) return
  try {
    await scanner.stop()
  } catch {
    // 未开启时 stop 会抛错，忽略
  }
  scanner.clear()
  scanner = null
  scanning.value = false
}

async function handleDecode(text: string) {
  if (!text) return
  await stopScan()
  await submitScan(text, 'camera')
}

async function submitScan(code: string, source: 'camera' | 'manual') {
  if (submitting) return
  submitting = true
  try {
    // 明确断网：直接本地安全分析，不发请求
    if (isOffline()) {
      goOffline(code, source)
      return
    }
    const scan = await createScanApi(code, source, userStore.activeProfile?.id)
    router.push({ path: `/product/${code}`, query: { scan_id: scan.id } })
  } catch (err) {
    // 断网/超时 → 降级到本地；商品不存在等业务错误已由拦截器提示
    if (isNetworkError(err)) goOffline(code, source)
  } finally {
    submitting = false
  }
}

function goOffline(code: string, source: 'camera' | 'manual') {
  const result = analyzeLocal(code, userStore.activeProfile)
  if (!result) {
    showToast('暂无该商品数据')
    return
  }
  // 记录扫码那一刻的档案，联网后按该档案补传
  queueOfflineScan(code, source, userStore.activeProfile?.id ?? null)
  showToast('已进入离线安全模式')
  router.push({ path: `/product/${code}`, query: { offline: '1' } })
}

function onToggleScan() {
  if (scanning.value) void stopScan()
  else void startScan()
}

function onManualSearch() {
  const code = barcode.value.trim()
  if (!code) {
    showToast('请输入条形码')
    return
  }
  void submitScan(code, 'manual')
}

onBeforeUnmount(() => {
  void stopScan()
})
</script>

<template>
  <div class="page">
    <van-nav-bar title="扫码" />
    <div class="profile-bar" @click="showProfileSwitch = true">
      <span class="profile-bar-label">给谁买</span>
      <span class="profile-bar-value">
        {{ userStore.activeProfile ? `${userStore.activeProfile.emoji || '👤'} ${userStore.activeProfile.name}` : '未选择' }}
      </span>
      <van-icon name="arrow-down" />
    </div>
    <div class="scan-body">
      <div v-show="scanning" class="scan-area">
        <div id="qr-reader" class="qr-reader" />
      </div>
      <van-empty v-if="!scanning" class="scan-empty" description="点击下方按钮开启摄像头扫码" />
      <div class="manual-area">
        <van-field v-model="barcode" type="digit" placeholder="或手动输入商品条形码" clearable>
          <template #button>
            <van-button size="small" type="primary" @click="onManualSearch">查询</van-button>
          </template>
        </van-field>
      </div>
      <div class="scan-actions">
        <van-button type="primary" block round @click="onToggleScan">
          {{ scanning ? '关闭摄像头' : '开启摄像头扫码' }}
        </van-button>
        <p class="tip">示例条码：6901234567890（花生夹心燕麦饼干）</p>
      </div>
    </div>

    <van-action-sheet
      v-model:show="showProfileSwitch"
      title="给谁买"
      :actions="profileActions"
      cancel-text="取消"
      @select="onSelectProfile"
    />
  </div>
</template>

<style scoped>
.page {
  min-height: calc(100vh - var(--van-tabbar-height, 50px));
  display: flex;
  flex-direction: column;
}
.profile-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 12px 16px 0;
  padding: 10px 14px;
  background: #fff;
  border-radius: 8px;
  font-size: 14px;
}
.profile-bar-label {
  color: #969799;
}
.profile-bar-value {
  flex: 1;
  font-weight: 500;
}
.scan-body {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.scan-area {
  margin: 12px;
}
.qr-reader {
  min-height: 240px;
  width: 100%;
}
.scan-empty {
  flex: 1;
}
.manual-area {
  margin: 12px;
}
.scan-actions {
  margin: 12px;
}
.tip {
  color: #969799;
  font-size: 12px;
  text-align: center;
}
</style>
