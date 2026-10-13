<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { createProfileApi, deleteMemberProfileApi, type Profile } from '@/api/user'
import { getScenariosApi, type Scenario } from '@/api/meta'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const scenarios = ref<Scenario[]>([])
const showAddSheet = ref(false)
const showNameDialog = ref(false)
const pendingScenario = ref<Scenario | null>(null)
const newName = ref('')

onMounted(async () => {
  try {
    await userStore.fetchProfiles()
    scenarios.value = await getScenariosApi()
  } catch {
    // 拦截器已统一提示
  }
})

const scenarioActions = computed(() => [
  { name: '自定义（空白）', subname: '不套用模板，稍后手动填写过敏源与偏好', scenario: null },
  ...scenarios.value.map((s) => ({
    name: `${s.emoji} ${s.name}`,
    subname: s.description,
    scenario: s,
  })),
])

function onTapProfile(p: Profile) {
  userStore.setActiveProfile(p.id)
  showToast({ message: `已切换为「${p.name}」`, type: 'success' })
}

function onEdit(p: Profile) {
  router.push(`/profiles/${p.id}/edit`)
}

async function onDelete(p: Profile) {
  try {
    await showConfirmDialog({ title: '删除成员', message: `确定删除「${p.name}」的档案吗？删除后不可恢复。` })
  } catch {
    return // 用户取消
  }
  try {
    await deleteMemberProfileApi(p.id)
    await userStore.fetchProfiles()
    showToast({ message: '已删除', type: 'success' })
  } catch {
    // 拦截器已统一提示
  }
}

function onSelectScenario(action: { name: string; subname?: string; scenario: Scenario | null }) {
  pendingScenario.value = action.scenario
  newName.value = action.scenario ? action.scenario.name : ''
  showAddSheet.value = false
  showNameDialog.value = true
}

async function onConfirmCreate() {
  const name = newName.value.trim() || pendingScenario.value?.name || '新成员'
  try {
    await createProfileApi(
      pendingScenario.value
        ? {
            name,
            emoji: pendingScenario.value.emoji,
            scenario: pendingScenario.value.key,
            allergen_ids: pendingScenario.value.allergen_ids,
            diet_ids: pendingScenario.value.diet_ids,
          }
        : { name, emoji: '👤', allergen_ids: [], diet_ids: [] },
    )
    await userStore.fetchProfiles()
    showToast({ message: '已新增成员', type: 'success' })
  } catch {
    // 拦截器已统一提示
  }
}
</script>

<template>
  <div class="page">
    <van-nav-bar title="家庭成员" left-arrow @click-left="$router.back()" />

    <van-cell-group inset title="点击切换当前档案">
      <van-cell v-for="p in userStore.profiles" :key="p.id" clickable @click="onTapProfile(p)">
        <template #title>
          <span class="profile-title">{{ p.emoji || '👤' }} {{ p.name }}</span>
        </template>
        <template #label>
          <span v-if="p.is_default">默认档案</span>
        </template>
        <template #right-icon>
          <van-tag v-if="p.id === userStore.activeProfile?.id" type="success">当前</van-tag>
        </template>
      </van-cell>
      <van-empty v-if="!userStore.profiles.length" description="还没有档案，点击下方新增" />
    </van-cell-group>

    <van-cell-group inset title="管理">
      <van-cell v-for="p in userStore.profiles" :key="`manage-${p.id}`" :title="`${p.emoji || '👤'} ${p.name}`">
        <template #right-icon>
          <div class="manage-actions">
            <van-button size="mini" plain @click="onEdit(p)">编辑</van-button>
            <van-button v-if="!p.is_default" size="mini" plain type="danger" @click="onDelete(p)">删除</van-button>
          </div>
        </template>
      </van-cell>
    </van-cell-group>

    <div class="add-wrap">
      <van-button block round type="primary" @click="showAddSheet = true">+ 新增成员</van-button>
    </div>

    <van-action-sheet
      v-model:show="showAddSheet"
      title="选择场景模板"
      :actions="scenarioActions"
      cancel-text="取消"
      @select="onSelectScenario"
    />

    <van-dialog
      v-model:show="showNameDialog"
      title="成员称呼"
      show-cancel-button
      @confirm="onConfirmCreate"
    >
      <van-field v-model="newName" placeholder="如：宝宝、奶奶" maxlength="10" clearable />
    </van-dialog>
  </div>
</template>

<style scoped>
.profile-title {
  font-weight: 500;
}
.manage-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.add-wrap {
  margin: 24px 16px;
}
</style>
