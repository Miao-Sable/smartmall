import request from './request'

export interface UserProfile {
  user_id: number
  email: string
  nickname: string
  gender: string
  birth_year: number | null
  default_profile_id: number | null
  onboarded: boolean
}

export interface UserProfileUpdate {
  nickname?: string
  gender?: string
  birth_year?: number | null
}

export interface Profile {
  id: number
  name: string
  emoji: string
  birth_year: number | null
  scenario: string
  is_default: boolean
  allergen_ids: number[]
  diet_ids: number[]
}

export interface ProfileCreate {
  name?: string
  emoji?: string
  birth_year?: number | null
  scenario?: string
  allergen_ids?: number[]
  diet_ids?: number[]
}

export interface ProfileUpdate {
  name?: string
  emoji?: string
  birth_year?: number | null
  scenario?: string
  allergen_ids?: number[]
  diet_ids?: number[]
}

export const getProfileApi = () => request.get<UserProfile>('/user/profile').then((r) => r.data)

export const updateProfileApi = (data: UserProfileUpdate) =>
  request.put<UserProfile>('/user/profile', data).then((r) => r.data)

export const getProfilesApi = () => request.get<Profile[]>('/user/profiles').then((r) => r.data)

export const createProfileApi = (data: ProfileCreate) =>
  request.post<Profile>('/user/profiles', data).then((r) => r.data)

export const updateMemberProfileApi = (id: number, data: ProfileUpdate) =>
  request.put<Profile>(`/user/profiles/${id}`, data).then((r) => r.data)

export const deleteMemberProfileApi = (id: number) =>
  request.delete(`/user/profiles/${id}`).then((r) => r.data)
