import { useRef, useState } from 'preact/hooks'
import { INPUT } from '../../../data/tuning.ts'
import { flickIntent, stickIntent, type ScreenBasis } from './stickMath.ts'

/**
 * docs/BATTLE_3D.md §5: the left-thumb stick. It appears where the thumb lands. Its direction is read against the
 * camera (the part pointing at the opponent on screen walks forward or back, the part across strafes), so it means
 * the same from any camera. A quick flick sideways is a sidestep; a quick flick toward the opponent is a dash.
 */

export interface StickProps {
  /** The player's monster's forward and left directions on screen (unit vectors, CSS px, y down). */
  basis: () => ScreenBasis | null
  onMove: (dir: -1 | 0 | 1, side: -1 | 0 | 1) => void
  onSidestep: (dir: -1 | 1) => void
  onDash: () => void
  label: string
}

const S = INPUT.stick

export function ThumbStick(p: StickProps) {
  const [knob, setKnob] = useState<{ ox: number; oy: number; dx: number; dy: number } | null>(null)
  const st = useRef({ id: -1, ox: 0, oy: 0, t0: 0, peak: { x: 0, y: 0 }, peakMag: 0, dir: 0 as -1 | 0 | 1, side: 0 as -1 | 0 | 1 })

  const down = (e: PointerEvent) => {
    const el = e.currentTarget as HTMLElement
    el.setPointerCapture?.(e.pointerId)
    const r = el.getBoundingClientRect()
    const s = st.current
    s.id = e.pointerId
    s.ox = e.clientX - r.left
    s.oy = e.clientY - r.top
    s.t0 = performance.now()
    s.peak = { x: 0, y: 0 }
    s.peakMag = 0
    setKnob({ ox: s.ox, oy: s.oy, dx: 0, dy: 0 })
  }

  const moveTo = (e: PointerEvent) => {
    const s = st.current
    if (e.pointerId !== s.id) return
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect()
    let dx = e.clientX - r.left - s.ox
    let dy = e.clientY - r.top - s.oy
    const len = Math.hypot(dx, dy)
    if (len > S.radiusPx) {
      dx = (dx / len) * S.radiusPx
      dy = (dy / len) * S.radiusPx
    }
    setKnob({ ox: s.ox, oy: s.oy, dx, dy })
    const v = { x: dx / S.radiusPx, y: dy / S.radiusPx }
    const mag = Math.hypot(v.x, v.y)
    if (mag > s.peakMag) {
      s.peakMag = mag
      s.peak = v
    }
    const b = p.basis()
    const { dir, side } = b ? stickIntent(v, b) : { dir: 0 as const, side: 0 as const }
    if (dir !== s.dir || side !== s.side) {
      s.dir = dir
      s.side = side
      p.onMove(dir, side)
    }
  }

  const up = (e: PointerEvent) => {
    const s = st.current
    if (e.pointerId !== s.id) return
    s.id = -1
    const b = p.basis()
    const flick = b ? flickIntent(s.peak, performance.now() - s.t0, b) : null
    if (flick?.kind === 'sidestep') p.onSidestep(flick.dir)
    else if (flick?.kind === 'dash') p.onDash()
    s.dir = 0
    s.side = 0
    p.onMove(0, 0)
    setKnob(null)
  }

  return (
    <div class="stick" role="application" aria-label={p.label} onPointerDown={down} onPointerMove={moveTo} onPointerUp={up} onPointerCancel={up} onContextMenu={(e) => e.preventDefault()}>
      {knob && (
        <>
          <span class="stick__base" style={{ left: `${knob.ox}px`, top: `${knob.oy}px`, width: `${S.radiusPx * 2}px`, height: `${S.radiusPx * 2}px` }} />
          <span class="stick__knob" style={{ left: `${knob.ox + knob.dx}px`, top: `${knob.oy + knob.dy}px` }} />
        </>
      )}
    </div>
  )
}
