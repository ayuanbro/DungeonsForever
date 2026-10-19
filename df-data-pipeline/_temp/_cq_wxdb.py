import io, json, os, re, sys, time, urllib.request
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

quests = {}
for m in re.finditer(r'\[\s*(\d{3,7})\s*\]\s*=\s*\{(.*?)\n', s):
    qid, body = int(m.group(1)), m.group(2)
    ids = set(int(x) for x in re.findall(r'\{\s*(\d{2,7})\s*,\s*"', body))
    quests[qid] = ids

target = set(en)
need = [q for q, ids in quests.items() if ids & target]
print('english npc %d, quests to fetch %d' % (len(target), len(need)))


def fetch(qid):
    for _ in range(3):
        try:
            req = urllib.request.Request(BASE % qid, headers={'User-Agent': 'Mozilla/5.0'})
            urlopen = urllib.request.urlopen
            with urlopen(req, timeout=25) as r:
                d = json.loads(r.read().decode('utf-8'))
            out = {}
            tmp = (d.get('facts') or {}).get('questTmp') or {}
            for qd in tmp.values():
                for key in ('start', 'end'):
                    for e in (qd.get(key) or []):
                        if e.get('kind') == 'npc' and e.get('id') and e.get('name'):
                            out[int(e['id'])] = e['name']
            return qid, out
        except Exception:
            time.sleep(0.5)
    return qid, {}


got = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    for qid, out in ex.map(fetch, need):
        for k, v in out.items():
            if k in target:
                got[k] = v
print('resolved %d / %d' % (len(got), len(target)))
for k in sorted(target):
    print('  %8d  %-42s -> %s' % (k, en[k], got.get(k, '--')))

cache = {}
if os.path.exists(OUT):
    cache = json.load(io.open(OUT, encoding='utf-8'))
for k, v in got.items():
    cache[str(k)] = v
io.open(OUT, 'w', encoding='utf-8', newline='\n').write(
    json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True))
print('cache now %d' % len(cache))
