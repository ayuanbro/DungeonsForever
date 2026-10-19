# -*- coding: utf-8 -*-
"""终局解析：把 enus_fetch2 未决的 NPC/链节点名全部落定。

三路：
1. wago.tools Creature 表（zhCN + enUS 两份 CSV，按 ID 拼接）→ CN→EN 官方名；
2. 链节点名 = 任务官方标题（npc 字段存的是任务/物品名的节点）：对 qids 逐个
   fetch EN quest title，全一致才收；
3. 都不中 → 写 _enus_hand2.txt 人工拍板。

产出覆盖 enus_data_names2.py（含 fetch2 的结果 + 本轮增量）。
"""
import csv, io, json, os, re, sys, time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.path.join(HERE, "..", "Core", "Data", "Data_DungeonQuests.lua")
CACHE = os.path.join(HERE, "_enus_wowhead.json")
OUT = os.path.join(HERE, "enus_data_names2.py")
HAND2 = os.path.join(HERE, "_enus_hand2.txt")

import gen_enus_data as G

# ── 残余集合（与 enus_fetch2 相同口径）──────────────────────────────────────
CJK = re.compile(r'[\u4e00-\u9fff]')

def literals(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c == '-' and src[i:i+2] == '--':
            j = src.find('\n', i)
            i = n if j < 0 else j
            continue
        if c == '"' or c == "'":
            q = c; j = i + 1; buf = []
            while j < n:
                if src[j] == '\\':
                    buf.append(src[j:j+2]); j += 2; continue
                if src[j] == q:
                    break
                buf.append(src[j]); j += 1
            out.append(''.join(buf)); i = j + 1
            continue
        if src[i:i+2] == '[[':
            j = src.find(']]', i + 2)
            out.append(src[i+2:j if j >= 0 else n]); i = (j + 2) if j >= 0 else n
            continue
        i += 1
    return out

src = io.open(SRC, encoding="utf-8").read()
body, _ = G.transform(src)
residual, seen = [], set()
for lit in literals(body):
    if CJK.search(lit) and lit not in seen:
        seen.add(lit)
        residual.append(lit)

qrows = re.findall(
    r'\{ (\d{3,6}), "([HA])", (-?\d+|nil), (\d+|nil), "([^"]*)", "([^"]*)", (?:(nil)|"([^"]*)")', src)
title_by_qid, giver_qids = {}, {}
for qid, fac, lv, req, giver, loc, nil_, qname in qrows:
    if qname:
        title_by_qid.setdefault(int(qid), qname)
    if giver:
        giver_qids.setdefault(giver, set()).add(int(qid))

npcname_qids = {}
for qid, npcfield in re.findall(
        r'\[(\d{4,6})\]\s*=\s*\{[^}]*?npc\s*=\s*"([^"]*)"', src):
    for part in npcfield.split(' / '):
        part = part.strip()
        if part:
            npcname_qids.setdefault(part, set()).add(int(qid))

is_free = lambda s: bool(re.search(r'[。：；，]', s))

# 名字类残余（非自由文本，且能归到 qid 的）
names = {}
for s in residual:
    if is_free(s):
        continue
    qids = set()
    if s in npcname_qids:
        qids |= npcname_qids[s]
    if s in giver_qids:
        qids |= giver_qids[s]
    if qids:
        names[s] = sorted(qids)

# 已被 fetch2 落定的（enus_data_names2.py 现有内容 + 全局已命中）先剔除
import enus_data_names2 as N2
already = set(N2.N) | set(N2.Q) | set(G.EXACT)
names = {s: q for s, q in names.items() if s not in already}
print("未决名字:", len(names))

# ── 1) wago Creature 双语拼接 ───────────────────────────────────────────────
def load_csv(path):
    with io.open(path, encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        hdr = next(rd)
        for row in rd:
            yield row

cn_by_id, en_by_id = {}, {}
for row in load_csv(os.path.join(HERE, "_creature.csv")):
    cn_by_id[row[0]] = row[1]
for row in load_csv(os.path.join(HERE, "_creature_en.csv")):
    en_by_id[row[0]] = row[1]
cn2en_wago = {}
for cid, cn in cn_by_id.items():
    en = en_by_id.get(cid)
    if cn and en and CJK.search(cn) and cn not in cn2en_wago:
        cn2en_wago[cn] = en
print("wago CN→EN:", len(cn2en_wago))

# ── 2) 任务官方标题兜底（同 qids 全一致才收）───────────────────────────────
cache = json.load(io.open(CACHE, encoding="utf-8"))
from curl_cffi import requests
PROXY = "http://127.0.0.1:7897"
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)

def _get(url):
    for attempt in range(4):
        try:
            r = requests.get(url, headers=HDRS, proxy=PROXY,
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
    t = re.sub(r"^\[Deprecated for 4\.x\]\s*", "", t, flags=re.I)
    t = re.sub(r"\s*-\s*(Quest|NPC)\s*-\s*(World of Warcraft|Forever|魔兽世界).*$", "", t).strip()
    return t

def fetch_title(qid):
    key = "quest%d" % qid
    if key in cache:
        return clean_title(cache[key]) if cache[key] else None
    for base in ("", "forever/"):
        r = _get("https://www.wowhead.com/%squest=%d" % (base, qid))
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
    cache[key] = None
    time.sleep(0.4)
    return None

# ── 求解 ────────────────────────────────────────────────────────────────────
final, hand = {}, []
for cn, qids in sorted(names.items()):
    en = cn2en_wago.get(cn)
    if en:
        final[cn] = en
        print("wago   %s → %s" % (cn, en))
        continue
    titles = {q: fetch_title(q) for q in qids}
    vals = {v for v in titles.values() if v}
    if len(vals) == 1:
        final[cn] = vals.pop()
        print("title  %s → %s  (q%s)" % (cn, final[cn], qids))
        continue
    hand.append((cn, qids, titles))
json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))

# 合并 fetch2 已有结果
merged_N = dict(N2.N); merged_N.update(final)
merged_Q = dict(N2.Q)

with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write('# -*- coding: utf-8 -*-\n')
    f.write('"""CN→EN 名字映射（补抓批次，enus_fetch2.py + enus_fetch3.py 生成，禁手改）。"""\n')
    f.write("Q = {\n")
    for k in sorted(merged_Q):
        f.write("    %s: %s,\n" % (json.dumps(k, ensure_ascii=False), json.dumps(merged_Q[k], ensure_ascii=False)))
    f.write("}\nN = {\n")
    for k in sorted(merged_N):
        f.write("    %s: %s,\n" % (json.dumps(k, ensure_ascii=False), json.dumps(merged_N[k], ensure_ascii=False)))
    f.write("}\n")
print("written:", OUT, "N=", len(merged_N))

with io.open(HAND2, "w", encoding="utf-8", newline="\n") as f:
    for cn, qids, titles in hand:
        f.write("%s    # qids=%s titles=%s\n" % (repr(cn), qids, titles))
print("hand2:", len(hand), "→", HAND2)
