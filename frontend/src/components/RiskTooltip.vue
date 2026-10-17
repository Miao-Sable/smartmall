<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 气泡内容；为空时不显示 */
    text: string
    /** 仅桌面 hover 触发；点击不拦截、继续冒泡给父级（用于成分点开详情等） */
    hoverOnly?: boolean
  }>(),
  { hoverOnly: false },
)

// 是否支持 hover：桌面端用鼠标悬浮，移动端用点击
const canHover = typeof window !== 'undefined' && window.matchMedia('(hover: hover)').matches

const show = ref(false)
const triggerEl = ref<HTMLElement | null>(null)
const placement = ref<'top' | 'bottom'>('top')
const style = ref({ left: '0px', top: '0px' })
let hideTimer: ReturnType<typeof setTimeout> | null = null

function clearTimer() {
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
}

function open() {
  clearTimer()
  const el = triggerEl.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const half = 120 // 气泡最大宽度 240 的一半，用于水平方向收敛
  const centerX = rect.left + rect.width / 2
  const left = Math.max(half + 8, Math.min(window.innerWidth - half - 8, centerX))
  const above = rect.top - 8
  placement.value = above < 64 ? 'bottom' : 'top'
  style.value = {
    left: `${left}px`,
    top: placement.value === 'top' ? `${above}px` : `${rect.bottom + 8}px`,
  }
  show.value = true
}

function close() {
  clearTimer()
  show.value = false
}

function onEnter() {
  if (canHover) open()
}

function onLeave() {
  if (canHover) close()
}

function onClick(e: MouseEvent) {
  if (props.hoverOnly || canHover) return // 点击透传 / 桌面端用 hover 触发
  e.stopPropagation()
  if (show.value) {
    close()
  } else {
    open()
    hideTimer = setTimeout(close, 2500)
  }
}

onBeforeUnmount(clearTimer)
</script>

<template>
  <span ref="triggerEl" class="risk-tip" @mouseenter="onEnter" @mouseleave="onLeave" @click="onClick">
    <slot />
  </span>
  <Teleport to="body">
    <transition name="tip-fade">
      <span v-if="show && text" class="tip-bubble" :class="placement" :style="style">{{ text }}</span>
    </transition>
  </Teleport>
</template>

<style scoped>
.risk-tip {
  display: inline-flex;
}
.tip-bubble {
  position: fixed;
  z-index: 4000;
  max-width: 240px;
  padding: 6px 10px;
  background: rgba(0, 0, 0, 0.78);
  color: #fff;
  font-size: 12px;
  line-height: 1.5;
  border-radius: 6px;
  word-break: break-word;
  pointer-events: none;
}
.tip-bubble.top {
  transform: translate(-50%, -100%);
}
.tip-bubble.top::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: rgba(0, 0, 0, 0.78);
}
.tip-bubble.bottom {
  transform: translate(-50%, 0);
}
.tip-bubble.bottom::after {
  content: '';
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-bottom-color: rgba(0, 0, 0, 0.78);
}
.tip-fade-enter-active,
.tip-fade-leave-active {
  transition: opacity 0.15s ease;
}
.tip-fade-enter-from,
.tip-fade-leave-to {
  opacity: 0;
}
</style>
