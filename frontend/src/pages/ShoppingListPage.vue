<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { showToast } from 'vant'
import { precheckApi, rematchApi, type PrecheckItem, type ProductBrief } from '@/api/shopping-list'

const SAVE_HISTORY_KEY = 'shopping-list-scheme-history'
const MAX_HISTORY = 50

// —— 主输入 ——
const rawText = ref('')
const pasting = ref(false)
const importing = ref(false)

// —— 导入结果 toast ——
const showResult = ref(false)
const resultItems = ref<PrecheckItem[]>([])

const matchedItems = computed(() => resultItems.value.filter((i) => i.match_type !== 'not_found'))
const notFound = computed(() =>
  resultItems.value.filter((i) => i.match_type === 'not_found').map((i) => i.name),
)
const hasHighRisk = computed(() => resultItems.value.some((i) => i.is_high_risk))

// 导入结果排序优先级：过敏源(精确) > 过敏源(模糊) > 其他
function priorityOf(item: PrecheckItem): number {
  const allergen = item.allergen_hits.length > 0
  const fuzzy = item.match_type === 'fuzzy'
  if (allergen && !fuzzy) return 0
  if (allergen && fuzzy) return 1
  return 2
}

const sortedMatchedItems = computed(() =>
  [...matchedItems.value].sort((a, b) => priorityOf(a) - priorityOf(b)),
)

// 导入结果建议理由：仅过敏源
function suggestReason(item: PrecheckItem): string {
  const allergens = uniqueAllergens(item)
  return allergens.length ? `含${allergens.join('、')}` : ''
}

// —— rematch 副窗口 ——
const rematchTarget = ref<PrecheckItem | null>(null)
const rematchCandidates = ref<ProductBrief[]>([])
const rematchLoading = ref(false)

// —— 替代方案对比 ——
interface SchemeRow {
  item: PrecheckItem
  keptIndex: number | null // 选中的替代品下标；null = 保留原商品（取消替换）
  removed: boolean
}
const showScheme = ref(false)
const schemeRows = ref<SchemeRow[]>([])

// —— 最近一次保存 / 历史 ——
interface SavedEntry {
  original: string
  replacement: string | null // null = 已删除
}
interface SavedScheme {
  entries: SavedEntry[]
  savedAt: string
}
interface SchemeDisplayItem {
  name: string
  changed: boolean
  removed?: boolean
}
const schemeHistory = ref<SavedScheme[]>([])
const lastSaved = computed(() => schemeHistory.value[0] ?? null)
const pastHistory = computed(() => schemeHistory.value.slice(1))
const pastShown = computed(() => pastHistory.value.slice(0, 3))
const showDetail = ref(false)
const detailScheme = ref<SavedScheme | null>(null)
const showMore = ref(false)

onMounted(() => {
  try {
    const raw = localStorage.getItem(SAVE_HISTORY_KEY)
    if (raw) {
      const arr = JSON.parse(raw)
      if (Array.isArray(arr)) {
        schemeHistory.value = arr.filter((s: unknown) => Array.isArray((s as SavedScheme)?.entries))
      }
    } else {
      // 迁移旧的单方案存储
      const oldRaw = localStorage.getItem('shopping-list-last-scheme')
      if (oldRaw) {
        const old = JSON.parse(oldRaw) as SavedScheme
        if (Array.isArray(old?.entries)) {
          schemeHistory.value = [{ entries: old.entries, savedAt: new Date().toISOString() }]
        }
      }
    }
  } catch {
    // 忽略损坏的本地数据
  }
})

function splitItems(text: string): string[] {
  // 先按换行、逗号、顿号、斜杠、分号拆成多行；每行内部再按空格拆成多个商品名
  return text
    .split(/[\n,，、\/;；]+/)
    .flatMap((line) => line.split(/\s+/))
    .map((s) => s.trim())
    .filter(Boolean)
}

// —— 粘贴 / 导入 ——
async function onPaste() {
  pasting.value = true
  try {
    const text = await navigator.clipboard.readText()
    if (!text.trim()) {
      showToast('剪贴板为空')
      return
    }
    rawText.value = text
    showToast({ message: '已粘贴', type: 'success' })
  } catch {
    showToast('无法读取剪贴板，请长按输入框手动粘贴')
  } finally {
    pasting.value = false
  }
}

async function onImport() {
  const items = splitItems(rawText.value)
  if (!items.length) {
    showToast('请先输入或粘贴商品')
    return
  }
  importing.value = true
  try {
    const res = await precheckApi(items)
    resultItems.value = res.items
    showResult.value = true
  } catch {
    // 拦截器已统一提示
  } finally {
    importing.value = false
  }
}

function closeResult() {
  showResult.value = false
  rematchTarget.value = null
}

// —— rematch ——
async function onRematch(item: PrecheckItem) {
  rematchTarget.value = item
  rematchCandidates.value = []
  rematchLoading.value = true
  try {
    rematchCandidates.value = await rematchApi(item.name, item.product ? [item.product.id] : [])
  } catch {
    // 拦截器已统一提示
  } finally {
    rematchLoading.value = false
  }
}

function closeRematch() {
  rematchTarget.value = null
  rematchCandidates.value = []
}

async function pickCandidate(candidate: ProductBrief) {
  // 选中候选：替换当前匹配商品，并重新调用 precheck 重算风险与替代品
  const target = rematchTarget.value
  if (!target) return
  try {
    const res = await precheckApi([candidate.name])
    const item = res.items[0]
    const idx = resultItems.value.findIndex((it) => it.name === target.name)
    if (idx >= 0 && item && item.match_type !== 'not_found') {
      resultItems.value.splice(idx, 1, item)
    }
  } catch {
    // 拦截器已统一提示
  } finally {
    closeRematch()
  }
}

function onDeleteItem() {
  const target = rematchTarget.value
  if (!target) return
  resultItems.value = resultItems.value.filter((it) => it.name !== target.name)
  closeRematch()
}

function onRerematch() {
  // 没有更多候选时，保留当前匹配并关闭副窗口
  closeRematch()
}

// —— 替代方案对比 ——
function onGenerateScheme() {
  schemeRows.value = resultItems.value
    .filter((i) => i.is_high_risk)
    .map((i) => ({
      item: i,
      keptIndex: i.alternatives.length ? 0 : null,
      removed: false,
    }))
  showResult.value = false
  rematchTarget.value = null
  showScheme.value = true
}

function closeScheme() {
  showScheme.value = false
}

function cycleAlt(rowIndex: number) {
  const row = schemeRows.value[rowIndex]
  const len = row.item.alternatives.length
  if (!len) return
  row.keptIndex = ((row.keptIndex ?? 0) + 1) % len
}

function removeAlt(rowIndex: number) {
  schemeRows.value[rowIndex].removed = true
}

function restoreAlt(rowIndex: number) {
  schemeRows.value[rowIndex].removed = false
}

function cancelAlt(rowIndex: number) {
  schemeRows.value[rowIndex].keptIndex = null
}

function reselectAlt(rowIndex: number) {
  const row = schemeRows.value[rowIndex]
  if (row.item.alternatives.length) row.keptIndex = 0
}

function uniqueAllergens(item: PrecheckItem): string[] {
  return [...new Set(item.allergen_hits.map((h) => h.allergen_name))]
}

// 原商品侧：红色关键词标签（仅过敏源），如「含牛奶」
function originalTag(item: PrecheckItem): string {
  const names = uniqueAllergens(item)
  return names.length ? `含${names.join('、')}` : ''
}

// 新商品侧：饮食偏好正向词标签，如「低脂」；过敏相关则不显示
function alternativeTag(item: PrecheckItem): string {
  if (uniqueAllergens(item).length) return ''
  return item.diet_hits.length ? item.diet_hits.join('、') : ''
}

function isChangedEntry(e: SavedEntry) {
  return e.replacement === null || e.replacement !== e.original
}

function buildEntries(): SavedEntry[] {
  const rowByName = new Map(schemeRows.value.map((r) => [r.item.name, r]))
  const entries: SavedEntry[] = []
  for (const item of resultItems.value) {
    if (item.match_type === 'not_found' || !item.product) continue
    const original = item.product.name
    if (!item.is_high_risk) {
      entries.push({ original, replacement: original })
      continue
    }
    const row = rowByName.get(item.name)
    if (row && row.removed) {
      entries.push({ original, replacement: null })
    } else if (row && row.keptIndex !== null) {
      entries.push({ original, replacement: item.alternatives[row.keptIndex].name })
    } else {
      entries.push({ original, replacement: original })
    }
  }
  return entries
}

function buildNewScheme(): string[] {
  return buildEntries()
    .filter((e) => e.replacement !== null)
    .map((e) => e.replacement as string)
}

const detailOriginalItems = computed<SchemeDisplayItem[]>(() => {
  const entries = detailScheme.value?.entries ?? []
  const changed = entries.filter(isChangedEntry).map((e) => ({
    name: e.original,
    changed: true,
    removed: e.replacement === null,
  }))
  const unchanged = entries.filter((e) => !isChangedEntry(e)).map((e) => ({ name: e.original, changed: false }))
  return [...changed, ...unchanged]
})

const detailNewItems = computed<SchemeDisplayItem[]>(() => {
  const entries = detailScheme.value?.entries ?? []
  const changed = entries
    .filter((e) => isChangedEntry(e) && e.replacement !== null)
    .map((e) => ({ name: e.replacement as string, changed: true }))
  const unchanged = entries
    .filter((e) => !isChangedEntry(e))
    .map((e) => ({ name: e.replacement as string, changed: false }))
  return [...changed, ...unchanged]
})

function hasChanges(scheme: SavedScheme): boolean {
  return scheme.entries.some(isChangedEntry)
}

function schemeSummaryLabels(scheme: SavedScheme): string[] {
  const changed = scheme.entries.filter(isChangedEntry)
  if (changed.length) return changed.map((e) => e.replacement ?? '已删除')
  return scheme.entries.map((e) => e.original)
}

function summaryText(scheme: SavedScheme): string {
  const total = scheme.entries.length
  const labels = schemeSummaryLabels(scheme)
  const head = labels.slice(0, 2).join('、')
  return total > 2 ? `${head} 等 ${total} 件商品` : head
}

function formatDateTime(iso: string): string {
  const d = new Date(iso)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function openDetail(scheme: SavedScheme) {
  detailScheme.value = scheme
  showDetail.value = true
}

const changedEntries = computed(() => (lastSaved.value?.entries ?? []).filter(isChangedEntry))
const unchangedEntries = computed(() => (lastSaved.value?.entries ?? []).filter((e) => !isChangedEntry(e)))

function saveScheme(entries: SavedEntry[]) {
  const scheme: SavedScheme = { entries, savedAt: new Date().toISOString() }
  schemeHistory.value = [scheme, ...schemeHistory.value].slice(0, MAX_HISTORY)
  localStorage.setItem(SAVE_HISTORY_KEY, JSON.stringify(schemeHistory.value))
}

function buildNoChangeEntries(): SavedEntry[] {
  return resultItems.value
    .filter((i) => i.match_type !== 'not_found' && i.product)
    .map((i) => ({ original: i.product!.name, replacement: i.product!.name }))
}

function confirmNoChange() {
  saveScheme(buildNoChangeEntries())
  closeResult()
}

function onSaveScheme() {
  saveScheme(buildEntries())
  showScheme.value = false
  showToast({ message: '已保存新方案', type: 'success' })
}

async function onCopyScheme() {
  const text = buildNewScheme().join('\n')
  try {
    await navigator.clipboard.writeText(text)
    showToast({ message: '已复制新方案', type: 'success' })
  } catch {
    fallbackCopy(text)
  }
}

function fallbackCopy(text: string) {
  const el = document.createElement('textarea')
  el.value = text
  el.style.position = 'fixed'
  el.style.opacity = '0'
  document.body.appendChild(el)
  el.select()
  try {
    document.execCommand('copy')
    showToast({ message: '已复制新方案', type: 'success' })
  } catch {
    showToast('复制失败，请手动复制')
  } finally {
    document.body.removeChild(el)
  }
}

async function copyText(text: string, message: string) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    showToast({ message, type: 'success' })
  } catch {
    showToast('复制失败，请手动复制')
  }
}

function copySchemeOriginal(scheme: SavedScheme) {
  void copyText(
    scheme.entries.map((e) => e.original).join('\n'),
    '已复制原方案',
  )
}

function copySchemeNew(scheme: SavedScheme) {
  const names = scheme.entries.filter((e) => e.replacement !== null).map((e) => e.replacement as string)
  void copyText(names.join('\n'), '已复制新方案')
}
</script>

<template>
  <div class="page">
    <van-nav-bar title="购物清单预检" left-arrow @click-left="$router.back()" />

    <!-- 方形输入区 -->
    <div class="input-box">
      <van-field
        v-model="rawText"
        type="textarea"
        class="square-input"
        placeholder="粘贴或输入商品名，支持换行 / 逗号 / 空格分隔"
      />
      <div class="input-actions">
        <van-button size="small" plain type="primary" :loading="pasting" @click="onPaste">粘贴</van-button>
        <van-button size="small" type="primary" :loading="importing" @click="onImport">导入并预检</van-button>
      </div>
      <p class="tip">示例：牛奶、面包、可乐</p>
    </div>

    <!-- 方案展示区：左最近一次调整方案，右历史调整方案 -->
    <div v-if="lastSaved" class="scheme-panel">
      <div class="scheme-box">
        <div class="scheme-box-head">
          <span class="scheme-box-title">最近一次调整方案</span>
          <van-button size="small" type="primary" @click="openDetail(lastSaved)">展开</van-button>
        </div>
        <div class="scheme-box-body">
          <template v-if="changedEntries.length">
            <div v-for="(e, i) in changedEntries" :key="i" class="change-row">
              <span class="change-orig">{{ e.original }}</span>
              <span class="change-arrow">→</span>
              <span class="change-new" :class="{ removed: e.replacement === null }">{{ e.replacement ?? '已删除' }}</span>
            </div>
            <div v-if="unchangedEntries.length" class="last-unchanged">
              <template v-if="unchangedEntries.length > 2">
                {{ unchangedEntries.slice(0, 2).map((e) => e.original).join('、') }} 等 {{ unchangedEntries.length }} 件商品
              </template>
              <template v-else>
                {{ unchangedEntries.map((e) => e.original).join('、') }}
              </template>
            </div>
          </template>
          <div v-else class="no-change-line">原方案：{{ summaryText(lastSaved) }}</div>
        </div>
        <div class="scheme-box-foot">
          <van-button size="small" type="primary" @click="changedEntries.length ? copySchemeNew(lastSaved) : copySchemeOriginal(lastSaved)">
            {{ changedEntries.length ? '复制新方案' : '复制原方案' }}
          </van-button>
        </div>
      </div>

      <div class="scheme-box">
        <div class="scheme-box-head">
          <span class="scheme-box-title">历史调整方案</span>
          <van-button v-if="pastHistory.length" size="small" type="primary" @click="showMore = true">更多</van-button>
        </div>
        <div class="scheme-box-body">
          <div v-for="(s, i) in pastShown" :key="i" class="history-item" @click="openDetail(s)">
            <div class="history-time">{{ formatDateTime(s.savedAt) }}</div>
            <div class="history-summary">{{ summaryText(s) }}</div>
          </div>
          <div v-if="!pastShown.length" class="history-empty">暂无历史方案</div>
        </div>
      </div>
    </div>

    <!-- 导入结果 toast -->
    <transition name="fade">
      <div v-if="showResult" class="overlay">
        <div class="toast-card">
          <div class="toast-head">
            <span class="toast-title">导入结果</span>
            <van-icon name="cross" class="toast-close" @click="closeResult" />
          </div>

          <div class="toast-body">
            <!-- 打勾动画 -->
            <svg class="checkmark" viewBox="0 0 52 52">
              <circle class="checkmark-circle" cx="26" cy="26" r="25" fill="none" />
              <path class="checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8" />
            </svg>
            <div class="check-text">已导入 {{ matchedItems.length }} 件商品</div>

            <!-- 匹配结果 -->
            <div v-for="(item, i) in sortedMatchedItems" :key="i" class="match-row">
              <span class="match-name" :class="{ dim: item.match_type === 'fuzzy' }">
                {{ item.match_type === 'fuzzy' ? `已为您匹配：${item.product?.name}` : item.product?.name }}
              </span>
              <span class="match-marks">
                <van-button v-if="item.match_type === 'fuzzy'" size="mini" plain @click="onRematch(item)">不是这个？</van-button>
                <template v-if="item.allergen_hits.length">
                  <van-tag type="danger" plain>{{ suggestReason(item) }}</van-tag>
                </template>
                <span v-else class="safe-mark">✅</span>
              </span>
            </div>

            <!-- 未匹配商品 -->
            <div v-if="notFound.length" class="notfound">
              <svg class="sad" viewBox="0 0 40 40">
                <circle cx="20" cy="20" r="18" fill="#ffd666" />
                <circle cx="14" cy="16" r="2" fill="#323233" />
                <circle cx="26" cy="16" r="2" fill="#323233" />
                <path d="M13 28 Q20 23 27 28" stroke="#323233" stroke-width="2" fill="none" stroke-linecap="round" />
              </svg>
              <div class="notfound-text">以下商品未找到，已从清单删除：{{ notFound.join('、') }}</div>
            </div>
          </div>

          <div class="toast-foot">
            <template v-if="hasHighRisk">
              <van-button block round type="primary" @click="onGenerateScheme">生成替代方案</van-button>
              <van-button block round plain class="skip-btn" @click="confirmNoChange">我已确认，跳过生成替代方案</van-button>
            </template>
            <van-button v-else block round type="primary" @click="confirmNoChange">确定</van-button>
          </div>

          <!-- rematch 副窗口 -->
          <div v-if="rematchTarget" class="sub-window">
            <div class="sub-panel">
              <div class="sub-head">
                <span>选择正确的商品</span>
                <van-icon name="cross" @click="closeRematch" />
              </div>
              <div class="sub-body">
                <van-loading v-if="rematchLoading" class="sub-loading" size="24" />
                <template v-else-if="rematchCandidates.length">
                  <div
                    v-for="c in rematchCandidates"
                    :key="c.id"
                    class="candidate"
                    @click="pickCandidate(c)"
                  >
                    <span>{{ c.name }}</span>
                  </div>
                </template>
                <template v-else>
                  <div class="sub-empty">没有更多匹配了</div>
                  <div class="sub-actions">
                    <van-button size="small" type="danger" plain @click="onDeleteItem">删除</van-button>
                    <van-button size="small" plain @click="onRerematch">重新匹配</van-button>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 替代方案对比 -->
    <transition name="fade">
      <div v-if="showScheme" class="overlay">
        <div class="scheme-card">
          <div class="scheme-head">
            <span>替代方案对比</span>
            <van-icon name="cross" @click="closeScheme" />
          </div>
          <div class="scheme-cols">
            <div class="col-label col-label-left">原方案</div>
            <div class="col-label col-label-right">新方案</div>
          </div>
          <div class="scheme-body">
            <div v-for="(row, i) in schemeRows" :key="i" class="scheme-row">
              <div class="scheme-left">
                <div class="p-name-row">
                  <span class="p-name">{{ row.item.product?.name }}</span>
                  <van-tag v-if="originalTag(row.item)" type="danger">{{ originalTag(row.item) }}</van-tag>
                </div>
              </div>
              <div class="scheme-right">
                <template v-if="row.removed">
                  <span class="state-text">已移除</span>
                  <van-button size="mini" plain @click="restoreAlt(i)">恢复</van-button>
                </template>
                <template v-else-if="row.keptIndex === null">
                  <span class="state-text">保留原商品</span>
                  <van-button v-if="row.item.alternatives.length" size="mini" plain @click="reselectAlt(i)">替换</van-button>
                </template>
                <template v-else>
                  <div class="p-name-row">
                    <span class="p-name">{{ row.item.alternatives[row.keptIndex].name }}</span>
                    <van-tag v-if="alternativeTag(row.item)" type="success" plain>{{ alternativeTag(row.item) }}</van-tag>
                  </div>
                  <div class="alt-actions">
                    <van-button v-if="row.item.alternatives.length > 1" size="mini" plain @click="cycleAlt(i)">换一个</van-button>
                    <van-button size="mini" plain @click="removeAlt(i)">删除</van-button>
                    <van-button size="mini" plain type="warning" @click="cancelAlt(i)">取消替换</van-button>
                  </div>
                </template>
              </div>
            </div>
          </div>
          <div class="scheme-foot">
            <van-button block round type="primary" @click="onSaveScheme">确认并保存新方案</van-button>
            <van-button block round plain type="primary" class="copy-btn" @click="onCopyScheme">复制新方案</van-button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 方案详情弹窗 -->
    <transition name="fade">
      <div v-if="showDetail" class="overlay">
        <div class="last-detail-card">
          <div class="detail-head">
            <span>方案详情</span>
            <van-icon name="cross" @click="showDetail = false" />
          </div>
          <div class="detail-body">
            <div class="detail-cols">
              <div class="detail-col">
                <div class="detail-col-title">原方案</div>
                <div v-for="(it, i) in detailOriginalItems" :key="i" class="detail-item" :class="{ removed: it.removed }">{{ it.name }}</div>
              </div>
              <div v-if="detailScheme && hasChanges(detailScheme)" class="detail-col">
                <div class="detail-col-title">新方案</div>
                <div v-for="(it, i) in detailNewItems" :key="i" class="detail-item" :class="{ changed: it.changed }">{{ it.name }}</div>
              </div>
            </div>
          </div>
          <div class="detail-foot">
            <van-button size="small" plain type="primary" @click="detailScheme && copySchemeOriginal(detailScheme)">复制原方案</van-button>
            <van-button v-if="detailScheme && hasChanges(detailScheme)" size="small" plain type="primary" @click="detailScheme && copySchemeNew(detailScheme)">复制新方案</van-button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 历史方案更多弹窗 -->
    <transition name="fade">
      <div v-if="showMore" class="overlay">
        <div class="last-detail-card">
          <div class="detail-head">
            <span>历史调整方案</span>
            <van-icon name="cross" @click="showMore = false" />
          </div>
          <div class="detail-body">
            <div v-for="(s, i) in pastHistory" :key="i" class="more-item" @click="showMore = false; openDetail(s)">
              <div class="history-time">{{ formatDateTime(s.savedAt) }}</div>
              <div class="history-summary">{{ summaryText(s) }}</div>
            </div>
            <div v-if="!pastHistory.length" class="history-empty">暂无历史方案</div>
          </div>
          <div class="detail-note">最多保存 50 条历史方案</div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.page {
  --input-h: 240px; /* 导入文本框固定高度 */
  min-height: 100vh;
  padding-bottom: 24px;
}
.input-box {
  margin: 12px 16px;
}
.square-input {
  background: #fff;
  border-radius: 12px;
  padding: 12px;
}
.square-input :deep(.van-field__control) {
  height: var(--input-h);
  overflow-y: auto;
  line-height: 1.6;
}
.input-actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}
.input-actions .van-button {
  flex: 1;
}
.tip {
  margin: 8px 0 0;
  color: #969799;
  font-size: 12px;
  text-align: center;
}
.scheme-panel {
  display: flex;
  gap: 10px;
  margin: 0 16px 12px;
}
.scheme-box {
  flex: 1;
  min-width: 0;
  padding: 12px;
  background: #fff;
  border-radius: 8px;
}
.scheme-box-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 6px;
}
.scheme-box-title {
  font-size: 14px;
  font-weight: 600;
}
.last-changes {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.change-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  line-height: 1.6;
}
.change-orig {
  color: #969799;
}
.change-arrow {
  color: #c8c9cc;
}
.change-new {
  color: #ee0a24;
  font-weight: 500;
}
.change-new.removed {
  color: #969799;
}
.last-unchanged {
  margin-top: 6px;
  color: #969799;
  font-size: 12px;
  line-height: 1.6;
}
.no-change-line {
  color: #646566;
  font-size: 13px;
  line-height: 1.6;
}
.scheme-box-foot {
  margin-top: 10px;
}
.scheme-box-foot .van-button {
  width: 100%;
}
.history-item {
  padding: 6px 0;
  border-bottom: 1px solid #f7f8fa;
  cursor: pointer;
}
.history-item:last-child {
  border-bottom: none;
}
.history-time {
  color: #969799;
  font-size: 11px;
}
.history-summary {
  margin-top: 2px;
  color: #646566;
  font-size: 12px;
  line-height: 1.5;
  word-break: break-all;
}
.history-empty {
  color: #969799;
  font-size: 12px;
  padding: 8px 0;
}
.more-item {
  padding: 10px 0;
  border-bottom: 1px solid #f7f8fa;
  cursor: pointer;
}
.more-item:last-child {
  border-bottom: none;
}
.detail-note {
  flex: none;
  padding: 8px 16px;
  color: #c8c9cc;
  font-size: 11px;
  text-align: left;
  border-top: 1px solid #f2f3f5;
}
.last-detail-card {
  width: 300px;
  max-width: 90vw;
  height: 70vh;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
}
.detail-head {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid #f2f3f5;
}
.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}
.detail-cols {
  display: flex;
  gap: 12px;
}
.detail-col {
  flex: 1;
  min-width: 0;
}
.detail-col-title {
  font-size: 12px;
  color: #969799;
  margin-bottom: 4px;
}
.detail-item {
  color: #646566;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-all;
}
.detail-item.changed {
  color: #ee0a24;
}
.detail-item.removed {
  color: #969799;
  text-decoration: line-through;
}
.detail-foot {
  flex: none;
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid #f2f3f5;
}
.detail-foot .van-button {
  flex: 1;
}

/* —— 遮罩与 toast —— */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}
.toast-card {
  position: relative;
  width: 88%;
  max-height: 78vh;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
}
.toast-head {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #f2f3f5;
}
.toast-title {
  font-size: 16px;
  font-weight: 600;
}
.toast-close {
  font-size: 18px;
  color: #969799;
}
.toast-body {
  flex: 1;
  position: relative;
  overflow-y: auto;
  padding: 16px;
}
.checkmark {
  width: 48px;
  height: 48px;
  display: block;
  margin: 0 auto;
}
.checkmark-circle {
  stroke: #07c160;
  stroke-width: 2;
  stroke-dasharray: 166;
  stroke-dashoffset: 166;
  animation: stroke 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards;
}
.checkmark-check {
  stroke: #07c160;
  stroke-width: 4;
  stroke-dasharray: 48;
  stroke-dashoffset: 48;
  animation: stroke 0.3s 0.8s cubic-bezier(0.65, 0, 0.45, 1) forwards;
}
@keyframes stroke {
  to {
    stroke-dashoffset: 0;
  }
}
.check-text {
  text-align: center;
  color: #646566;
  font-size: 13px;
  margin: 8px 0 12px;
}
.match-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #f7f8fa;
}
.match-name {
  font-size: 14px;
}
.match-marks {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: none;
}
.safe-mark {
  font-size: 16px;
  line-height: 22px;
}
.dim {
  color: #969799;
  font-size: 14px;
}
.notfound {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin-top: 12px;
  padding: 10px;
  background: #fffbe8;
  border-radius: 8px;
}
.sad {
  width: 28px;
  height: 28px;
  flex: none;
}
.notfound-text {
  color: #646566;
  font-size: 12px;
  line-height: 1.5;
}
.toast-foot {
  flex: none;
  padding: 12px 16px;
  border-top: 1px solid #f2f3f5;
}
.skip-btn {
  margin-top: 10px;
}

/* —— rematch 副窗口 —— */
.sub-window {
  position: absolute;
  top: 49px;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.sub-panel {
  width: 100%;
  max-height: 100%;
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
}
.sub-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  font-size: 14px;
  font-weight: 600;
  border-bottom: 1px solid #f2f3f5;
}
.sub-body {
  padding: 12px 14px;
}
.sub-loading {
  display: block;
  margin: 20px auto;
}
.candidate {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  background: #f7f8fa;
  font-size: 14px;
}
.sub-empty {
  color: #969799;
  font-size: 13px;
  text-align: center;
  margin: 12px 0;
}
.sub-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

/* —— 替代方案对比 —— */
.scheme-card {
  width: 92%;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
}
.scheme-head {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid #f2f3f5;
}
.scheme-cols {
  display: flex;
  flex: none;
  background: #f7f8fa;
  font-size: 12px;
  color: #969799;
}
.col-label {
  flex: 1;
  padding: 6px 12px;
}
.col-label-left {
  border-right: 1px solid #ebedf0;
}
.scheme-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
}
.scheme-row {
  display: flex;
  border-bottom: 1px solid #f7f8fa;
  padding: 8px 0;
}
.scheme-left,
.scheme-right {
  flex: 1;
  min-width: 0;
  padding: 0 6px;
}
.scheme-left {
  border-right: 1px solid #f2f3f5;
}
.p-name {
  font-size: 14px;
  font-weight: 500;
}
.p-name-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
.state-text {
  color: #969799;
  font-size: 13px;
  margin-right: 6px;
}
.alt-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}
.scheme-foot {
  flex: none;
  padding: 12px 16px;
  border-top: 1px solid #f2f3f5;
}
.copy-btn {
  margin-top: 10px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
