/**
 * Art 2.1: a lineup of shipped Ultra looks at true relative size, Puddlepup first (the approved yardstick).
 *
 *   npm run art:lineup -- <breed…> [--lite]
 *
 * Any shipped look works, a grown form too (`npm run art:lineup -- hearthwing hearthwing-grown`): each is read from
 * public/models/monsters-ultra/<look>.json and drawn at its own heightUnits.
 *
 * Each look is scaled the way the game scales it (model metres × heightUnits / restHeight, shown at 150 units = 1 m),
 * so the picture shows the sizes players will see, whatever size the model was built at. Two rows, front and
 * three-quarter, from a near-orthographic camera, with each look's name, height in units and modelled height (and a
 * note when the model breaks the size rule, HEIGHT_UNITS / 150 m tall). Renders with the game's film renderer through
 * tools/art/ultra-viewer/ in headless Chrome; writes art-review/lineup/lineup.png (+ front.png, three_quarter.png).
 * --lite lines up the Lite copies instead.
 */
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { BASE, launch, readSide, ROOT, savePng, startServer, stopServer, viewerPage, type UltraSide } from './ultra-serve.ts'

const UNITS_PER_METRE = 150
const REST_SHARE = 0.986          // Puddlepup's rest height over its HEIGHT_UNITS / 150: the size rule's yardstick
const W = 2400
const H = 760

const args = process.argv.slice(2)
const lite = args.includes('--lite')
const asked = args.filter((a) => !a.startsWith('--'))
const breeds = ['puddlepup', ...asked.filter((b) => b !== 'puddlepup')]
const OUT = join(ROOT, 'art-review', 'lineup')

interface Label { look: string; x: number; y: number; height: number }
type LineupFn = { lineup(o: unknown): Promise<{ png: string; labels: Label[] }> }

function info(side: UltraSide): { scale: number; note: string } {
  const shown = side.heightUnits / UNITS_PER_METRE
  const scale = shown / side.restHeight
  const rule = shown * REST_SHARE
  const off = Math.abs(side.restHeight - rule) / rule
  return { scale, note: off > 0.1 ? `modelled ${side.restHeight.toFixed(2)} m; the size rule says about ${rule.toFixed(2)} m` : '' }
}

async function main(): Promise<void> {
  mkdirSync(OUT, { recursive: true })
  const sides = new Map<string, UltraSide>()
  for (const b of breeds) {
    try {
      sides.set(b, readSide(b))
    } catch (e) {
      console.warn(`skipping ${b}: ${(e as Error).message}`)
    }
  }
  if (sides.size === 0) throw new Error('nothing shipped to line up')
  const looks = [...sides.entries()].map(([look, s]) => ({ look, scale: info(s).scale }))
  const server = await startServer()
  const rows: { name: string; file: string; labels: Label[] }[] = []
  try {
    const b = await launch()
    try {
      const page = await viewerPage(b, 2500)
      for (const [name, az, el] of [['front', 0, 6], ['three_quarter', 35, 12]] as const) {
        const r = await page.evaluate((o) => (window as unknown as { __ultra: LineupFn }).__ultra.lineup(o), { looks, az, el, width: W, height: H, lite })
        writeFileSync(join(OUT, `${name}.png`), savePng(r.png))
        rows.push({ name, file: `${name}.png`, labels: r.labels })
        console.log('lineup', name, r.labels.map((l) => `${l.look} ${l.height.toFixed(2)} m`).join(', '))
      }
      const label = (l: Label) => {
        const s = sides.get(l.look)!
        const { note } = info(s)
        // horns and other always-worn props may top the body (build_ultra reports restHeightWithProps beside restHeight)
        const withProps = typeof s.restHeightWithProps === 'number' ? ` · ${(s.restHeightWithProps * info(s).scale).toFixed(2)} m with props` : ''
        return `<div class="lab" style="left:${l.x.toFixed(0)}px;top:${Math.max(4, l.y - 50).toFixed(0)}px"><b>${l.look}</b><br>${s.heightUnits} units · shown ${l.height.toFixed(2)} m${withProps}${note ? `<br><span class="note">${note}</span>` : ''}</div>`
      }
      const html = `<!doctype html><html><head><meta charset="utf-8"><title>Ultra lineup</title><style>
body{margin:0;padding:16px 20px;background:#e4e6ea;font:14px/1.35 system-ui,Segoe UI,sans-serif;color:#1d2126;width:${W}px}
h1{font-size:21px;margin:0 0 4px} p{margin:0 0 10px} .row{position:relative;width:${W}px;height:${H}px;margin-bottom:14px}
.row img{display:block;border-radius:6px} .lab{position:absolute;transform:translateX(-50%);text-align:center;background:#fffd;border-radius:6px;padding:3px 8px;font-size:13px;white-space:nowrap}
.note{color:#a33}
</style></head><body>
<h1>Ultra lineup${lite ? ' (Lite copies)' : ''}: ${[...sides.keys()].join(', ')}</h1>
<p>Each look at its in-game relative size (heightUnits; 150 units = 1 m), Puddlepup first. Front, then three-quarter. The game's film renderer, near-orthographic camera.</p>
${rows.map((r) => `<div class="row"><img src="${r.file}" width="${W}" height="${H}">${r.labels.map(label).join('')}</div>`).join('\n')}
</body></html>`
      writeFileSync(join(OUT, 'index.html'), html)
      const sheet = await b.newPage({ viewport: { width: W + 40, height: 400 }, deviceScaleFactor: 1 })
      await sheet.goto(`${BASE}art-review/lineup/index.html`)
      await sheet.waitForLoadState('networkidle')
      await sheet.screenshot({ path: join(OUT, 'lineup.png'), fullPage: true })
      console.log('lineup', join(OUT, 'lineup.png'))
    } finally {
      await b.close()
    }
  } finally {
    stopServer(server)
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
