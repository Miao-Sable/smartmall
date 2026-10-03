import request from './request'
import type { AllergenHit } from './scan'

export interface ProductBrief {
  id: number
  name: string
  barcode: string
  category: string
  price: number
}

export interface PrecheckItem {
  name: string // 用户输入的原商品名
  match_type: 'exact' | 'fuzzy' | 'not_found'
  product: ProductBrief | null
  is_high_risk: boolean
  allergen_hits: AllergenHit[]
  diet_hits: string[]
  alternatives: ProductBrief[]
}

export interface PrecheckResult {
  items: PrecheckItem[]
}

export const precheckApi = (items: string[]) =>
  request.post<PrecheckResult>('/shopping-list/precheck', { items }).then((r) => r.data)

export const rematchApi = (name: string, excludeIds: number[]) =>
  request.post<ProductBrief[]>('/shopping-list/rematch', { name, exclude_ids: excludeIds }).then((r) => r.data)
