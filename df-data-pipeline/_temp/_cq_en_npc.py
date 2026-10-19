import io, re, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s = io.open(os.path.join(ROOT,'Core','Data','Data_ClassQuest.lua'), encoding='utf-8').read()
seen = {}
for m in re.finditer(r'\{\s*(\d{2,7})\s*,\s*"((?:[^"\\]|\\.)*)"', s):
    nid, name = int(m.group(1)), m.group(2)
    if re.search(r'[A-Za-z]', name):
        seen.setdefault(nid, [name, 0])
        seen[nid][1] += 1
print('english npc: %d' % len(seen))
for nid in sorted(seen):
    print('%8d  x%-3d %s' % (nid, seen[nid][1], seen[nid][0]))
cache = json.load(io.open(os.path.join(ROOT,'_temp','_cq_npc_zh.json'), encoding='utf-8')) if os.path.exists(os.path.join(ROOT,'_temp','_cq_npc_zh.json')) else {}
print('not in cache:', [n for n in sorted(seen) if str(n) not in cache])
