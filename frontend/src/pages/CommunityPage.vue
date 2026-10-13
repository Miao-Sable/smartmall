<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { showToast } from 'vant'
import { createReviewApi, getReviewsApi, type Review } from '@/api/community'
import { formatTime } from '@/utils'

const reviews = ref<Review[]>([])
const loading = ref(true)
const showPost = ref(false)
const content = ref('')
const productName = ref('')
const tag = ref('')
const submitting = ref(false)

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
  showPost.value = true
}

async function onSubmit() {
  const text = content.value.trim()
  if (!text) {
    showToast('请输入评价内容')
    return
  }
  if (submitting.value) return
  submitting.value = true
  try {
    await createReviewApi({ content: text, product_name: productName.value.trim(), tag: tag.value })
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
        <van-field v-model="productName" placeholder="商品名（选填）" maxlength="30" />
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
</style>
