import { FxLayer, type FxLayerOptions } from './FxLayer.ts'

/**
 * The lazy entry of the effects chunk (it pulls in PixiJS). The UI imports this file with a dynamic import on
 * the screens that draw effects; everything pure (quality, bus, recipes, elements) is imported directly.
 */
export async function createFxLayer(opts: FxLayerOptions): Promise<FxLayer | null> {
  const layer = new FxLayer(opts)
  const ok = await layer.init()
  if (!ok) {
    layer.destroy()
    return null
  }
  return layer
}

export type { FxLayer, FxLayerOptions, FxStats } from './FxLayer.ts'
