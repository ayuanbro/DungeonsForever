import base64
import re
from collections import Counter

import cbor2

TOC = r"D:\workspace\DungeonsForever\_temp\questie\forever\QuestieDB\QuestieDB_Forever.toc"
pat = re.compile(r"^## X-Quest-(\d+)-S:\s*(\S+)\s*$", re.M)
txt = open(TOC, encoding="utf-8", errors="replace").read()
want = {5722, 92401, 96393, 1654, 373, 97288, 166, 1013}
keycount = Counter()
n = 0
for m in pat.finditer(txt):
    q = int(m.group(1))
    n += 1
    try:
        row = cbor2.loads(base64.b64decode(m.group(2)))
    except Exception:
        continue
    keys = {}
    for k, v in row.items():
        kk = int(k) if isinstance(k, bytes) and k.isdigit() else (k.decode("utf-8", "replace") if isinstance(k, bytes) else k)
        keys[kk] = v
    for k in keys:
        keycount[k] += 1
    if q in want:
        show = {k: (v.decode("utf-8", "replace") if isinstance(v, bytes) else v) for k, v in keys.items()}
        print(q, sorted(str(x) for x in keys.keys()), show)
print("S rows:", n)
print("key counts:", sorted(keycount.items()))
