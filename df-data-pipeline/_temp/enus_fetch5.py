# -*- coding: utf-8 -*-
"""斜杠名单成员解析：QuestPreNpcID 里 npc = "A / B / C" 的每个成员，
用其 qid 的 /classic/cn/quest=ID 锚点对（ccnq 缓存）反查 npcID → EN 官方名。
未匹配成员 → _enus_hand3.txt 人工拍板。产出 enus_data_names3.py（HAND 表）。
"""
import io, json, os, re, sys, time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.path.join(HERE, "..", "Core", "Data", "Data_DungeonQuests.lua")
CACHE = os.path.join(HERE, "_enus_wowhead.json")
OUT = os.path.join(HERE, "enus_data_names3.py")

import gen_enus_data as G
import enus_data_names2 as N2

CJK = re.compile(r'[\u4e00-\u9fff]')
src = io.open(SRC, encoding="utf-8").read()

# 斜杠名单成员 → qids
slash_members = {}
for qid, npcfield in re.findall(
        r'\[(\d{4,6})\]\s*=\s*\{[^}]*?npc\s*=\s*"([^"]*)"', src):
    if ' / ' not in npcfield:
        continue
    for part in npcfield.split(' / '):
        part = part.strip()
        if part and CJK.search(part):
            slash_members.setdefault(part, set()).add(int(qid))

already = set(N2.N) | set(N2.Q) | set(G.EXACT)
todo = {k: v for k, v in slash_members.items() if k not in already}
print("斜杠成员:", len(slash_members), "未决:", len(todo))

cache = json.load(io.open(CACHE, encoding="utf-8"))
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)

def _get(url):
    for attempt in range(4):
        try:
            r = requests.get(url, headers=HDRS, proxy="http://127.0.0.1:7897",
                             impersonate="chrome", timeout=20)
        except Exception as e:
            print("  ERR", url, e); time.sleep(5); continue
        if r.status_code == 403:
            wait = (15, 25, 35, 45)[attempt]
            print("  403 sleep", wait); time.sleep(wait); continue
        return r
    return None

def clean_title(t):
    t = re.sub(r"^\[DEPRECATED\]\s*", "", t)
    t = re.sub(r"\s*[-—]\s*(Quest|NPC)\s*[-—]\s*.*$", "", t).strip()
    return t

def fetch_title(kind, oid):
    key = "%s%d" % (kind, oid)
    if key in cache and cache[key]:
        return clean_title(cache[key])
    for base in ("", "forever/"):
        r = _get("https://www.wowhead.com/%s%s=%d" % (base, kind, oid))
        if r is None:
            continue
        if r.status_code == 404:
            break
        if r.status_code == 200:
            m = TITLE_RE.search(r.text)
            if m:
                t = clean_title(m.group(1).strip())
                if t and "couldn't find" not in t.lower():
                    cache[key] = t
                    return t
    time.sleep(0.4)
    return None

def _cn_page_pairs(qid):
    key = "ccnq%d" % qid
    if key in cache:
        return cache[key]
    r = _get("https://www.wowhead.com/classic/cn/quest=%d" % qid)
    out = {}
    if r is not None and r.status_code == 200:
        txt = re.sub(r'\\u([0-9a-fA-F]{4})',
                     lambda m: chr(int(m.group(1), 16)), r.text).replace('\\', '')
        for nid, cn in re.findall(r'\[url=[^\]]*?npc=(\d+)\]([^[]+?)\[/url\]', txt):
            cn = cn.strip()
            if cn and cn not in out:
                out[cn] = int(nid)
    cache[key] = out
    return out

def _fuzzy(pairs, cn):
    sig = ''.join(sorted(cn))
    for name, nid in pairs.items():
        if ''.join(sorted(name)) == sig:
            return nid
    return None

final, hand = {}, {}
for cn, qids in sorted(todo.items()):
    nid = None
    for qid in sorted(qids):
        pairs = _cn_page_pairs(qid)
        nid = pairs.get(cn) or _fuzzy(pairs, cn)
        if nid:
            break
    if nid:
        en = fetch_title("npc", nid)
        if en:
            final[cn] = en
            print("ok %s ← npc%d → %s" % (cn, nid, en))
            continue
    hand[cn] = sorted(qids)
    print("MISS %s (q%s)" % (cn, sorted(qids)))
    for qid in sorted(qids):
        print("    q%d pairs: %s" % (qid, _cn_page_pairs(qid)))
json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))

with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write('# -*- coding: utf-8 -*-\n')
    f.write('"""斜杠名单成员 CN→EN（enus_fetch5.py 生成，禁手改）。"""\n')
    f.write("H = {\n")
    for k in sorted(final):
        f.write("    %s: %s,\n" % (json.dumps(k, ensure_ascii=False), json.dumps(final[k], ensure_ascii=False)))
    f.write("}\n")
print("written:", OUT, len(final))
print("hand3:", hand)
