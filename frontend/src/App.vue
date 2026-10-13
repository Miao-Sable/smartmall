<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const showTabbar = computed(() => route.meta.tabbar === true)
</script>

<template>
  <router-view />
  <van-tabbar v-if="showTabbar" route placeholder>
    <van-tabbar-item replace to="/" icon="home-o">首页</van-tabbar-item>
    <van-tabbar-item replace to="/scan" icon="scan">扫码</van-tabbar-item>
    <van-tabbar-item replace to="/community" icon="friends-o">社区</van-tabbar-item>
    <van-tabbar-item replace to="/profile" icon="user-o">我的</van-tabbar-item>
  </van-tabbar>
</template>
