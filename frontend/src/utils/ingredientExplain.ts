// 成分白话翻译：内置成分词典 + 结合用户档案（过敏源/饮食偏好）的个性化解释。
// 词典见 @/data/ingredient_dictionary.json；过敏/偏好关键词复用 @/data/allergens.json、
// @/data/diet_preferences.json，与 backend/app/services/matching.py、@/utils/offline.ts 的匹配规则保持一致。
import dictionaryJson from '@/data/ingredient_dictionary.json'
import allergensJson from '@/data/allergens.json'
import dietPreferencesJson from '@/data/diet_preferences.json'
import type { Profile } from '@/api/user'

export type RiskLevel = 'low' | 'medium' | 'high'

export interface IngredientEntry {
  name: string
  plain_name: string
  category: string
  function: string
  aliases: string[]
  e_numbers: string[]
  risk_level: RiskLevel
  risk: string
  crowd_hints: string[]
  /** 添加剂/辅料，添加量极少（用于过敏命中的视觉降级提示） */
  trace?: boolean
}

export interface IngredientExplanation {
  ingredient: string
  entry: IngredientEntry | null
  level: RiskLevel | 'none'
  reasons: { label: string; level: RiskLevel }[]
  /** 过敏命中的微量添加剂：视觉降级为橙色，但评分/过敏判定不变 */
  trace?: boolean
}

interface RawDictItem {
  id: number
  name: string
  keywords: string[]
}

const DICT = dictionaryJson as unknown as IngredientEntry[]
const ALLERGENS = allergensJson as unknown as RawDictItem[]
const DIETS = dietPreferencesJson as unknown as RawDictItem[]

function norm(s: string): string {
  return s.trim().toLowerCase()
}

function matchesKeywords(ingredient: string, keywords: string[]): boolean {
  return (keywords ?? []).some((kw) => kw && ingredient.includes(kw))
}

/** 名称/别名/E 编号精确或子串匹配；精确优先，其次取匹配到的最长 token。 */
export function lookupIngredient(ingredient: string): IngredientEntry | null {
  const ing = norm(ingredient)
  let best: { entry: IngredientEntry; len: number } | null = null
  for (const entry of DICT) {
    const tokens = [entry.name, ...(entry.aliases ?? []), ...(entry.e_numbers ?? [])]
    for (const token of tokens) {
      const t = norm(token)
      if (!t) continue
      if (ing === t) return entry
      if (ing.includes(t) || t.includes(ing)) {
        if (!best || t.length > best.len) best = { entry, len: t.length }
      }
    }
  }
  return best?.entry ?? null
}

/** 解释单个成分：结合词典固有风险与当前档案的过敏源/饮食偏好，给出红/黄/绿级别与「与你相关」提示。 */
export function explainIngredient(ingredient: string, profile: Profile | null): IngredientExplanation {
  const entry = lookupIngredient(ingredient)
  const reasons: { label: string; level: RiskLevel }[] = []

  const allergenIds = new Set<number>(profile?.allergen_ids ?? [])
  const dietIds = new Set<number>(profile?.diet_ids ?? [])

  // 过敏源：命中 → 红色高风险（安全第一）
  for (const a of ALLERGENS) {
    if (allergenIds.has(a.id) && matchesKeywords(ingredient, a.keywords)) {
      reasons.push({ label: `你设置了「${a.name}」过敏：${ingredient}属于${a.name}类，可能引发过敏`, level: 'high' })
    }
  }

  // 饮食偏好：命中 → 黄色提示
  for (const d of DIETS) {
    if (dietIds.has(d.id) && matchesKeywords(ingredient, d.keywords)) {
      reasons.push({ label: `你在控制「${d.name}」：${ingredient}可能不符合该偏好`, level: 'medium' })
    }
  }

  // 级别 = 词典固有风险 与 个性化命中的最严重一档
  let risk: RiskLevel | null = entry?.risk_level ?? null
  for (const r of reasons) risk = worse(risk, r.level)
  let level: RiskLevel | 'none' = risk ?? 'none'

  // 微量添加剂（如鱼露）：本因过敏命中为高风险，但添加量极少，视觉降级为橙色；
  // 评分与过敏判定不变，仅调整展示层级。
  let trace = false
  if (entry?.trace && level === 'high') {
    level = 'medium'
    trace = true
    reasons.push({ label: `含添加剂 ${ingredient}（添加量极少，风险提示降级）`, level: 'medium' })
  }

  return { ingredient, entry, level, reasons, trace }
}

function worse(a: RiskLevel | null, b: RiskLevel | null): RiskLevel | null {
  if (a === 'high' || b === 'high') return 'high'
  if (a === 'medium' || b === 'medium') return 'medium'
  if (a === 'low' || b === 'low') return 'low'
  return null
}

/** 成分搜索：名称/白话名/别名/E 编号匹配，精确结果在前。 */
export function searchIngredients(query: string): IngredientEntry[] {
  const q = norm(query)
  if (!q) return []
  const exact: IngredientEntry[] = []
  const partial: IngredientEntry[] = []
  for (const entry of DICT) {
    const names = [entry.name, entry.plain_name, ...(entry.aliases ?? []), ...(entry.e_numbers ?? [])]
    if (names.some((n) => norm(n) === q)) exact.push(entry)
    else if (names.some((n) => norm(n).includes(q))) partial.push(entry)
  }
  return [...exact, ...partial].slice(0, 20)
}

/** 判断某成分是否为「添加剂·添加量极少」（词典中标记 trace）。用于购物清单等场景的过敏命中降级。 */
export function isTraceAdditive(ingredient: string): boolean {
  return lookupIngredient(ingredient)?.trace === true
}
