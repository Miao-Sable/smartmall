/** 匹配度等级与颜色（与后端业务规则保持一致） */
export const SCORE_LEVELS = [
  { min: 90, label: '非常适合', color: '#07c160' },
  { min: 70, label: '比较适合', color: '#1989fa' },
  { min: 50, label: '一般', color: '#ff976a' },
  { min: 0, label: '不适合', color: '#ee0a24' },
] as const

export function scoreLevel(score: number) {
  return SCORE_LEVELS.find((l) => score >= l.min) ?? SCORE_LEVELS[SCORE_LEVELS.length - 1]
}

/** 红黄绿交通灯颜色（与后端 matching.LIGHT_LABELS 一致） */
export const TRAFFIC_COLORS: Record<string, string> = {
  green: '#07c160',
  yellow: '#ff976a',
  red: '#ee0a24',
}

export const TRAFFIC_LABELS: Record<string, string> = {
  green: '适合',
  yellow: '谨慎',
  red: '不建议',
}

export function trafficColor(light?: string) {
  return TRAFFIC_COLORS[light ?? ''] ?? TRAFFIC_COLORS.green
}

export function formatTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}
