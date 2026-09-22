<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { Html5Qrcode } from 'html5-qrcode'
import { createScanApi } from '@/api/scan'

const router = useRouter()
const barcode = ref('')
const scanning = ref(false)

let scanner: Html5Qrcode | null = null
let submitting = false

async function startScan() {
  // 先显示摄像头容器并等 DOM 更新，否则库初始化时找不到 #qr-reader
  scanning.value = true
  await nextTick()
  scanner = new Html5Qrcode('qr-reader')
  try {
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
    const scan = await createScanApi(code, source)
    router.push({ path: `/product/${code}`, query: { scan_id: scan.id } })
  } catch {
    // 商品不存在等错误已由拦截器提示
  } finally {
    submitting = false
  }
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
    <div class="scan-body">
      <div v-if="scanning" class="scan-area">
        <div id="qr-reader" class="qr-reader" />
      </div>
      <van-empty v-else class="scan-empty" description="点击下方按钮开启摄像头扫码" />
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
  </div>
</template>

<style scoped>
.page {
  min-height: calc(100vh - var(--van-tabbar-height, 50px));
  display: flex;
  flex-direction: column;
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
