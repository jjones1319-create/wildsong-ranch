"""Download the arenas' CC0 Poly Haven sources (sources.json) into tools/blender/arenas/.cache/ (gitignored).

    py -I tools/blender/arenas/fetch.py

Uses the public Poly Haven API (https://api.polyhaven.com): /files/<id> for the download URLs and MD5s, /info/<id>
for the name and authors. Every file is checked against its MD5 and only ever read as data (images, glTF JSON and
buffers, HDR); nothing downloaded is executed. Writes .cache/manifest.json (id, type, name, authors, page URL, files),
which CREDITS.md and guild.json are written from.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
CACHE = HERE / '.cache'
API = 'https://api.polyhaven.com'
UA = {'User-Agent': 'WildsongRanch-arena-build/1.0 (CC0 asset fetch)'}


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def md5_of(p: Path) -> str:
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def safe_join(root: Path, rel: str) -> Path:
    """Only plain relative paths inside `root` (the API's include keys are like textures/x.jpg)."""
    pp = PurePosixPath(rel)
    if pp.is_absolute() or any(part in ('..', '') for part in pp.parts):
        raise ValueError(f'unsafe path from the API: {rel!r}')
    out = (root / Path(*pp.parts)).resolve()
    if root.resolve() not in out.parents and out != root.resolve():
        raise ValueError(f'path escapes the cache: {rel!r}')
    return out


def download(url: str, dst: Path, md5: str | None) -> None:
    if not url.startswith('https://dl.polyhaven.org/'):
        raise ValueError(f'unexpected download host: {url}')
    if dst.exists() and (md5 is None or md5_of(dst) == md5):
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + '.part')
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r, open(tmp, 'wb') as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            if md5 and md5_of(tmp) != md5:
                raise IOError(f'MD5 mismatch for {url}')
            tmp.replace(dst)
            print(f'  got {dst.relative_to(CACHE)} ({dst.stat().st_size / 1e6:.1f} MB)', flush=True)
            return
        except Exception as e:  # noqa: BLE001
            print(f'  retry {attempt + 1}: {e}', flush=True)
            time.sleep(2 + attempt * 3)
    raise IOError(f'could not download {url}')


def fetch_model(aid: str, res: str) -> list[str]:
    files = get_json(f'{API}/files/{aid}')
    g = files['gltf'][res]['gltf']
    root = CACHE / 'models' / aid
    out = []
    main = safe_join(root, f'{aid}.gltf')
    download(g['url'], main, g.get('md5'))
    out.append(main.name)
    for rel, f in g.get('include', {}).items():
        dst = safe_join(root, rel)
        download(f['url'], dst, f.get('md5'))
        out.append(rel)
    return out


def fetch_texture(aid: str, res: str, maps: list[str]) -> list[str]:
    files = get_json(f'{API}/files/{aid}')
    root = CACHE / 'textures' / aid
    out = []
    for m in maps:
        if m not in files:
            print(f'  {aid}: no {m} map', flush=True)
            continue
        f = files[m][res]['jpg']
        name = f['url'].rsplit('/', 1)[1]
        download(f['url'], safe_join(root, name), f.get('md5'))
        out.append(name)
    return out


def fetch_hdri(aid: str, res: str) -> list[str]:
    files = get_json(f'{API}/files/{aid}')
    f = files['hdri'][res]['hdr']
    name = f['url'].rsplit('/', 1)[1]
    download(f['url'], safe_join(CACHE / 'hdris' / aid, name), f.get('md5'))
    return [name]


def main() -> None:
    src = json.loads((HERE / 'sources.json').read_text(encoding='utf-8'))
    CACHE.mkdir(parents=True, exist_ok=True)
    man_path = CACHE / 'manifest.json'
    manifest: dict = {}
    jobs = [('model', a, lambda a=a: fetch_model(a, src['models']['res'])) for a in src['models']['ids']]
    jobs += [('texture', a, lambda a=a: fetch_texture(a, src['textures']['res'], src['textures']['maps'])) for a in src['textures']['ids']]
    jobs += [('hdri', a, lambda a=a: fetch_hdri(a, src['hdris']['res'])) for a in src['hdris']['ids']]
    for kind, aid, fn in jobs:
        print(f'{kind} {aid}', flush=True)
        info = get_json(f'{API}/info/{aid}')
        files = fn()
        manifest[aid] = {
            'type': kind,
            'name': info.get('name', aid),
            'authors': sorted(info.get('authors', {}).keys()),
            'url': f'https://polyhaven.com/a/{aid}',
            'license': 'CC0 1.0',
            'files': files,
        }
        man_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'done: {len(jobs)} assets in {CACHE}', flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
