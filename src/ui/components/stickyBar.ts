import { useCallback, useEffect, useRef } from 'preact/hooks'

/** The CSS variable base.css reads for the page's scroll-padding-bottom. */
const VAR = '--actionbar-h'

function clear(): void {
  document.documentElement.style.removeProperty(VAR)
}

/**
 * The owner (Nov 3): on short phones the ranch's sticky action bar covered the herd strip. A callback ref for the bar:
 * while it is on the page, `--actionbar-h` holds its height (kept current as its rows come and go), so whenever the
 * browser scrolls something into view (focus, a card opening) it stops clear of the bar instead of under it.
 */
export function useStickyBarPadding(): (el: HTMLElement | null) => void {
  const ro = useRef<ResizeObserver | null>(null)
  useEffect(
    () => () => {
      ro.current?.disconnect()
      clear()
    },
    [],
  )
  return useCallback((el: HTMLElement | null) => {
    ro.current?.disconnect()
    ro.current = null
    if (!el || typeof ResizeObserver === 'undefined') {
      clear()
      return
    }
    const set = () => document.documentElement.style.setProperty(VAR, `${Math.ceil(el.getBoundingClientRect().height)}px`)
    ro.current = new ResizeObserver(set)
    ro.current.observe(el)
    set()
  }, [])
}
