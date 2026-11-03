"""Download the files of a FREE itch.io asset page (the "No thanks, just take me to the downloads" flow).

    py -I tools/blender/arenas/candidates/itch_fetch.py <page-url> <out-dir>

Research-only helper for the arena candidates (art-review/arena-candidates/). Files are saved as data and never run.
"""
from __future__ import annotations

import http.cookiejar
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'


def main(page: str, out: Path) -> None:
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [('User-Agent', UA)]
    h = op.open(page, timeout=60).read().decode('utf-8', 'replace')
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', h).group(1)
    body = urllib.parse.urlencode({'csrf_token': csrf}).encode()
    dl = json.loads(op.open(page.rstrip('/') + '/download_url', data=body, timeout=60).read())['url']
    h2 = op.open(dl, timeout=60).read().decode('utf-8', 'replace')
    uploads = re.findall(r'data-upload_id="(\d+)"', h2)
    names = re.findall(r'class="name"[^>]*>([^<]+)<', h2)
    out.mkdir(parents=True, exist_ok=True)
    for uid, name in zip(uploads, names):
        safe = re.sub(r'[^A-Za-z0-9._-]', '_', name)
        q = 'source=view_game&as_props=1&after_download_lightbox=true'
        r = op.open(f"{page.rstrip('/')}/file/{uid}?{q}", data=body, timeout=60)
        url = json.loads(r.read())['url']
        data = op.open(url, timeout=300).read()
        (out / safe).write_bytes(data)
        print(f'got {safe} ({len(data) / 1e6:.2f} MB)')


if __name__ == '__main__':
    main(sys.argv[1], Path(sys.argv[2]))
