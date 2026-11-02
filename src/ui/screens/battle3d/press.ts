/**
 * docs/BATTLE_3D.md §5: a battle button that works while another finger holds the stick. Phones make no click for a
 * second finger (the owner, Nov 2: "I have to let off the joystick to use an attack"), so it acts on the touch itself;
 * a keyboard's click (detail 0) still works, and a finger's own click afterwards is ignored.
 */
export function press(fn: () => void): { onPointerDown: (e: PointerEvent) => void; onClick: (e: MouseEvent) => void } {
  return {
    onPointerDown: (e) => {
      if (e.pointerType === 'mouse' && e.button !== 0) return
      e.preventDefault()
      fn()
    },
    onClick: (e) => {
      if (e.detail === 0) fn()
    },
  }
}
