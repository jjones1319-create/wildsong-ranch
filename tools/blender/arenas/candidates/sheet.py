"""Contact sheet + index.html for art-review/arena-candidates/ from its candidates.json.

    py -I tools/blender/arenas/candidates/sheet.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
DIR = ROOT / 'art-review' / 'arena-candidates'
W = 2600
IMG_H = 430
PAD = 18
GROUP = {'fallback': 'FALLBACK (ours, CC0 materials)', 'cc0': 'CC0', 'cc-by': 'CC-BY (needs owner OK for credit)'}
COL = {'fallback': (38, 120, 60), 'cc0': (30, 90, 160), 'cc-by': (170, 100, 20)}


def font(size: int, bold: bool = False):
    for f in (('segoeuib.ttf' if bold else 'segoeui.ttf'), 'arial.ttf'):
        try:
            return ImageFont.truetype(f'C:/Windows/Fonts/{f}', size)
        except OSError:
            continue
    return ImageFont.load_default()


def tris(c: dict) -> str:
    if c.get('stats') and (DIR / c['stats']).exists():
        n = json.loads((DIR / c['stats']).read_text(encoding='utf-8'))['triangles']
        return f'{n:,} (measured)'
    return f"{c['triangles']:,}" if c.get('triangles') else '?'


def card(c: dict) -> Image.Image:
    ims = [Image.open(DIR / p).convert('RGB') for p in c['images'] if (DIR / p).exists()]
    ims = [i.resize((max(1, int(i.width * IMG_H / i.height)), IMG_H)) for i in ims][:3]
    w = max(560, sum(i.width for i in ims) + 6 * (len(ims) - 1))
    lines = [
        (f"#{c['rank']}  {c['name']}", font(26, True), (20, 20, 20)),
        (f"by {c['author']}", font(19), (60, 60, 60)),
        (f"{GROUP[c['group']]}  |  {c['license']}", font(19, True), COL[c['group']]),
        (f"Triangles: {tris(c)}  |  already in Blender: {c['in_blender']}", font(19), (40, 40, 40)),
        (f"Rendered here: {'yes' if any('renders/' in p for p in c['images']) else 'no (page preview)'}", font(17), (90, 90, 90)),
    ]
    h = IMG_H + 12 + 31 * len(lines)
    im = Image.new('RGB', (w + 2 * 12, h + 12), (255, 255, 255))
    x = 12
    for i in ims:
        im.paste(i, (x, 12))
        x += i.width + 6
    d = ImageDraw.Draw(im)
    y = IMG_H + 20
    for text, f, col in lines:
        while d.textlength(text, font=f) > w and len(text) > 10:
            text = text[:-4] + '...'
        d.text((12, y), text, font=f, fill=col)
        y += 31
    return im


def sheet(data: dict) -> None:
    cards = [card(c) for c in sorted(data['candidates'], key=lambda c: c['rank'])]
    rows, row, rw = [], [], 0
    for c in cards:
        if row and rw + c.width + PAD > W - 2 * PAD:
            rows.append(row)
            row, rw = [], 0
        row.append(c)
        rw += c.width + PAD
    rows.append(row)
    head = 150
    H = head + sum(max(c.height for c in r) + PAD for r in rows) + PAD
    s = Image.new('RGB', (W, H), (228, 230, 234))
    d = ImageDraw.Draw(s)
    d.text((PAD, 16), 'Tournament amphitheatre: candidates (best first)', font=font(40, True), fill=(20, 20, 20))
    d.text((PAD, 70), 'Grey capsules = 1 m stand-ins 4.6 m apart; white circle = the 12 m duel ring. Battle views: phone portrait, '
           'camera 1.6 m high. Renders: Blender 5.2 EEVEE, no light bake.', font=font(21), fill=(50, 50, 50))
    d.text((PAD, 102), 'Phone budget: <= 150k triangles, <= 12 MB after optimising. Licences checked on each asset page. '
           'Full size + notes: index.html', font=font(21), fill=(50, 50, 50))
    y = head
    for r in rows:
        x = PAD
        for c in r:
            s.paste(c, (x, y))
            x += c.width + PAD
        y += max(c.height for c in r) + PAD
    s.save(DIR / 'sheet.png', optimize=True)
    print('sheet', s.size)


def index(data: dict) -> None:
    e = html.escape
    parts = ['<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
             '<title>Arena candidates</title><style>body{font:16px system-ui,sans-serif;margin:16px;background:#eef0f3;color:#222}'
             'section{background:#fff;border-radius:10px;padding:14px;margin:14px 0}img{max-width:100%;height:auto;'
             'display:block;margin:8px 0;border-radius:6px}.imgs{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-start}'
             '.imgs a{flex:0 1 auto;max-width:100%}.imgs img{max-height:80vh}.lic{font-weight:600}.fallback{color:#26783c}'
             '.cc0{color:#1e5aa0}.cc-by{color:#aa6414}td{padding:2px 10px 2px 0;vertical-align:top}</style>',
             '<h1>Tournament amphitheatre: candidates</h1>', f"<p>{e(data['about'])}</p>",
             '<p><a href="sheet.png">Contact sheet</a> &middot; <a href="candidates.json">candidates.json</a></p>']
    for c in sorted(data['candidates'], key=lambda c: c['rank']):
        url = c['url'] if c['url'].startswith('http') else ''
        link = f'<a href="{e(url)}">{e(url)}</a>' if url else e(c['url'])
        rows = [('Author', e(c['author'])), ('Link', link),
                ('Licence', f'<span class="lic {c["group"]}">{e(c["license"])}</span> (<a href="{e(c["license_url"])}">text</a>)'),
                ('Format', e(c['format'])), ('Already in Blender', e(c['in_blender'])),
                ('Triangles', e(tris(c)) + (f" &middot; {e(c['triangles_note'])}" if c.get('triangles_note') else '')),
                ('Download', e(c['download'])), ('Verdict', e(c['verdict']))]
        imgs = ''.join(f'<a href="{e(p)}"><img src="{e(p)}" alt="{e(p)}" loading="lazy"></a>' for p in c['images'])
        table = ''.join(f'<tr><td><b>{k}</b></td><td>{v}</td></tr>' for k, v in rows)
        parts.append(f'<section><h2>#{c["rank"]} {e(c["name"])}</h2><table>{table}</table><div class="imgs">{imgs}</div></section>')
    parts.append('<section><h2>Also checked (rejected)</h2><ul>' +
                 ''.join(f'<li>{e(x)}</li>' for x in data['also_checked_rejected']) + '</ul></section>')
    (DIR / 'index.html').write_text('\n'.join(parts) + '\n', encoding='utf-8')
    print('index.html written')


if __name__ == '__main__':
    d = json.loads((DIR / 'candidates.json').read_text(encoding='utf-8'))
    sheet(d)
    index(d)
