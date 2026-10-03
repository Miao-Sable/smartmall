<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { updateProfileApi } from '@/api/user'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()

const showNickname = ref(false)
const nicknameInput = ref('')

onMounted(() => {
  void userStore.fetchProfile()
})

function onEditNickname() {
  nicknameInput.value = userStore.profile?.nickname ?? ''
  showNickname.value = true
}

async function onSaveNickname() {
  const nick = nicknameInput.value.trim()
  if (!nick) {
    showToast('昵称不能为空')
    return
  }
  try {
    await updateProfileApi({
      nickname: nick,
      allergen_ids: userStore.profile?.allergen_ids ?? [],
      diet_ids: userStore.profile?.diet_ids ?? [],
    })
    await userStore.fetchProfile()
    showToast({ message: '修改成功', type: 'success' })
  } catch {
    // 拦截器已统一提示
  }
}

function onLogout() {
  userStore.logout()
  router.push('/')
}
</script>

<template>
  <div class="page">
    <van-nav-bar title="我的" />
    <template v-if="userStore.isLoggedIn">
      <van-cell-group inset title="账号">
        <van-cell title="邮箱" :value="userStore.profile?.email ?? '加载中…'" />
        <van-cell title="昵称" is-link :value="userStore.profile?.nickname || '未设置'" @click="onEditNickname" />
      </van-cell-group>
      <van-cell-group inset title="功能">
        <van-cell title="过敏源与饮食偏好" is-link to="/profile/setup" />
        <van-cell title="扫描历史" is-link to="/history" />
        <van-cell title="购物清单预检" is-link to="/shopping-list" />
      </van-cell-group>
      <van-cell-group inset title="关于">
        <van-cell title="隐私与免责声明" is-link to="/privacy" />
        <van-cell title="版本" value="v0.2 MVP" />
      </van-cell-group>
      <div class="logout-wrap">
        <van-button block type="danger" plain round @click="onLogout">退出登录</van-button>
      </div>
    </template>
    <van-empty v-else description="登录后可使用扫码、档案与历史功能">
      <van-button round type="primary" to="/login">去登录</van-button>
    </van-empty>
    <van-dialog v-model:show="showNickname" title="修改昵称" show-cancel-button @confirm="onSaveNickname">
      <van-field v-model="nicknameInput" placeholder="请输入昵称" maxlength="20" clearable />
    </van-dialog>
  </div>
</template>

<style scoped>
.logout-wrap {
  margin: 24px 16px;
}
</style>
