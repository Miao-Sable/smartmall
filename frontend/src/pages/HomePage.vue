<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getStatsApi, type StatsOverview } from '@/api/stats'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const stats = ref<StatsOverview | null>(null)
// null = 全部档案；否则按该 profile_id 统计
const filterProfileId = ref<number | null>(null)

async function loadStats() {
  try {
    stats.value = await getStatsApi(filterProfileId.value)
  } catch {
    // 拦截器已统一提示
  }
}

function onSelectFilter(id: number | null) {
  if (filterProfileId.value === id) return
  filterProfileId.value = id
  void loadStats()
}

onMounted(async () => {
  if (!userStore.isLoggedIn) return
  void userStore.fetchProfiles()
  await loadStats()
})
</script>

<template>
  <div class="page">
    <van-nav-bar title="智慧购物" />
    <template v-if="userStore.isLoggedIn && stats">
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

      <!-- 核心统计（TODO：后续用 ECharts 展示近 7 天扫描趋势） -->
      <van-grid :column-num="2" :border="false" class="stats-grid">
        <van-grid-item icon="scan" :text="`${stats.total_scans} 次累计扫描`" />
        <van-grid-item icon="warning-o" :text="`${stats.allergen_alerts} 次过敏警报`" />
        <van-grid-item icon="fire-o" :text="`${stats.today_scans} 次今日扫描`" />
        <van-grid-item icon="chart-trending-o" :text="`${stats.avg_score} 平均匹配分`" />
      </van-grid>
      <div class="quick-actions">
        <van-button type="primary" block round to="/scan">去扫码</van-button>
      </div>
    </template>
    <van-empty v-else description="登录后可查看个人扫描统计与过敏警报">
      <van-button round type="primary" to="/login">去登录 / 注册</van-button>
    </van-empty>
  </div>
</template>

<style scoped>
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
.stats-grid {
  margin-top: 4px;
}
.quick-actions {
  margin: 16px;
}
</style>
