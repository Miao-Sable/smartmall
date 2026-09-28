<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getPriceHistoryApi, getProductApi, type PricePoint, type Product } from '@/api/product'
import { getScanApi, type ScanRecord } from '@/api/scan'
import { scoreLevel, trafficColor } from '@/utils'
import PriceTrendChart from '@/components/PriceTrendChart.vue'

const route = useRoute()
const barcode = route.params.barcode as string
const scanId = Number(route.query.scan_id ?? 0)

const product = ref<Product | null>(null)
const scan = ref<ScanRecord | null>(null)
const points = ref<PricePoint[]>([])
const loading = ref(true)

const hitNames = computed(() =>
  [...new Set((scan.value?.analysis?.allergen_hits ?? []).map((h) => h.allergen_name))].join('、'),
)

onMounted(async () => {
  try {
    product.value = await getProductApi(barcode)
    if (product.value) {
      const history = await getPriceHistoryApi(product.value.id)
      points.value = history.points
      if (scanId) scan.value = await getScanApi(scanId)
    }
  } catch {
    // 拦截器已统一提示
  } finally {
    loading.value = false
  }
})

function isHit(ingredient: string) {
  return scan.value?.analysis?.allergen_hits.some((h) => h.ingredient === ingredient) ?? false
}
</script>

<template>
  <div class="page">
    <van-nav-bar title="商品详情" left-arrow @click-left="$router.back()" />
    <van-loading v-if="loading" class="center" size="24" />
    <template v-else-if="product">
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

      <!-- 价格趋势（模拟数据） -->
      <van-cell-group inset title="历史价格趋势（模拟）">
        <div v-if="points.length" class="chart-wrap">
          <PriceTrendChart :points="points" :product-name="product.name" />
        </div>
        <van-empty v-else image="search" description="暂无价格数据" />
      </van-cell-group>

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
</style>
