# -*- coding: utf-8 -*-
"""终局解析 v3：NFU 60 级数据库（老版官方 CN 译名）对齐剩余斜杠成员/未决名 → wowhead EN 官方名。"""
import io, json, os, re, sys, time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.path.join(HERE, "..", "Core", "Data", "Data_DungeonQuests.lua")
CACHE = os.path.join(HERE, "_enus_wowhead.json")
OUT = os.path.join(HERE, "enus_data_names3.py")

import gen_enus_data as G
import enus_data_names2 as N2
import enus_data_names3 as N3

CJK = re.compile(r'[\u4e00-\u9fff]')
src = io.open(SRC, encoding="utf-8").read()

# 全部 npc= 字段（含斜杠名单拆分）→ qids
npcname_qids = {}
for qid, npcfield in re.findall(
        r'\[(\d{4,6})\]\s*=\s*\{[^}]*?npc\s*=\s*"([^"]*)"', src):
    for part in npcfield.split(' / '):
        part = part.strip()
        if part and CJK.search(part):
            npcname_qids.setdefault(part, set()).add(int(qid))

already = set(N3.H) | set(N2.N) | set(N2.Q) | set(G.EXACT)
todo = {k: sorted(v) for k, v in npcname_qids.items() if k not in already}
print("剩余未决:", len(todo))

cache = json.load(io.open(CACHE, encoding="utf-8"))
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0"}

def _get(url, nf=False):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HDRS, proxy="http://127.0.0.1:7897",
                             impersonate="chrome", timeout=20)
        except Exception as e:
            print("  ERR", url, e); time.sleep(4); continue
        if r.status_code == 403:
            time.sleep((15, 25, 35)[attempt]); continue
        return r
    return None

def fetch_en_title(nid):
    key = "npc%d" % nid
    if key in cache and cache[key]:
        return cache[key]
    r = _get("https://www.wowhead.com/npc=%d" % nid)
    t = None
    if r is not None and r.status_code == 200:
        m = re.search(r"<title>(.*?)</title>", r.text, re.S)
        if m:
            t = re.sub(r"\s*[-—]\s*NPC\s*[-—].*$", "", m.group(1).strip())
    cache[key] = t
    time.sleep(0.3)
    return t

def nfu_pairs(qid):
    key = "nfuq%d" % qid
    if key in cache:
        return cache[key]
    r = _get("https://db.nfuwow.com/60?quest=%d" % qid)
    out = {}
    if r is not None and r.status_code == 200:
        for nid, cn in re.findall(r'npc=(\d+)"[^>]*>([^<]{2,24})<', r.text):
            cn = cn.strip()
            if cn and CJK.search(cn) and cn not in out:
                out[cn] = int(nid)
    cache[key] = out
    time.sleep(0.3)
    return out

final, hand = {}, {}
for cn, qids in sorted(todo.items()):
    nid = None
    for qid in qids:
        pairs = nfu_pairs(qid)
        nid = pairs.get(cn)
        if not nid:  # 词序/全半角差异兜底
            sig = ''.join(sorted(cn))
            for nm, i2 in pairs.items():
                if ''.join(sorted(nm)) == sig:
                    nid = i2
                    break
        if nid:
            break
    if nid:
        en = fetch_en_title(nid)
        if en:
            final[cn] = en
            print("ok  %s ← npc%d → %s" % (cn, nid, en))
            continue
    hand[cn] = qids
    print("MISS %s q%s" % (cn, qids))

json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))
merged = dict(N3.H)
merged.update(final)
with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write('# -*- coding: utf-8 -*-\n')
    f.write('"""斜杠名单成员/老译名 CN→EN（enus_fetch5+6 生成，禁手改）。"""\n')
    f.write("H = {\n")
    for k in sorted(merged):
        f.write("    %s: %s,\n" % (json.dumps(k, ensure_ascii=False), json.dumps(merged[k], ensure_ascii=False)))
    f.write("}\n")
print("written:", OUT, len(merged))
print("MISS:", json.dumps(hand, ensure_ascii=False))
