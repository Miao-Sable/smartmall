<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getScanHistoryApi, type ScanRecord } from '@/api/scan'
import { formatTime, trafficColor } from '@/utils'

const list = ref<ScanRecord[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    list.value = await getScanHistoryApi()
  } catch {
    // 拦截器已统一提示
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <van-nav-bar title="扫描历史" fixed placeholder left-arrow @click-left="$router.back()" />
    <van-loading v-if="loading" class="center" size="24" />
    <van-empty v-else-if="!list.length" description="还没有扫描记录，去扫一扫吧">
      <van-button round type="primary" to="/scan">去扫码</van-button>
    </van-empty>
    <van-cell-group v-else inset>
      <van-cell
        v-for="item in list"
        :key="item.id"
        :title="item.product_name || item.barcode"
        is-link
        :label="`条码 ${item.barcode} · ${formatTime(item.created_at)}`"
        :to="{ path: `/product/${item.barcode}`, query: { scan_id: item.id } }"
      >
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
  </div>
</template>

<style scoped>
.center {
  display: block;
  margin: 60px auto;
}
.history-score {
  margin-right: 8px;
  font-weight: 600;
}
</style>
