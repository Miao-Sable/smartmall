import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { loginApi, registerApi } from '@/api/auth'
import { getProfileApi, getProfilesApi, type Profile, type UserProfile } from '@/api/user'
import { clearOfflineQueue, flushOfflineScans } from '@/utils/offlineSync'

const ACTIVE_PROFILE_KEY = 'active-profile-id'
const CACHED_PROFILES_KEY = 'cached-profiles'

function readActiveProfileId(): number | null {
  const raw = localStorage.getItem(ACTIVE_PROFILE_KEY)
  if (!raw) return null
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
}

function readProfiles(): Profile[] {
  try {
    const raw = localStorage.getItem(CACHED_PROFILES_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as Profile[]) : []
  } catch {
    return []
  }
}

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') ?? '')
  const profile = ref<UserProfile | null>(null)
  const profiles = ref<Profile[]>(readProfiles())
  const activeProfileId = ref<number | null>(readActiveProfileId())

  const isLoggedIn = computed(() => token.value !== '')

  const defaultProfile = computed(
    () => profiles.value.find((p) => p.is_default) ?? profiles.value[0] ?? null,
  )
  const activeProfile = computed(
    () => profiles.value.find((p) => p.id === activeProfileId.value) ?? defaultProfile.value ?? null,
  )

  async function login(email: string, password: string) {
    const res = await loginApi({ email, password })
    token.value = res.access_token
    localStorage.setItem('token', res.access_token)
    await fetchProfile()
    await fetchProfiles()
  }

  async function register(data: { email: string; password: string; phone?: string }) {
    await registerApi(data)
  }

  function logout() {
    token.value = ''
    profile.value = null
    profiles.value = []
    activeProfileId.value = null
    localStorage.removeItem('token')
    localStorage.removeItem(ACTIVE_PROFILE_KEY)
    localStorage.removeItem(CACHED_PROFILES_KEY)
    clearOfflineQueue()
  }

  async function fetchProfile() {
    if (!isLoggedIn.value) return
    profile.value = await getProfileApi()
  }

  async function fetchProfiles() {
    if (!isLoggedIn.value) return
    try {
      profiles.value = await getProfilesApi()
      localStorage.setItem(CACHED_PROFILES_KEY, JSON.stringify(profiles.value))
      void flushOfflineScans()
    } catch {
      // 离线/失败时保留本地缓存
    }
    if (activeProfileId.value == null || !profiles.value.some((p) => p.id === activeProfileId.value)) {
      setActiveProfile(defaultProfile.value?.id ?? null)
    }
  }

  function setActiveProfile(id: number | null) {
    activeProfileId.value = id
    if (id == null) localStorage.removeItem(ACTIVE_PROFILE_KEY)
    else localStorage.setItem(ACTIVE_PROFILE_KEY, String(id))
  }

  return {
    token,
    profile,
    profiles,
    activeProfileId,
    defaultProfile,
    activeProfile,
    isLoggedIn,
    login,
    register,
    logout,
    fetchProfile,
    fetchProfiles,
    setActiveProfile,
  }
})
