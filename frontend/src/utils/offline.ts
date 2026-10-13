// 离线安全模式：断网时用内置 mock 数据 + 本地缓存的档案，复刻后端 matching.py 的评分逻辑。
// 规则与 backend/app/services/matching.py 逐条对齐，保证离线结果与在线 100% 一致。
import allergensJson from '@/data/allergens.json'
import dietPreferencesJson from '@/data/diet_preferences.json'
import priceHistoryJson from '@/data/price_history.json'
import productsJson from '@/data/products.json'
import type { AllergenHit, Analysis, ScanRecord, ScoreReason } from '@/api/scan'
import type { PricePoint, Product } from '@/api/product'
import type { Profile } from '@/api/user'

// ---- 原始 mock 数据类型（nutrition.value 可能是数字或字符串） ----
interface RawNutrition {
  name: string
  value: string | number
  unit: string
}
interface RawProduct {
  id: number
  barcode: string
  name: string
  brand: string
  category: string
  image_url: string
  description: string
  tags: string[]
  ingredients: string[]
  nutrition: RawNutrition[]
}
interface RawDictItem {
  id: number
  name: string
  keywords: string[]
}
interface RawPriceHistory {
  product_id: number
  barcode: string
  points: PricePoint[]
}

const PRODUCTS = productsJson as unknown as RawProduct[]
const ALLERGENS = allergensJson as unknown as RawDictItem[]
const DIETS = dietPreferencesJson as unknown as RawDictItem[]
const PRICE_HISTORY = priceHistoryJson as unknown as RawPriceHistory[]

// ---- 网络 / 离线判定 ----

export function isOffline(): boolean {
  return typeof navigator !== 'undefined' && navigator.onLine === false
}

/** axios 网络/超时错误没有 response；业务错误（404/500 等）有 response */
export function isNetworkError(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false
  return (err as { response?: unknown }).response == null
}

// ---- 匹配引擎（复刻 matching.py） ----

type NameKeywords = { name: string; keywords: string[] }

function matchAllergens(ingredients: string[], userAllergens: NameKeywords[]): AllergenHit[] {
  const hits: AllergenHit[] = []
  for (const ing of ingredients) {
    for (const allergen of userAllergens) {
      if (allergen.keywords.some((kw) => ing.includes(kw))) {
        hits.push({ allergen_name: allergen.name, ingredient: ing })
      }
    }
  }
  return hits
}

function violatesDiet(ingredients: string[], tags: string[], diet: NameKeywords): boolean {
  if (tags.includes(diet.name)) return false
  return ingredients.some((ing) => diet.keywords.some((kw) => ing.includes(kw)))
}

function scoreLevel(score: number): string {
  if (score >= 90) return '非常适合'
  if (score >= 70) return '比较适合'
  if (score >= 50) return '一般'
  return '不适合'
}

const LIGHT_LABELS: Record<string, string> = { green: '适合', yellow: '谨慎', red: '不建议' }

function lightOf(hits: AllergenHit[], score: number): { light: string; label: string } {
  let light: string
  if (hits.length) light = 'red'
  else if (score >= 70) light = 'green'
  else if (score >= 50) light = 'yellow'
  else light = 'red'
  return { light, label: LIGHT_LABELS[light] ?? '适合' }
}

function nutritionWarnings(nutrition: RawNutrition[]): ScoreReason[] {
  const reasons: ScoreReason[] = []
  const rules = [
    { name: '碳水化合物', threshold: 60, label: '碳水化合物偏高（高糖）' },
    { name: '钠', threshold: 600, label: '钠含量偏高' },
    { name: '脂肪', threshold: 20, label: '脂肪偏高' },
  ]
  const byName = new Map(nutrition.map((n) => [n.name, n]))
  for (const rule of rules) {
    const item = byName.get(rule.name)
    if (!item) continue
    const value = Number(item.value)
    if (Number.isNaN(value)) continue
    if (value >= rule.threshold) {
      reasons.push({ type: 'nutrition', label: `${rule.label}（${value.toFixed(0)}${item.unit}/100g）`, delta: -5 })
    }
  }
  return reasons
}

function priceReason(productId: number): ScoreReason | null {
  const points = PRICE_HISTORY.find((h) => h.product_id === productId)?.points ?? []
  if (points.length < 2) return null
  const prices = points.map((p) => p.price)
  const latest = prices[prices.length - 1]
  const avg = prices.reduce((a, b) => a + b, 0) / prices.length
  if (latest < avg * 0.9) return { type: 'price', label: `当前价 ¥${latest.toFixed(1)} 低于近期均价`, delta: 5 }
  if (latest > avg * 1.1) return { type: 'price', label: `当前价 ¥${latest.toFixed(1)} 高于近期均价`, delta: -5 }
  return null
}

function analyzeOffline(product: RawProduct, userAllergens: NameKeywords[], userDiets: NameKeywords[]): Analysis {
  const ingredients = product.ingredients ?? []
  const tags = product.tags ?? []
  const reasons: ScoreReason[] = []

  // 过敏源：每命中一种 -40（同种过敏源命中多成分只扣一次，明细保留全部成分）
  const hits = matchAllergens(ingredients, userAllergens)
  const byAllergen = new Map<string, string[]>()
  for (const h of hits) {
    const arr = byAllergen.get(h.allergen_name) ?? []
    arr.push(h.ingredient)
    byAllergen.set(h.allergen_name, arr)
  }
  for (const [name, ings] of byAllergen) {
    reasons.push({ type: 'allergen', label: `含${name}：${ings.join('、')}`, delta: -40 })
  }

  // 饮食偏好：标签命中 +5，关键词违规 -10
  for (const diet of userDiets) {
    if (tags.includes(diet.name)) reasons.push({ type: 'diet', label: `含「${diet.name}」标签，符合偏好`, delta: 5 })
    else if (violatesDiet(ingredients, tags, diet)) reasons.push({ type: 'diet', label: `不符合「${diet.name}」饮食偏好`, delta: -10 })
  }

  reasons.push(...nutritionWarnings(product.nutrition ?? []))
  const pr = priceReason(product.id)
  if (pr) reasons.push(pr)

  const score = Math.max(0, Math.min(100, 100 + reasons.reduce((s, r) => s + r.delta, 0)))
  const { light, label } = lightOf(hits, score)

  return {
    score,
    level: scoreLevel(score),
    traffic_light: light as 'green' | 'yellow' | 'red',
    traffic_label: label,
    allergen_hits: hits,
    reasons,
    recommended: light === 'green',
  }
}

// ---- 档案 → 过敏/偏好（等价后端 load_profile_allergens / load_profile_diets） ----

function profileAllergens(profile: Profile | null): NameKeywords[] {
  if (!profile) return []
  const ids = new Set(profile.allergen_ids)
  return ALLERGENS.filter((a) => ids.has(a.id)).map((a) => ({ name: a.name, keywords: a.keywords }))
}

function profileDiets(profile: Profile | null): NameKeywords[] {
  if (!profile) return []
  const ids = new Set(profile.diet_ids)
  return DIETS.filter((d) => ids.has(d.id)).map((d) => ({ name: d.name, keywords: d.keywords }))
}

// ---- 对外入口 ----

export interface OfflineResult {
  product: Product
  pricePoints: PricePoint[]
  scan: ScanRecord
}

function toProduct(raw: RawProduct): Product {
  return {
    id: raw.id,
    barcode: raw.barcode,
    name: raw.name,
    brand: raw.brand,
    category: raw.category,
    image_url: raw.image_url,
    description: raw.description,
    ingredients: raw.ingredients,
    tags: raw.tags,
    nutrition: raw.nutrition.map((n) => ({ name: n.name, value: String(n.value), unit: n.unit, per: '100g' })),
  }
}

/** 本地安全分析：找不到商品返回 null；profile 为空则用空过敏/偏好（仍给出营养+价格评分） */
export function analyzeLocal(barcode: string, profile: Profile | null): OfflineResult | null {
  const raw = PRODUCTS.find((p) => String(p.barcode) === String(barcode))
  if (!raw) return null

  const analysis = analyzeOffline(raw, profileAllergens(profile), profileDiets(profile))
  const scan: ScanRecord = {
    id: 0,
    barcode: raw.barcode,
    product_id: raw.id,
    product_name: raw.name,
    score: analysis.score,
    level: analysis.level,
    has_allergen: analysis.allergen_hits.length > 0,
    source: 'offline',
    created_at: '',
    profile_id: profile?.id ?? null,
    profile_name: profile?.name ?? '',
    analysis,
  }

  return {
    product: toProduct(raw),
    pricePoints: PRICE_HISTORY.find((h) => h.product_id === raw.id)?.points ?? [],
    scan,
  }
}
