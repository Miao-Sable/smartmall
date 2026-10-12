import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { loginApi, registerApi } from '@/api/auth'
import { getProfileApi, getProfilesApi, type Profile, type UserProfile } from '@/api/user'

const ACTIVE_PROFILE_KEY = 'active-profile-id'

function readActiveProfileId(): number | null {
  const raw = localStorage.getItem(ACTIVE_PROFILE_KEY)
  if (!raw) return null
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
}

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') ?? '')
  const profile = ref<UserProfile | null>(null)
  const profiles = ref<Profile[]>([])
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
  }

  async function fetchProfile() {
    if (!isLoggedIn.value) return
    profile.value = await getProfileApi()
  }

  async function fetchProfiles() {
    if (!isLoggedIn.value) return
    profiles.value = await getProfilesApi()
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
