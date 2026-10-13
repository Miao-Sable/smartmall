// 离线扫描补传：断网时把扫描压入本地队列，联网后逐条 POST /scan 补传。
// 补传时按「扫码那一刻」的档案（profile_id）重新分析，后端结果与离线一致。
import { showToast } from 'vant'
import { createScanApi } from '@/api/scan'
import { isNetworkError } from './offline'

const QUEUE_KEY = 'pending-offline-scans'

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
}

export function clearOfflineQueue() {
  localStorage.removeItem(QUEUE_KEY)
}

let flushing = false

/** 联网后补传队列，返回成功补传条数；未登录或队列为空返回 0 */
export async function flushOfflineScans(): Promise<number> {
  if (flushing) return 0
  if (!localStorage.getItem('token')) return 0
  const list = readQueue()
  if (!list.length) return 0

  flushing = true
  let synced = 0
  const remaining: PendingScan[] = []
  let networkDown = false
  try {
    for (const item of list) {
      if (networkDown) {
        remaining.push(item)
        continue
      }
      try {
        await createScanApi(item.barcode, item.source, item.profile_id)
        synced++
      } catch (err) {
        if (isNetworkError(err)) {
          // 仍断网：保留本条及后续，下次再试
          networkDown = true
          remaining.push(item)
        }
        // 业务错误（404 商品/档案已删除）：丢弃，不再重试
      }
    }
  } finally {
    writeQueue(remaining)
    flushing = false
  }

  if (synced > 0) showToast(`已补传 ${synced} 条离线扫描记录`)
  return synced
}

/** 在 main.ts 调用一次：注册联网事件，并在启动时（若已在线）立即补传 */
export function initOfflineSync() {
  window.addEventListener('online', () => {
    void flushOfflineScans()
  })
  if (typeof navigator !== 'undefined' && navigator.onLine) void flushOfflineScans()
}
