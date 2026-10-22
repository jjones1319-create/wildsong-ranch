/**
 * Browser-side file and sharing helpers (GAME_DESIGN §19 Export/Import). Chromium cannot share
 * `.json` files through Web Share, so sharing uses `.txt`; downloads use `.json`. Everything here
 * reports what happened instead of throwing, so the screen can show a friendly line.
 */

export function downloadText(fileName: string, text: string, mime = 'application/json'): boolean {
  try {
    const blob = new Blob([text], { type: mime })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 10_000)
    return true
  } catch {
    return false
  }
}

export function canShare(): boolean {
  return typeof navigator !== 'undefined' && typeof navigator.share === 'function'
}

export type ShareResult = 'shared' | 'cancelled' | 'unsupported' | 'failed'

/** Shares a `.txt` file when the phone allows files, otherwise the text itself. */
export async function shareText(fileName: string, text: string, title: string): Promise<ShareResult> {
  if (!canShare()) return 'unsupported'
  try {
    const file = new File([text], fileName, { type: 'text/plain' })
    const withFile: ShareData = { files: [file], title }
    if (typeof navigator.canShare === 'function' && navigator.canShare(withFile)) {
      await navigator.share(withFile)
    } else {
      await navigator.share({ title, text })
    }
    return 'shared'
  } catch (err) {
    return err instanceof DOMException && err.name === 'AbortError' ? 'cancelled' : 'failed'
  }
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    try {
      const area = document.createElement('textarea')
      area.value = text
      area.setAttribute('readonly', '')
      area.style.position = 'fixed'
      area.style.opacity = '0'
      document.body.appendChild(area)
      area.select()
      const ok = document.execCommand('copy')
      area.remove()
      return ok
    } catch {
      return false
    }
  }
}

export function readFileText(file: File): Promise<string | null> {
  return new Promise((resolve) => {
    try {
      const reader = new FileReader()
      reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : null)
      reader.onerror = () => resolve(null)
      reader.readAsText(file)
    } catch {
      resolve(null)
    }
  })
}

/** The page's own address without any hash: the base of an `#import=` link. */
export function pageUrl(): string {
  return `${location.origin}${import.meta.env.BASE_URL}`
}
