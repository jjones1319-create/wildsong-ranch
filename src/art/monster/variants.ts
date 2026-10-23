/**
 * GAME_DESIGN §22 / CONTENT §12: the unique palette of each secret variant. The body wears these colours
 * instead of the sub breed's; the main breed's eyes stay unless the variant names its own.
 */
export interface VariantPalette {
  body: string
  belly: string
  accent: string
  eye: string
}

export const VARIANT_PALETTES: Readonly<Record<string, VariantPalette>> = {
  'songheart-puddlepup': { body: '#5FC7B0', belly: '#FFF4D6', accent: '#FF6FB5', eye: '#24323A' },
  'town-crier-tumblefox': { body: '#C8522B', belly: '#FFF7E8', accent: '#F2C14E', eye: '#2A1E22' },
  'glitch-tumblefox': { body: '#2DE2A6', belly: '#F4F4F4', accent: '#FF3D81', eye: '#101014' },
  'party-bloatoad': { body: '#8FB84A', belly: '#FFD9A6', accent: '#FF5C8A', eye: '#E9C46A' },
  'stormcrown-nimbusheep': { body: '#4A5366', belly: '#2E3440', accent: '#F2D16B', eye: '#E6ECF5' },
  'porcelain-moatshell': { body: '#F4F7FA', belly: '#FFFFFF', accent: '#2F5D8A', eye: '#2B2B2B' },
  'bonfire-cinderlynx': { body: '#5A1F14', belly: '#A03A1E', accent: '#FFB300', eye: '#FFF0A8' },
  'imperial-coilfang': { body: '#D4A017', belly: '#FFF0B8', accent: '#8A1C1C', eye: '#1B3A2B' },
  'syrup-nibblegrub': { body: '#D9892E', belly: '#FFE2A8', accent: '#8C4A12', eye: '#3B2F2F' },
  'beacon-wishlume': { body: '#F6F1EA', belly: '#FFFFFF', accent: '#D9262C', eye: '#3A2A2A' },
  'champion-quillion': { body: '#6B4A2E', belly: '#F1E4D0', accent: '#E8B923', eye: '#1E1E1E' },
  'dawnwing-galeheron': { body: '#F7B59A', belly: '#FFF1EA', accent: '#E86A8A', eye: '#F2C14E' },
  'granite-cobblemaw': { body: '#8E8E96', belly: '#C9C9CF', accent: '#4A4A52', eye: '#F2B544' },
  'moonlit-velvesper': { body: '#5C5F78', belly: '#D9DCEC', accent: '#C0C4D8', eye: '#F2E6A0' },
  'lantern-bearer-ashwraith': { body: '#2B2F3A', belly: '#4A5366', accent: '#5AB6FF', eye: '#CFF0FF' },
  'prism-zipwisp': { body: '#F5F2FF', belly: '#FFFFFF', accent: '#9B5CFF', eye: '#2A2140' },
  'obsidian-mirrorkin': { body: '#141418', belly: '#2C2C34', accent: '#7A7A88', eye: '#E0E0EA' },
  'silver-gearhoot': { body: '#BFC5CC', belly: '#E8ECF0', accent: '#5B6670', eye: '#F2B544' },
  'abyss-reefclaw': { body: '#1C3F6E', belly: '#2E6AA8', accent: '#F26B8A', eye: '#BFE3FF' },
  'gilded-lootlid': { body: '#E0B030', belly: '#F7DE8A', accent: '#8A5A12', eye: '#3A2A10' },
  'sunsoul-aurelwyrm': { body: '#FFF6E0', belly: '#FFFFFF', accent: '#E8B923', eye: '#8A5A12' },
}

export function variantPalette(variantId: string | null | undefined): VariantPalette | null {
  return variantId ? (VARIANT_PALETTES[variantId] ?? null) : null
}
