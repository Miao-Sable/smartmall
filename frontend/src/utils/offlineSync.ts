// 离线扫描补传：断网时把扫描压入本地队列，联网后逐条 POST /scan 补传。
// 补传时按「扫码那一刻」的档案（profile_id）重新分析，后端结果与离线一致。
import { showToast } from 'vant'
import { createScanApi } from '@/api/scan'
import { isNetworkError } from './offline'

const QUEUE_KEY = 'pending-offline-scans'
// 队列未清空时，每 15s 自动重试一次补传（兜底「后端宕机」等 navigator.onLine 未变化的场景）
const RETRY_INTERVAL = 15000

interface PendingScan {
  barcode: string
  source: 'camera' | 'manual'
  profile_id: number | null
}

function readQueue(): PendingScan[] {
  try {
    const raw = localStorage.getItem(QUEUE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as PendingScan[]) : []
  } catch {
    return []
  }
}

function writeQueue(list: PendingScan[]) {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(list))
}

/** 离线扫码成功时入队，等待联网补传 */
export function queueOfflineScan(barcode: string, source: 'camera' | 'manual', profileId: number | null) {
  const list = readQueue()
  list.push({ barcode, source, profile_id: profileId })
  writeQueue(list)
  // 入队即安排自动重试，避免依赖 online 事件漏触发（如后端宕机时 navigator.onLine 仍为 true）
  scheduleRetry()
}

export function clearOfflineQueue() {
  localStorage.removeItem(QUEUE_KEY)
  stopRetry()
}

let flushing = false

/** 是否应保留并稍后重试：网络层失败（断网/超时）或服务器 5xx 临时故障。
 *  4xx（商品 404 / 档案已删除等确定失败）则丢弃，不再重试。 */
function isRetryable(err: unknown): boolean {
  if (isNetworkError(err)) return true
  const status = (err as { response?: { status?: number } }).response?.status
  return typeof status === 'number' && status >= 500
}

/** 联网后补传队列，返回成功补传条数；未登录或队列为空返回 0 */
export async function flushOfflineScans(): Promise<number> {
  if (flushing) return 0
  if (!localStorage.getItem('token')) return 0
  const list = readQueue()
  if (!list.length) {
    stopRetry()
    return 0
  }

  flushing = true
  let synced = 0
  const remaining: PendingScan[] = []
  let unavailable = false
  try {
    for (const item of list) {
      if (unavailable) {
        remaining.push(item)
        continue
      }
      try {
        await createScanApi(item.barcode, item.source, item.profile_id)
        synced++
      } catch (err) {
        if (isRetryable(err)) {
          // 网络/服务器仍不可用：保留本条及后续，下次再试
          unavailable = true
          remaining.push(item)
        }
        // 业务确定失败（404 商品/档案已删除等）：丢弃，不再重试
      }
    }
  } finally {
    writeQueue(remaining)
    flushing = false
    if (remaining.length) scheduleRetry()
    else stopRetry()
  }

  if (synced > 0) showToast(`已补传 ${synced} 条离线扫描记录`)
  return synced
}

let retryTimer: ReturnType<typeof setTimeout> | null = null

/** 队列未清空且网络可用时，安排一次延迟重试；已有定时器则跳过 */
function scheduleRetry() {
  if (retryTimer) return
  if (!localStorage.getItem('token')) return
  if (!readQueue().length) return
  // 明确处于断网态时不空转：恢复网络会触发 online 事件补传
  if (typeof navigator !== 'undefined' && navigator.onLine === false) return
  retryTimer = setTimeout(() => {
    retryTimer = null
    void flushOfflineScans()
  }, RETRY_INTERVAL)
}

function stopRetry() {
  if (retryTimer) {
    clearTimeout(retryTimer)
    retryTimer = null
  }
}

/** 在 main.ts 调用一次：注册联网事件，并在启动时（若已在线）立即补传；遗留队列则自动重试 */
export function initOfflineSync() {
  window.addEventListener('online', () => {
    void flushOfflineScans()
  })
  if (typeof navigator !== 'undefined' && navigator.onLine) void flushOfflineScans()
  scheduleRetry()
}
