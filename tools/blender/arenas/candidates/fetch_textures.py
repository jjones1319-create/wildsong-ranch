"""Download the CC0 Poly Haven textures the grand-amphitheatre blockout uses into .cache/candidates/textures/.

    py -I tools/blender/arenas/candidates/fetch_textures.py

Same API and checks as ../fetch.py (MD5-verified, https://dl.polyhaven.org only), kept separate so the Guild
arena's cache is never touched. Writes .cache/candidates/textures/manifest.json (id, name, authors, url).
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / '.cache' / 'candidates' / 'textures'
API = 'https://api.polyhaven.com'
UA = {'User-Agent': 'WildsongRanch-arena-candidates/1.0 (CC0 asset fetch)'}
IDS = ['coast_sand_01', 'large_sandstone_blocks_01', 'large_sandstone_blocks', 'castle_brick_07',
       'clay_roof_tiles_02', 'rough_linen']
MAPS = ['Diffuse', 'nor_gl', 'Rough']
RES = '2k'


def get_json(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def md5_of(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> None:
    manifest = {}
    for aid in IDS:
        files = get_json(f'{API}/files/{aid}')
        info = get_json(f'{API}/info/{aid}')
        got = []
        for m in MAPS:
            if m not in files:
                continue
            f = files[m][RES]['jpg']
            url = f['url']
            if not url.startswith('https://dl.polyhaven.org/'):
                raise ValueError(url)
            name = url.rsplit('/', 1)[1]
            dst = OUT / aid / name
            if not (dst.exists() and md5_of(dst) == f.get('md5')):
                dst.parent.mkdir(parents=True, exist_ok=True)
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                    dst.write_bytes(r.read())
                if f.get('md5') and md5_of(dst) != f['md5']:
                    raise IOError(f'MD5 mismatch {url}')
            got.append(name)
        manifest[aid] = {'name': info.get('name', aid), 'authors': sorted(info.get('authors', {})),
                         'url': f'https://polyhaven.com/a/{aid}', 'license': 'CC0 1.0', 'files': got}
        print(aid, got, flush=True)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
