import io, json, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Core', 'Data', 'Data_ClassQuest.lua')
OUT = os.path.join(ROOT, '_temp', '_cq_npc_zh.json')
BASE = 'https://wuxianwow.com/data/page/quest/%d.json'

s = io.open(SRC, encoding='utf-8').read()
en = {}
for m in re.finditer(r'\{\s*(\d{2,7})\s*,\s*"((?:[^"\\]|\\.)*)"', s):
    nid, name = int(m.group(1)), m.group(2)
    if re.search(r'[A-Za-z]', name):
        en[nid] = name

ENT = re.compile(r'\{\s*(\d{2,7})\s*,\s*"((?:[^"\\]|\\.)*)"')
quests = {}
for line in s.splitlines():
    m = re.match(r'\s*\[\s*(\d{3,7})\s*\]\s*=\s*(\{.*)', line)
    if not m:
        continue
    qid, body = int(m.group(1)), m.group(2)
    parts = body.split(' e = ')
    st = [int(x) for x in ENT.findall(parts[0]) and [a for a, _ in ENT.findall(parts[0])]]
    en_ = [int(x) for x in ([a for a, _ in ENT.findall(parts[1])] if len(parts) > 1 else [])]
    quests[qid] = {'s': st, 'e': en_}

target = set(en)
need = [q for q, v in quests.items() if (set(v['s']) | set(v['e'])) & target]
print('english npc %d, quests %d' % (len(target), len(need)))


def fetch(qid):
    for _ in range(3):
        try:
            req = urllib.request.Request(BASE % qid, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.loads(r.read().decode('utf-8'))
            return qid, d
        except Exception:
            time.sleep(0.5)
    return qid, None


got = {}
byindex = {}
rows = []
with ThreadPoolExecutor(max_workers=8) as ex:
    for qid, d in ex.map(fetch, need):
        if not d:
            continue
        f = d.get('facts') or {}
        tmp = (f.get('questTmp') or {}).get(str(qid)) or {}
        mine = quests[qid]
        for key, mk in (('start', 's'), ('end', 'e')):
            arr = tmp.get(key) or []
            for e in arr:
                if e.get('kind') != 'npc' or not e.get('name'):
                    continue
                if e.get('id') and int(e['id']) in target:
                    got[int(e['id'])] = e['name']
            if arr and len(arr) == len(mine[mk]):
                pairs = []
                for i, e in enumerate(arr):
                    nid = mine[mk][i]
                    if nid in target and not e.get('id'):
                        pairs.append((nid, e['name']))
                if pairs:
                    byindex[qid] = pairs

for qid, pairs in byindex.items():
    for nid, nm in pairs:
        if nid not in got:
            got[nid] = nm
            rows.append((qid, nid, nm))

miss = sorted(target - set(got))
print('resolved %d / %d' % (len(got), len(target)))
print('--- by index ---')
for r in rows:
    print('  q%-7d %8d  -> %s' % r)
print('--- still english ---')
for k in miss:
    print('  %8d  %s' % (k, en[k]))

cache = {}
if os.path.exists(OUT):
    cache = json.load(io.open(OUT, encoding='utf-8'))
for k, v in got.items():
    cache[str(k)] = v
io.open(OUT, 'w', encoding='utf-8', newline='\n').write(
    json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True))
print('cache now %d' % len(cache))
