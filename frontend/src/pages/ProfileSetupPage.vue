<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getAllergensApi, getDietPreferencesApi, type Allergen, type DietPreference } from '@/api/meta'
import { getProfileApi, updateProfileApi } from '@/api/user'

const route = useRoute()
const router = useRouter()
// 从登录页进入（首次引导）时展示「跳过」；保存后据此决定去向
const isOnboarding = route.query.from === 'login'
const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'

// 昵称已移到「我的」页修改，这里仅用于保存时回传，避免被清空
const nickname = ref('')
const allergenIds = ref<number[]>([])
const dietIds = ref<number[]>([])
const allergens = ref<Allergen[]>([])
const diets = ref<DietPreference[]>([])
const loading = ref(true)
const saving = ref(false)

onMounted(async () => {
  try {
    const [allergenList, dietList, profile] = await Promise.all([
      getAllergensApi(),
      getDietPreferencesApi(),
      getProfileApi(),
    ])
    allergens.value = allergenList
    diets.value = dietList
    nickname.value = profile.nickname
    allergenIds.value = profile.allergen_ids
    dietIds.value = profile.diet_ids
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

async function onSkip() {
  // 跳过也要标记「已完成引导」：写入空档案（创建 profile 行），下次登录不再引导
  try {
    await updateProfileApi({})
  } catch {
    // 忽略失败，下次登录仍会引导
  }
  router.replace(redirect)
}

async function onSave() {
  saving.value = true
  try {
    await updateProfileApi({ nickname: nickname.value, allergen_ids: allergenIds.value, diet_ids: dietIds.value })
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
