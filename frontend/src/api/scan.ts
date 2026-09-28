import request from './request'

export interface AllergenHit {
  allergen_name: string
  ingredient: string
}

export interface ScoreReason {
  type: 'allergen' | 'diet' | 'nutrition' | 'price'
  label: string
  delta: number
}

export interface Analysis {
  score: number
  level: string
  traffic_light: 'green' | 'yellow' | 'red'
  traffic_label: string
  allergen_hits: AllergenHit[]
  reasons: ScoreReason[]
  recommended: boolean
}

export interface ScanRecord {
  id: number
  barcode: string
  product_id: number | null
  product_name: string
  score: number
  level: string
  has_allergen: boolean
  source: string
  created_at: string
  analysis: Analysis | null
}

export const createScanApi = (barcode: string, source = 'manual') =>
  request.post<ScanRecord>('/scan', { barcode, source }).then((r) => r.data)

export const getScanApi = (scanId: number) =>
  request.get<ScanRecord>(`/scan/${scanId}`).then((r) => r.data)

export const getScanHistoryApi = () => request.get<ScanRecord[]>('/scan/history').then((r) => r.data)
