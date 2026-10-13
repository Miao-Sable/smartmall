<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getPriceHistoryApi, getProductApi, type PricePoint, type Product } from '@/api/product'
import { getScanApi, type ScanRecord } from '@/api/scan'
import { createReviewApi, getProductReviewsApi, type Review } from '@/api/community'
import { formatTime, scoreLevel, trafficColor } from '@/utils'
import { analyzeLocal, isNetworkError, isOffline } from '@/utils/offline'
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

function isHit(ingredient: string) {
  return scan.value?.analysis?.allergen_hits.some((h) => h.ingredient === ingredient) ?? false
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

      <!-- 成分表（命中过敏源高亮） -->
      <van-cell-group inset title="成分表">
        <div class="ingredients">
          <span v-for="ing in product.ingredients" :key="ing" class="ingredient" :class="{ hit: isHit(ing) }">
            {{ ing }}
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
.ingredient {
  padding: 4px 10px;
  border-radius: 12px;
  background: #f2f3f5;
  font-size: 13px;
}
.ingredient.hit {
  background: #ffe1e1;
  color: #ee0a24;
  font-weight: 600;
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
