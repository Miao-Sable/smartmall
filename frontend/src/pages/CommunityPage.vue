<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { showToast } from 'vant'
import { createReviewApi, getReviewsApi, type Review } from '@/api/community'
import { searchProductsApi, type ProductBrief } from '@/api/shopping-list'
import { formatTime } from '@/utils'

const reviews = ref<Review[]>([])
const loading = ref(true)
const showPost = ref(false)
const content = ref('')
const productName = ref('')
const tag = ref('')
const submitting = ref(false)
const candidates = ref<ProductBrief[]>([])
const selected = ref<ProductBrief | null>(null)
const matching = ref(false)
const searchedName = ref('')
let searchTimer: ReturnType<typeof setTimeout> | undefined

const TAG_OPTIONS = [
  { value: '', label: '无标签' },
  { value: 'recommend', label: '推荐' },
  { value: 'avoid', label: '避坑' },
]

const displayReviews = computed(() =>
  reviews.value.map((r) => ({
    ...r,
    time: formatTime(r.created_at),
    tag: r.tag === 'recommend'
      ? { label: '推荐', type: 'success' as const }
      : r.tag === 'avoid'
        ? { label: '避坑', type: 'danger' as const }
        : null,
  })),
)

async function loadReviews() {
  try {
    reviews.value = await getReviewsApi()
  } catch {
    // 拦截器已统一提示
  } finally {
    loading.value = false
  }
}

onMounted(loadReviews)

function openPost() {
  content.value = ''
  productName.value = ''
  tag.value = ''
  candidates.value = []
  selected.value = null
  searchedName.value = ''
  showPost.value = true
}

watch(productName, () => {
  const name = productName.value.trim()
  searchedName.value = ''
  candidates.value = []
  // 已选定该商品，输入不再触发搜索
  if (selected.value && selected.value.name === name) return
  selected.value = null
  if (searchTimer) clearTimeout(searchTimer)
  if (!name) return
  searchTimer = setTimeout(() => resolveProduct(name), 400)
})

async function resolveProduct(name: string) {
  matching.value = true
  try {
    const results = await searchProductsApi(name)
    if (productName.value.trim() === name) {
      candidates.value = results
      searchedName.value = name
    }
  } catch {
    if (productName.value.trim() === name) {
      candidates.value = []
      searchedName.value = name
    }
  } finally {
    matching.value = false
  }
}

function selectProduct(p: ProductBrief) {
  selected.value = p
  productName.value = p.name
  candidates.value = []
  searchedName.value = ''
}

function clearProduct() {
  selected.value = null
  productName.value = ''
  candidates.value = []
}

async function onSubmit() {
  const text = content.value.trim()
  if (!text) {
    showToast('请输入评价内容')
    return
  }
  const name = productName.value.trim()
  if (name && !selected.value) {
    showToast('请从候选列表选择商品，或清空商品名')
    return
  }
  if (submitting.value) return
  submitting.value = true
  try {
    await createReviewApi({
      content: text,
      product_name: selected.value?.name ?? '',
      tag: tag.value,
      barcode: selected.value?.barcode ?? '',
    })
    showToast({ message: '发布成功', type: 'success' })
    showPost.value = false
    await loadReviews()
  } catch {
    // 拦截器已统一提示
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page">
    <van-nav-bar title="社区" right-text="发评价" @click-right="openPost" />

    <van-loading v-if="loading" class="center" size="24" />
    <template v-else>
      <van-empty v-if="!reviews.length" description="还没有评价，来发第一条吧">
        <van-button round type="primary" @click="openPost">发评价</van-button>
      </van-empty>
      <div v-else class="feed">
        <div v-for="r in displayReviews" :key="r.id" class="review-card">
          <div class="review-head">
            <span class="review-author">{{ r.author_nickname || '匿名' }}</span>
            <span class="review-time">{{ r.time }}</span>
          </div>
          <div class="review-meta">
            <van-tag v-if="r.tag" :type="r.tag.type" class="review-tag">{{ r.tag.label }}</van-tag>
            <span v-if="r.product_name" class="review-product">{{ r.product_name }}</span>
          </div>
          <div class="review-content">{{ r.content }}</div>
        </div>
      </div>
    </template>

    <!-- 发评价弹层 -->
    <van-popup v-model:show="showPost" position="bottom" round class="post-popup">
      <div class="post-head">发评价</div>
      <div class="post-body">
        <van-field
          v-model="content"
          type="textarea"
          rows="3"
          autosize
          maxlength="200"
          show-word-limit
          placeholder="说说这个商品怎么样（含不含过敏源、值不值得买…）"
        />
        <van-field v-model="productName" placeholder="输入商品名，从候选列表选择" maxlength="30" />
        <div v-if="selected" class="match-hint">
          <span class="match-ok">已选择：{{ selected.name }}</span>
          <van-icon name="cross" class="match-clear" @click="clearProduct" />
        </div>
        <div v-else-if="productName.trim()" class="match-hint">
          <van-loading v-if="matching" size="14" class="match-loading" />
          <template v-else>
            <span v-if="searchedName && !candidates.length" class="match-none">暂无该商品，无法评价</span>
          </template>
        </div>
        <div v-if="!selected && candidates.length" class="candidate-list">
          <div v-for="c in candidates" :key="c.id" class="candidate-item" @click="selectProduct(c)">
            <span class="candidate-name">{{ c.name }}</span>
            <span class="candidate-cat">{{ c.category }}</span>
          </div>
        </div>
        <div class="tag-row">
          <span
            v-for="opt in TAG_OPTIONS"
            :key="opt.value"
            class="tag-chip"
            :class="{ active: tag === opt.value }"
            @click="tag = opt.value"
          >
            {{ opt.label }}
          </span>
        </div>
      </div>
      <div class="post-footer">
        <van-button block round plain @click="showPost = false">取消</van-button>
        <van-button block round type="primary" :loading="submitting" @click="onSubmit">发布</van-button>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.center {
  display: block;
  margin: 60px auto;
}
.feed {
  padding: 12px 16px calc(12px + var(--van-tabbar-height, 50px));
}
.review-card {
  background: #fff;
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 10px;
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
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 6px 0;
}
.review-tag {
  flex-shrink: 0;
}
.review-product {
  font-size: 13px;
  color: #646566;
}
.review-content {
  font-size: 14px;
  color: #323233;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.post-popup {
  padding: 16px;
}
.post-head {
  font-size: 16px;
  font-weight: 600;
  text-align: center;
  margin-bottom: 8px;
}
.post-body {
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
.post-footer {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}
.match-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 16px 12px;
  background: #fff;
  font-size: 13px;
}
.match-loading {
  vertical-align: middle;
}
.match-ok {
  color: #07c160;
}
.match-none {
  color: #ee0a24;
}
.match-clear {
  margin-left: auto;
  color: #969799;
  cursor: pointer;
}
.candidate-list {
  background: #fff;
  max-height: 220px;
  overflow-y: auto;
  padding: 0 16px 8px;
}
.candidate-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f2f3f5;
}
.candidate-item:last-child {
  border-bottom: none;
}
.candidate-name {
  font-size: 14px;
  color: #323233;
}
.candidate-cat {
  font-size: 12px;
  color: #969799;
}
</style>
