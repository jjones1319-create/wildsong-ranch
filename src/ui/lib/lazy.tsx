import type { ComponentType } from 'preact'
import { useEffect, useState } from 'preact/hooks'
import { UI_TEXT } from '../../data/text/ui.ts'

/**
 * §22 performance: heavy screens load on first use with a dynamic import, so the first paint ships a
 * smaller bundle. The module is cached after its first load; the service worker precaches every chunk,
 * so the lazy screens work offline too. No preact/compat needed.
 */
export function lazyScreen<P extends object>(loader: () => Promise<Record<string, unknown>>, name: string): ComponentType<P> {
  let loaded: ComponentType<P> | null = null
  let pending: Promise<ComponentType<P>> | null = null
  const load = () => {
    if (loaded) return Promise.resolve(loaded)
    pending ??= loader().then((mod) => {
      loaded = mod[name] as ComponentType<P>
      return loaded
    })
    return pending
  }
  return function Lazy(props: P) {
    // The component is boxed: useState would call a bare function as a lazy initialiser.
    const [box, setBox] = useState<{ c: ComponentType<P> } | null>(loaded ? { c: loaded } : null)
    useEffect(() => {
      if (box) return
      let alive = true
      void load().then((c) => {
        if (alive) setBox({ c })
      })
      return () => {
        alive = false
      }
    }, [])
    if (!box) {
      return (
        <main class="screen">
          <p class="loading">{UI_TEXT.loading}</p>
        </main>
      )
    }
    const Comp = box.c
    return <Comp {...props} />
  }
}
