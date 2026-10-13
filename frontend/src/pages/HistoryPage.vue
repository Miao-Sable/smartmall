<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getScanHistoryApi, type ScanRecord } from '@/api/scan'
import { useUserStore } from '@/stores/user'
import { formatTime, trafficColor } from '@/utils'

const userStore = useUserStore()

const list = ref<ScanRecord[]>([])
const loading = ref(true)
// null = 全部档案；否则按该 profile_id 过滤
const filterProfileId = ref<number | null>(null)

onMounted(async () => {
  try {
    void userStore.fetchProfiles()
    list.value = await getScanHistoryApi()
  } catch {
    // 拦截器已统一提示
  } finally {
    loading.value = false
  }
})

const filteredList = computed(() =>
  filterProfileId.value == null
    ? list.value
    : list.value.filter((i) => i.profile_id === filterProfileId.value),
)

// 优先用当前档案列表还原 emoji；档案已被删除时回退到后端返回的 profile_name
function profileLabel(item: ScanRecord): string {
  const p = userStore.profiles.find((x) => x.id === item.profile_id)
  if (p) return `${p.emoji || '👤'} ${p.name}`
  return item.profile_name || ''
}
</script>

<template>
  <div class="page">
    <van-nav-bar title="扫描历史" fixed placeholder left-arrow @click-left="$router.back()" />

    <van-loading v-if="loading" class="center" size="24" />
    <template v-else>
      <van-empty v-if="!list.length" description="还没有扫描记录，去扫一扫吧">
        <van-button round type="primary" to="/scan">去扫码</van-button>
      </van-empty>
      <template v-else>
        <!-- 按档案筛选 -->
        <div class="filter-bar">
          <span class="filter-chip" :class="{ active: filterProfileId === null }" @click="filterProfileId = null">全部</span>
          <span
            v-for="p in userStore.profiles"
            :key="p.id"
            class="filter-chip"
            :class="{ active: filterProfileId === p.id }"
            @click="filterProfileId = p.id"
          >
            {{ p.emoji || '👤' }} {{ p.name }}
          </span>
        </div>

        <van-cell-group v-if="filteredList.length" inset>
          <van-cell
            v-for="item in filteredList"
            :key="item.id"
            :title="item.product_name || item.barcode"
            is-link
            :to="{ path: `/product/${item.barcode}`, query: { scan_id: item.id } }"
          >
            <template #label>
              <span v-if="profileLabel(item)" class="profile-tag">{{ profileLabel(item) }}</span>
              <span>条码 {{ item.barcode }} · {{ formatTime(item.created_at) }}</span>
            </template>
            <template #value>
              <span class="history-score" :style="{ color: trafficColor(item.analysis?.traffic_light) }">
                {{ item.score }} 分
              </span>
              <van-tag :type="item.has_allergen ? 'danger' : 'success'" plain>
                {{ item.has_allergen ? '含过敏源' : '安全' }}
              </van-tag>
            </template>
          </van-cell>
        </van-cell-group>
        <van-empty v-else description="该档案下暂无扫描记录" />
      </template>
    </template>
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
.profile-tag {
  display: inline-block;
  margin-right: 6px;
  padding: 0 6px;
  border-radius: 4px;
  background: #e8f3ff;
  color: #1989fa;
  font-size: 12px;
}
.history-score {
  margin-right: 8px;
  font-weight: 600;
}
</style>
