#!/usr/bin/env python3
"""Download small (96px WebP) headshots for every current-roster player into faces_cache/. Skips ones already cached."""
import json, os, sys, urllib.request, concurrent.futures
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "faces_cache")
os.makedirs(CACHE, exist_ok=True)
imgs = json.load(open(os.path.join(HERE, "images.json")))
ids = sorted({i for t in imgs.values() for i in t["c"] if i})
def url(i): return "https://static.www.nfl.com/image/%s/f_webp,q_70,w_96,h_96,c_fill,g_face/league/%s" % ("private" if i[0] == "p" else "upload", i[1:])
def get(i):
    path = os.path.join(CACHE, i + ".webp")
    if os.path.exists(path) and os.path.getsize(path) > 200: return "cached"
    try:
        with urllib.request.urlopen(urllib.request.Request(url(i), headers={"User-Agent": "the53-build"}), timeout=30) as r:
            data = r.read()
        if len(data) < 200: return "tiny"
        open(path, "wb").write(data); return "ok"
    except Exception as e:
        return "fail"
from collections import Counter
with concurrent.futures.ThreadPoolExecutor(8) as ex:
    res = Counter(ex.map(get, ids))
print(len(ids), dict(res))
