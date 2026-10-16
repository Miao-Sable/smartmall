<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getWeeklyReportApi, type WeeklyReport } from '@/api/stats'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const report = ref<WeeklyReport | null>(null)
const loading = ref(true)
// null = 全部档案；否则按该 profile_id 统计
const filterProfileId = ref<number | null>(null)

async function loadReport() {
  loading.value = true
  try {
    report.value = await getWeeklyReportApi(filterProfileId.value)
  } catch {
    // 拦截器已统一提示
  } finally {
    loading.value = false
  }
}

function onSelectFilter(id: number | null) {
  if (filterProfileId.value === id) return
  filterProfileId.value = id
  void loadReport()
}

onMounted(async () => {
  if (!userStore.isLoggedIn) {
    loading.value = false
    return
  }
  void userStore.fetchProfiles()
  await loadReport()
})
</script>

<template>
  <div class="page">
    <van-nav-bar title="健康周报" left-arrow @click-left="$router.back()" />
    <van-loading v-if="loading" class="center" size="24" />
    <template v-else-if="userStore.isLoggedIn && report">
      <!-- 按档案筛选 -->
      <div class="filter-bar">
        <span class="filter-chip" :class="{ active: filterProfileId === null }" @click="onSelectFilter(null)">全部</span>
        <span
          v-for="p in userStore.profiles"
          :key="p.id"
          class="filter-chip"
          :class="{ active: filterProfileId === p.id }"
          @click="onSelectFilter(p.id)"
        >
          {{ p.emoji || '👤' }} {{ p.name }}
        </span>
      </div>

      <div class="period">统计周期：{{ report.period_start }} ~ {{ report.period_end }}</div>

      <!-- 核心指标 -->
      <van-grid :column-num="2" :border="false" class="stats-grid">
        <van-grid-item icon="scan" :text="`${report.total_scans} 次本周扫描`" />
        <van-grid-item icon="warning-o" :text="`${report.allergen_avoided} 次过敏提醒`" />
        <van-grid-item icon="chart-trending-o" :text="`${report.avg_score} 平均匹配分`" />
        <van-grid-item icon="clock-o" :text="report.score_trend || '暂无趋势'" />
      </van-grid>

      <!-- 商品品类趋势 -->
      <van-cell-group inset title="商品品类趋势（Top 5）">
        <van-empty v-if="!report.category_trends.length" image="search" description="本周暂无扫描记录" />
        <van-cell v-for="c in report.category_trends" :key="c.category" :title="c.category">
          <template #label>
            <van-progress :percentage="c.percentage" :show-pivot="false" stroke-width="6" />
          </template>
          <template #value>
            <span class="trend-value">{{ c.count }} 次 · {{ c.percentage }}%</span>
          </template>
        </van-cell>
      </van-cell-group>

      <!-- 高频扫描商品 -->
      <van-cell-group v-if="report.top_products.length" inset title="高频扫描商品（Top 5）">
        <van-cell v-for="(name, i) in report.top_products" :key="name" :title="name">
          <template #value>第 {{ i + 1 }} 位</template>
        </van-cell>
      </van-cell-group>

      <!-- 营养警示 -->
      <van-cell-group inset title="营养警示（本周命中次数）">
        <van-cell title="高糖（碳水 ≥ 60g/100g）" :value="`${report.nutrition_summary.high_sugar_count} 次`" />
        <van-cell title="高钠（钠 ≥ 600mg/100g）" :value="`${report.nutrition_summary.high_sodium_count} 次`" />
        <van-cell title="高脂（脂肪 ≥ 20g/100g）" :value="`${report.nutrition_summary.high_fat_count} 次`" />
      </van-cell-group>
    </template>
    <van-empty v-else description="登录后可查看本周健康周报">
      <van-button round type="primary" to="/login">去登录</van-button>
    </van-empty>
  </div>
</template>

<style scoped>
.center {
  display: block;
  margin: 60px auto;
}
.filter-bar {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 12px 16px;
  white-space: nowrap;
}
.filter-chip {
  flex: none;
  padding: 6px 14px;
  border-radius: 16px;
  background: #f7f8fa;
  color: #646566;
  font-size: 13px;
  cursor: pointer;
}
.filter-chip.active {
  background: #1989fa;
  color: #fff;
}
.period {
  padding: 0 20px 12px;
  color: #969799;
  font-size: 12px;
}
.stats-grid {
  margin-top: 4px;
}
.trend-value {
  color: #969799;
  font-size: 12px;
}
</style>
