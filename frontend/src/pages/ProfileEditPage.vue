<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getAllergensApi, getDietPreferencesApi, type Allergen, type DietPreference } from '@/api/meta'
import { getProfilesApi, updateMemberProfileApi, type Profile } from '@/api/user'

const route = useRoute()
const router = useRouter()

const profileId = Number(route.params.id)

const name = ref('')
const allergenIds = ref<number[]>([])
const dietIds = ref<number[]>([])
const allergens = ref<Allergen[]>([])
const diets = ref<DietPreference[]>([])
const loading = ref(true)
const saving = ref(false)

onMounted(async () => {
  try {
    const [allergenList, dietList, profileList] = await Promise.all([
      getAllergensApi(),
      getDietPreferencesApi(),
      getProfilesApi(),
    ])
    allergens.value = allergenList
    diets.value = dietList
    const target = profileList.find((p: Profile) => p.id === profileId)
    if (!target) {
      showToast('档案不存在')
      router.replace('/profiles')
      return
    }
    name.value = target.name
    allergenIds.value = [...target.allergen_ids]
    dietIds.value = [...target.diet_ids]
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

async function onSave() {
  const nick = name.value.trim()
  if (!nick) {
    showToast('称呼不能为空')
    return
  }
  saving.value = true
  try {
    await updateMemberProfileApi(profileId, {
      name: nick,
      allergen_ids: allergenIds.value,
      diet_ids: dietIds.value,
    })
    showToast({ message: '保存成功', type: 'success' })
    router.back()
  } catch {
    // 拦截器已统一提示
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page">
    <van-nav-bar title="编辑档案" left-arrow @click-left="$router.back()" />
    <van-loading v-if="loading" class="center" size="24" />
    <template v-else>
      <van-cell-group inset title="基本信息">
        <van-field v-model="name" label="称呼" placeholder="如：我、宝宝、奶奶" maxlength="10" clearable />
      </van-cell-group>

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
</style>
