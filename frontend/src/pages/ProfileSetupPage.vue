<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getAllergensApi, getDietPreferencesApi, type Allergen, type DietPreference } from '@/api/meta'
import { getProfilesApi, updateMemberProfileApi, updateProfileApi, type Profile } from '@/api/user'

const route = useRoute()
const router = useRouter()
// 从登录页进入（首次引导）时展示「跳过」；保存后据此决定去向
const isOnboarding = route.query.from === 'login'
const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'

const allergenIds = ref<number[]>([])
const dietIds = ref<number[]>([])
const allergens = ref<Allergen[]>([])
const diets = ref<DietPreference[]>([])
const profiles = ref<Profile[]>([])
const loading = ref(true)
const saving = ref(false)

const defaultProfile = computed(() => profiles.value.find((p) => p.is_default) ?? profiles.value[0] ?? null)

onMounted(async () => {
  try {
    const [allergenList, dietList, profileList] = await Promise.all([
      getAllergensApi(),
      getDietPreferencesApi(),
      getProfilesApi(),
    ])
    allergens.value = allergenList
    diets.value = dietList
    profiles.value = profileList
    allergenIds.value = [...(defaultProfile.value?.allergen_ids ?? [])]
    dietIds.value = [...(defaultProfile.value?.diet_ids ?? [])]
  } catch {
    // 拦截器已统一提示
  } finally {
    loading.value = false
  }
})

function toggleIn(list: number[], id: number) {
  const i = list.indexOf(id)
  if (i >= 0) list.splice(i, 1)
  else list.push(id)
}

// 首次引导时：仅需创建账号档案行，把「已引导」标记下来；昵称到「我的」页再填
async function markOnboarded() {
  if (!isOnboarding) return
  try {
    await updateProfileApi({})
  } catch {
    // 忽略失败，下次登录仍会引导
  }
}

async function onSkip() {
  await markOnboarded()
  router.replace(redirect)
}

async function onSave() {
  const pid = defaultProfile.value?.id
  if (pid == null) {
    showToast('档案尚未就绪，请稍后重试')
    return
  }
  saving.value = true
  try {
    await updateMemberProfileApi(pid, { allergen_ids: allergenIds.value, diet_ids: dietIds.value })
    await markOnboarded()
    showToast({ message: '保存成功', type: 'success' })
    if (isOnboarding) router.replace(redirect)
  } catch {
    // 拦截器已统一提示
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page">
    <van-nav-bar title="档案设置" left-arrow @click-left="$router.back()" />
    <van-loading v-if="loading" class="center" size="24" />
    <template v-else>
      <van-cell-group inset title="过敏源（选择后扫码将自动提醒）">
        <van-checkbox-group v-model="allergenIds">
          <van-cell
            v-for="a in allergens"
            :key="a.id"
            clickable
            :title="a.name"
            :label="a.description || a.keywords.join('、')"
            @click="toggleIn(allergenIds, a.id)"
          >
            <template #right-icon>
              <van-checkbox :name="a.id" @click.stop />
            </template>
          </van-cell>
        </van-checkbox-group>
      </van-cell-group>

      <van-cell-group inset title="饮食偏好">
        <van-checkbox-group v-model="dietIds">
          <van-cell
            v-for="d in diets"
            :key="d.id"
            clickable
            :title="d.name"
            :label="d.description || d.keywords.join('、')"
            @click="toggleIn(dietIds, d.id)"
          >
            <template #right-icon>
              <van-checkbox :name="d.id" @click.stop />
            </template>
          </van-cell>
        </van-checkbox-group>
      </van-cell-group>

      <div class="save-wrap">
        <van-button block round type="primary" :loading="saving" @click="onSave">保存</van-button>
        <van-button v-if="isOnboarding" block round plain type="primary" class="skip" @click="onSkip">跳过，稍后填写</van-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.center {
  display: block;
  margin: 60px auto;
}
.save-wrap {
  margin: 24px 16px;
}
.skip {
  margin-top: 12px;
}
</style>
