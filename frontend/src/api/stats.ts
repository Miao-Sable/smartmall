import request from './request'

export interface DailyCount {
  date: string
  count: number
}

export interface StatsOverview {
  total_scans: number
  allergen_alerts: number
  today_scans: number
  avg_score: number
  recent_days: DailyCount[]
}

export const getStatsApi = (profileId?: number | null) =>
  request
    .get<StatsOverview>('/stats/overview', {
      params: profileId == null ? undefined : { profile_id: profileId },
    })
    .then((r) => r.data)
