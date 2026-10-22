import { useEffect, useState } from 'preact/hooks'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { fileNameFor, importUrlFor, monsterJsonText, monsterShareCode, qrSvgFor, shareTextFor } from '../../../save/exportImport.ts'
import { TopBar } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { canShare, copyText, downloadText, pageUrl, shareText } from '../../lib/files.ts'
import { navigate } from '../../router.ts'
import { showToast } from '../../store/appStore.ts'
import { selectedListed } from '../../store/labStore.ts'

/** §19 Export: share code with Copy, a QR code of the import link, a .json download, Web Share as .txt, and Copy link. */
export function LabExportScreen() {
  const t = UI_TEXT.lab.export_
  const listed = selectedListed()
  const [code, setCode] = useState<string | null>(null)
  const [qr, setQr] = useState<string | null | 'none'>(null)

  useEffect(() => {
    if (!listed) navigate('lab')
  }, [listed])

  const monsterId = listed?.monster.id
  useEffect(() => {
    if (!listed) return
    let alive = true
    setCode(null)
    setQr(null)
    void monsterShareCode(listed.monster).then(async (c) => {
      if (!alive) return
      setCode(c)
      const svg = await qrSvgFor(importUrlFor(pageUrl(), c))
      if (alive) setQr(svg ?? 'none')
    })
    return () => {
      alive = false
    }
  }, [monsterId])

  if (!listed) return null
  const m = listed.monster
  const link = code ? importUrlFor(pageUrl(), code) : ''

  const copy = async (value: string, okText: string) => showToast((await copyText(value)) ? okText : t.copyFailed)

  const download = () => {
    const file = fileNameFor(m, 'json')
    showToast(downloadText(file, monsterJsonText(m, listed.history)) ? fill(t.downloaded, { file }) : t.downloadFailed)
  }

  const share = async () => {
    if (!code) return
    const outcome = await shareText(fileNameFor(m, 'txt'), shareTextFor(m, code), m.name)
    if (outcome === 'shared') showToast(t.shared)
    else if (outcome === 'failed' || outcome === 'unsupported') showToast(t.shareFailed)
  }

  return (
    <main class="screen">
      <TopBar title={t.title} />
      <div class="preview">
        <MonsterPortrait monster={m} size={96} />
        <div class="preview__info">
          <span class="preview__name">{m.name}</span>
        </div>
      </div>

      <label class="field">
        <span class="field__label">{t.code}</span>
        <textarea class="textarea" readOnly rows={4} value={code ?? t.making} onFocus={(e) => (e.currentTarget as HTMLTextAreaElement).select()} />
      </label>
      <div class="btn-grid">
        <button type="button" class="btn btn--primary" disabled={!code} onClick={() => code && void copy(code, t.copied)}>
          {t.copy}
        </button>
        <button type="button" class="btn" disabled={!code} onClick={() => code && void copy(link, t.linkCopied)}>
          {t.copyLink}
        </button>
        <button type="button" class="btn" onClick={download}>
          {t.download}
        </button>
        {canShare() && (
          <button type="button" class="btn" disabled={!code} onClick={() => void share()}>
            {t.share}
          </button>
        )}
      </div>

      <section class="card">
        <p class="field__label">{t.qr}</p>
        {qr && qr !== 'none' && <div class="qr" dangerouslySetInnerHTML={{ __html: qr }} />}
        {qr === 'none' && <p class="muted small">{t.qrTooLong}</p>}
        {qr && qr !== 'none' && <p class="muted small center">{t.qrHint}</p>}
      </section>
    </main>
  )
}
