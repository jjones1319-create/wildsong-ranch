"""Download the Crown Amphitheatre's extra CC0 Poly Haven textures (crown_sources.json) into .cache/ (gitignored).

    py -I tools/blender/arenas/crown_fetch.py

Reuses fetch.py's checked download (MD5-verified, https://dl.polyhaven.org only; nothing downloaded is executed) and
writes .cache/crown_manifest.json (id, type, name, authors, page URL) for every source the arena uses, the Guild's
shared ones included. Run `py -I tools/blender/arenas/fetch.py` first for the shared ones.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))           # our own fetch.py (the -I flag leaves the script folder off the path)

import fetch as F  # noqa: E402


def info(aid: str, kind: str) -> dict:
    i = F.get_json(f'{F.API}/info/{aid}')
    return {'type': kind, 'name': i.get('name', aid), 'authors': sorted(i.get('authors', {}).keys()),
            'url': f'https://polyhaven.com/a/{aid}', 'license': 'CC0 1.0'}


def main() -> None:
    src = json.loads((HERE / 'crown_sources.json').read_text(encoding='utf-8'))
    t = src['textures']
    man: dict = {}
    for aid in t['ids']:
        print('texture', aid, flush=True)
        files = F.fetch_texture(aid, t['res'], t['maps'])
        man[aid] = {**info(aid, 'texture'), 'files': files}
    for aid in t['shared']:
        if not (F.CACHE / 'textures' / aid).exists():
            raise SystemExit(f'{aid} is missing: run py -I tools/blender/arenas/fetch.py first')
        man[aid] = info(aid, 'texture')
    for aid in src['hdris']['shared']:
        man[aid] = info(aid, 'hdri')
    (F.CACHE / 'crown_manifest.json').write_text(json.dumps(man, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'done: {len(man)} sources', flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
