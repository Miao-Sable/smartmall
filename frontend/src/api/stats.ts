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

// ---- 健康周报 ----

export interface CategoryTrend {
  category: string
  count: number
  percentage: number
}

export interface NutritionSummary {
  high_sugar_count: number
  high_sodium_count: number
  high_fat_count: number
}

export interface WeeklyReport {
  period_start: string
  period_end: string
  total_scans: number
  allergen_avoided: number
  avg_score: number
  score_trend: string
  category_trends: CategoryTrend[]
  nutrition_summary: NutritionSummary
  top_products: string[]
}

export const getWeeklyReportApi = (profileId?: number | null) =>
  request
    .get<WeeklyReport>('/stats/weekly-report', {
      params: profileId == null ? undefined : { profile_id: profileId },
    })
    .then((r) => r.data)
