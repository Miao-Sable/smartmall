<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getPriceHistoryApi, getProductApi, type PricePoint, type Product } from '@/api/product'
import { getScanApi, type ScanRecord } from '@/api/scan'
import { createReviewApi, getProductReviewsApi, type Review } from '@/api/community'
import { formatTime, scoreLevel, trafficColor } from '@/utils'
import { analyzeLocal, isNetworkError, isOffline } from '@/utils/offline'
import { explainIngredient, searchIngredients, type IngredientExplanation } from '@/utils/ingredientExplain'
import { useUserStore } from '@/stores/user'
import PriceTrendChart from '@/components/PriceTrendChart.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const barcode = route.params.barcode as string
const scanId = Number(route.query.scan_id ?? 0)

const product = ref<Product | null>(null)
const scan = ref<ScanRecord | null>(null)
const points = ref<PricePoint[]>([])
const loading = ref(true)
const offlineMode = ref(false)

const hitNames = computed(() =>
  [...new Set((scan.value?.analysis?.allergen_hits ?? []).map((h) => h.allergen_name))].join('、'),
)

// ---- 用户评价 ----
const TAG_OPTIONS = [
  { value: '', label: '无标签' },
  { value: 'recommend', label: '推荐' },
  { value: 'avoid', label: '避坑' },
]
const reviews = ref<Review[]>([])
const reviewsLoaded = ref(false)
const showReview = ref(false)
const reviewContent = ref('')
const reviewTag = ref('')
const submitting = ref(false)

async function loadReviews() {
  if (!userStore.isLoggedIn || isOffline()) {
    reviewsLoaded.value = true
    return
  }
  try {
    reviews.value = await getProductReviewsApi(barcode)
  } catch {
    // 未登录/网络异常由拦截器提示，此处静默
  } finally {
    reviewsLoaded.value = true
  }
}

function openReview() {
  if (isOffline()) {
    showToast('离线状态下无法发布评价')
    return
  }
  if (!userStore.isLoggedIn) {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  reviewContent.value = ''
  reviewTag.value = ''
  showReview.value = true
}

async function submitReview() {
  const text = reviewContent.value.trim()
  if (!text) {
    showToast('请输入评价内容')
    return
  }
  if (submitting.value) return
  submitting.value = true
  try {
    await createReviewApi({
      content: text,
      product_name: product.value?.name ?? '',
      tag: reviewTag.value,
      barcode,
    })
    showToast({ message: '发布成功', type: 'success' })
    showReview.value = false
    await loadReviews()
  } catch {
    // 拦截器已统一提示
  } finally {
    submitting.value = false
  }
}

function tagLabel(tag: string) {
  return tag === 'recommend' ? '推荐' : tag === 'avoid' ? '避坑' : ''
}

function tagType(tag: string): 'success' | 'danger' {
  return tag === 'recommend' ? 'success' : 'danger'
}

onMounted(async () => {
  void loadReviews()
  try {
    if (route.query.offline === '1' || isOffline()) {
      loadOffline()
      return
    }
    try {
      product.value = await getProductApi(barcode)
      if (product.value) {
        const history = await getPriceHistoryApi(product.value.id)
        points.value = history.points
        if (scanId) scan.value = await getScanApi(scanId)
      }
    } catch (err) {
      // 断网/超时 → 本地降级；商品不存在等业务错误由拦截器提示
      if (isNetworkError(err)) loadOffline()
    }
  } finally {
    loading.value = false
  }
})

function loadOffline() {
  const result = analyzeLocal(barcode, userStore.activeProfile)
  if (!result) {
    showToast('暂无该商品数据')
    return
  }
  product.value = result.product
  points.value = result.pricePoints
  scan.value = result.scan
  offlineMode.value = true
}

// ---- 成分白话翻译 ----
const LEVEL_LABELS: Record<string, string> = { high: '高风险', medium: '中风险', low: '安全', none: '未知' }

const searchText = ref('')
const searchResults = computed(() => (searchText.value.trim() ? searchIngredients(searchText.value.trim()) : []))
const activeIngredient = ref<IngredientExplanation | null>(null)
const showIngredient = ref(false)

const ingredientItems = computed(() =>
  (product.value?.ingredients ?? []).map((ing) => explainIngredient(ing, userStore.activeProfile)),
)

function openIngredient(name: string) {
  activeIngredient.value = explainIngredient(name, userStore.activeProfile)
  showIngredient.value = true
}

function levelClass(level: string) {
  return `lvl-${level}`
}

function levelLabel(level: string) {
  return LEVEL_LABELS[level] ?? '未知'
}
</script>

<template>
  <div class="page">
    <van-nav-bar title="商品详情" left-arrow @click-left="$router.back()" />
    <van-loading v-if="loading" class="center" size="24" />
    <template v-else-if="product">
      <van-notice-bar
        v-if="offlineMode"
        color="#1989fa"
        background="#ecf5ff"
        wrapable
        text="离线安全模式 · 本次结果来自本地，未保存到扫描历史"
      />
      <!-- 基本信息 -->
      <div class="product-card">
        <van-image :src="product.image_url" width="72" height="72" radius="8" class="product-img">
          <template #error>
            <van-icon name="photo-o" size="36" />
          </template>
        </van-image>
        <div class="product-info">
          <div class="product-name">{{ product.name }}</div>
          <div class="product-brand">{{ product.brand }} · {{ product.category }}</div>
          <van-tag v-for="t in product.tags" :key="t" plain type="primary" class="tag">{{ t }}</van-tag>
        </div>
      </div>

      <!-- 分析结果 -->
      <van-cell-group inset title="分析结果">
        <van-cell v-if="scan?.analysis">
          <template #title>
            <div class="result-head">
              <span class="traffic-dot" :style="{ background: trafficColor(scan.analysis.traffic_light) }" />
              <span class="traffic-label" :style="{ color: trafficColor(scan.analysis.traffic_light) }">
                {{ scan.analysis.traffic_label }}
              </span>
              <span class="score" :style="{ color: scoreLevel(scan.analysis.score).color }">
                {{ scan.analysis.score }} 分 · {{ scan.analysis.level }}
              </span>
            </div>
          </template>
        </van-cell>
        <van-cell v-else title="暂无分析结果">
          <template #label>扫码后即可看到匹配度评分与过敏提醒</template>
        </van-cell>
      </van-cell-group>

      <!-- 评分明细（可解释加减分） -->
      <van-cell-group v-if="scan?.analysis?.reasons.length" inset title="评分明细">
        <van-cell v-for="(r, i) in scan.analysis.reasons" :key="i" :title="r.label">
          <template #value>
            <span class="delta" :class="r.delta >= 0 ? 'delta-plus' : 'delta-minus'">
              {{ r.delta >= 0 ? '+' : '' }}{{ r.delta }}
            </span>
          </template>
        </van-cell>
      </van-cell-group>

      <!-- 过敏提醒 -->
      <van-cell-group v-if="scan" inset title="过敏提醒">
        <van-notice-bar
          v-if="scan.has_allergen"
          color="#ee0a24"
          background="#fff1f0"
          wrapable
          :text="`⚠ 检测到过敏源：${hitNames}`"
        />
        <van-notice-bar v-else color="#07c160" background="#f0fff4" wrapable
          text="未发现已知过敏源（分析仅供参考，请以包装说明为准）" />
      </van-cell-group>

      <!-- 成分白话翻译 -->
      <van-cell-group inset title="成分白话翻译">
        <div class="ing-search">
          <van-search v-model="searchText" placeholder="搜索成分，如「小苏打 / 苯甲酸钠 / E211」" />
        </div>
        <div v-if="searchResults.length" class="search-results">
          <div v-for="e in searchResults" :key="e.name" class="search-item" @click="openIngredient(e.name)">
            <span class="search-name">{{ e.plain_name }}</span>
            <span class="search-cat">{{ e.category }}</span>
          </div>
        </div>
        <div class="ingredients">
          <span
            v-for="it in ingredientItems"
            :key="it.ingredient"
            class="ingredient"
            :class="levelClass(it.level)"
            @click="openIngredient(it.ingredient)"
          >
            {{ it.ingredient }}
          </span>
        </div>
      </van-cell-group>

      <!-- 营养成分 -->
      <van-cell-group inset title="营养成分">
        <van-cell v-for="n in product.nutrition" :key="n.name" :title="n.name" :value="`${n.value} ${n.unit}`" />
      </van-cell-group>

      <!-- 用户评价 -->
      <van-cell-group inset title="用户评价">
        <div class="reviews">
          <template v-if="reviews.length">
            <div v-for="r in reviews" :key="r.id" class="review-card">
              <div class="review-head">
                <span class="review-author">{{ r.author_nickname || '匿名' }}</span>
                <span class="review-time">{{ formatTime(r.created_at) }}</span>
              </div>
              <div class="review-meta">
                <van-tag v-if="tagLabel(r.tag)" :type="tagType(r.tag)" class="review-tag">
                  {{ tagLabel(r.tag) }}
                </van-tag>
              </div>
              <div class="review-content">{{ r.content }}</div>
            </div>
          </template>
          <van-empty v-else-if="reviewsLoaded" description="暂无评价，来写第一条" />
          <van-button block round plain class="review-btn" @click="openReview">写评价</van-button>
        </div>
      </van-cell-group>

      <!-- 价格趋势（模拟数据） -->
      <van-cell-group inset title="历史价格趋势（模拟）">
        <div v-if="points.length" class="chart-wrap">
          <PriceTrendChart :points="points" :product-name="product.name" />
        </div>
        <van-empty v-else image="search" description="暂无价格数据" />
      </van-cell-group>

      <!-- 写评价弹层 -->
      <van-popup v-model:show="showReview" position="bottom" round class="review-popup">
        <div class="rv-head">评价「{{ product.name }}」</div>
        <div class="rv-body">
          <van-field
            v-model="reviewContent"
            type="textarea"
            rows="3"
            autosize
            maxlength="200"
            show-word-limit
            placeholder="说说这款商品怎么样，值不值得买…"
          />
          <div class="tag-row">
            <span
              v-for="opt in TAG_OPTIONS"
              :key="opt.value"
              class="tag-chip"
              :class="{ active: reviewTag === opt.value }"
              @click="reviewTag = opt.value"
            >
              {{ opt.label }}
            </span>
          </div>
        </div>
        <div class="rv-footer">
          <van-button block round plain @click="showReview = false">取消</van-button>
          <van-button block round type="primary" :loading="submitting" @click="submitReview">发布</van-button>
        </div>
      <!-- 成分解释弹层 -->
      <van-popup v-model:show="showIngredient" position="bottom" round class="ing-popup">
        <template v-if="activeIngredient">
          <div class="ing-head">
            <div class="ing-title">
              {{ activeIngredient.entry?.plain_name || activeIngredient.ingredient }}
            </div>
            <div
              v-if="activeIngredient.entry && activeIngredient.entry.plain_name !== activeIngredient.ingredient"
              class="ing-origin"
            >
              原配料名：{{ activeIngredient.ingredient }}
            </div>
            <span class="ing-level-badge" :class="levelClass(activeIngredient.level)">
              {{ levelLabel(activeIngredient.level) }}
            </span>
          </div>
          <div class="ing-body">
            <template v-if="activeIngredient.entry">
              <div class="ing-row">
                <span class="ing-k">类别</span>
                <span class="ing-v">{{ activeIngredient.entry.category }}</span>
              </div>
              <div class="ing-row">
                <span class="ing-k">作用</span>
                <span class="ing-v">{{ activeIngredient.entry.function }}</span>
              </div>
              <div class="ing-row">
                <span class="ing-k">风险</span>
                <span class="ing-v">{{ activeIngredient.entry.risk }}</span>
              </div>
              <div v-if="activeIngredient.entry.e_numbers.length" class="ing-row">
                <span class="ing-k">E 编号</span>
                <span class="ing-v">{{ activeIngredient.entry.e_numbers.join('、') }}</span>
              </div>
              <div v-if="activeIngredient.entry.crowd_hints.length" class="ing-row">
                <span class="ing-k">人群提示</span>
                <span class="ing-v">{{ activeIngredient.entry.crowd_hints.join('、') }}</span>
              </div>
            </template>
            <div v-else class="ing-empty">暂未收录该成分的白话解释，属常见食材或未收录成分。</div>
          </div>
          <div v-if="activeIngredient.reasons.length" class="ing-reasons">
            <div v-for="(r, i) in activeIngredient.reasons" :key="i" class="reason" :class="levelClass(r.level)">
              {{ r.label }}
            </div>
          </div>
        </template>
      </van-popup>

      <p class="disclaimer">
        本应用提供的过敏提醒和成分分析仅供参考，不构成医疗建议。请以商品包装说明和医生意见为准。
      </p>
    </template>
    <van-empty v-else image="search" description="暂无该商品数据">
      <van-button round type="primary" to="/scan">去扫码 / 手动输入</van-button>
    </van-empty>
  </div>
</template>

<style scoped>
.center {
  display: block;
  margin: 60px auto;
}
.product-card {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 16px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
}
.product-name {
  font-size: 16px;
  font-weight: 600;
}
.product-brand {
  margin: 4px 0;
  color: #969799;
  font-size: 13px;
}
.tag {
  margin-right: 4px;
}
.score {
  font-size: 16px;
  font-weight: 600;
}
.result-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.traffic-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}
.traffic-label {
  font-size: 16px;
  font-weight: 600;
}
.delta {
  font-weight: 600;
  font-size: 15px;
}
.delta-plus {
  color: #07c160;
}
.delta-minus {
  color: #ee0a24;
}
.ingredients {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
}
.ing-search {
  padding: 0 8px;
}
.ing-search :deep(.van-search) {
  padding: 8px 0;
  background: transparent;
}
.search-results {
  padding: 4px 16px 8px;
}
.search-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f2f3f5;
}
.search-name {
  font-size: 14px;
  color: #323233;
}
.search-cat {
  font-size: 12px;
  color: #969799;
}
.ingredients {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
}
.ingredient {
  padding: 4px 10px;
  border-radius: 12px;
  background: #f2f3f5;
  font-size: 13px;
}
.ingredient.lvl-high {
  background: #fff1f0;
  color: #ee0a24;
  font-weight: 600;
}
.ingredient.lvl-medium {
  background: #fff7e6;
  color: #ed6a0c;
  font-weight: 600;
}
.ingredient.lvl-low {
  background: #f0fff4;
  color: #07c160;
}
.ingredient.lvl-none {
  background: #f2f3f5;
  color: #646566;
}
.ing-popup {
  padding: 20px 16px;
  max-height: 70vh;
  overflow-y: auto;
}
.ing-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.ing-title {
  font-size: 18px;
  font-weight: 600;
  color: #323233;
}
.ing-origin {
  font-size: 12px;
  color: #969799;
  width: 100%;
}
.ing-level-badge {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
}
.ing-level-badge.lvl-high {
  background: #fff1f0;
  color: #ee0a24;
}
.ing-level-badge.lvl-medium {
  background: #fff7e6;
  color: #ed6a0c;
}
.ing-level-badge.lvl-low {
  background: #f0fff4;
  color: #07c160;
}
.ing-level-badge.lvl-none {
  background: #f2f3f5;
  color: #969799;
}
.ing-body {
  background: #f7f8fa;
  border-radius: 8px;
  padding: 4px 12px;
}
.ing-row {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #ebedf0;
}
.ing-row:last-child {
  border-bottom: none;
}
.ing-k {
  flex-shrink: 0;
  width: 56px;
  color: #969799;
  font-size: 13px;
}
.ing-v {
  color: #323233;
  font-size: 13px;
  line-height: 1.5;
}
.ing-empty {
  padding: 12px;
  color: #969799;
  font-size: 13px;
}
.ing-reasons {
  margin-top: 12px;
}
.reason {
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 6px;
}
.reason.lvl-high {
  background: #fff1f0;
  color: #ee0a24;
}
.reason.lvl-medium {
  background: #fff7e6;
  color: #ed6a0c;
}
.chart-wrap {
  padding: 12px;
}
.disclaimer {
  padding: 12px 24px;
  color: #969799;
  font-size: 12px;
  line-height: 1.6;
}
.reviews {
  padding: 12px 16px;
}
.review-card {
  background: #fff;
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 10px;
  border: 1px solid #f2f3f5;
}
.review-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.review-author {
  font-size: 14px;
  font-weight: 600;
  color: #323233;
}
.review-time {
  font-size: 12px;
  color: #969799;
}
.review-meta {
  margin: 6px 0;
}
.review-tag {
  margin-right: 8px;
}
.review-content {
  font-size: 14px;
  color: #323233;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.review-btn {
  margin-top: 4px;
}
.review-popup {
  padding: 16px;
}
.rv-head {
  font-size: 16px;
  font-weight: 600;
  text-align: center;
  margin-bottom: 8px;
}
.rv-body {
  background: #f7f8fa;
  border-radius: 8px;
  overflow: hidden;
}
.tag-row {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  background: #fff;
}
.tag-chip {
  flex: 1;
  text-align: center;
  padding: 8px 0;
  border-radius: 16px;
  background: #f2f3f5;
  color: #646566;
  font-size: 13px;
}
.tag-chip.active {
  background: #ecf5ff;
  color: #1989fa;
  font-weight: 600;
}
.rv-footer {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}
</style>
