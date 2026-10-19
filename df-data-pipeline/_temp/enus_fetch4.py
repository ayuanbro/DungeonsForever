# -*- coding: utf-8 -*-
"""终局解析 v2：用 www.wowhead.com/classic/cn/quest=ID 的「开始于」锚点反查 NPC。

经典版任务页保留了 vanilla 任务的 infobox（主站 /cn/ 的 vanilla 任务页已空）。
页面是 JS 转义 BBCode：\\uXXXX + [url=\/classic\/cn\/npc=1182]安东修士[\/url]
→ 解码 \\u、去反斜杠，即可用精确/模糊 CN 名对到 npcID → EN /npc=ID 官方名。

对 fetch3 已走 title 路由的键：凡 classic-cn 能解析出 NPC 名的一律覆盖
（节点标签语义 = NPC 名）；解析不出的保留 title 值（那类确实是任务/物品名节点）。
产出覆盖 enus_data_names2.py。
"""
import io, json, os, re, sys, time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.path.join(HERE, "..", "Core", "Data", "Data_DungeonQuests.lua")
CACHE = os.path.join(HERE, "_enus_wowhead.json")
OUT = os.path.join(HERE, "enus_data_names2.py")

import gen_enus_data as G
import enus_data_names2 as N2

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
giver_qids = {}
for qid, fac, lv, req, giver, loc, nil_, qname in qrows:
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
print("名字类残余:", len(names))

# ── 抓取基建 ────────────────────────────────────────────────────────────────
cache = json.load(io.open(CACHE, encoding="utf-8"))
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
UNI = re.compile(r'\\u([0-9a-fA-F]{4})')

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
    t = re.sub(r"^\[Deprecated for 4\.x\]\s*", "", t, flags=re.I)
    t = re.sub(r"\s*[-—]\s*(Quest|NPC|任务|NPC)\s*[-—]\s*.*$", "", t).strip()
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
    """/classic/cn/quest=ID → {CN名: npcID}。"""
    key = "ccnq%d" % qid
    if key in cache:
        return cache[key]
    r = _get("https://www.wowhead.com/classic/cn/quest=%d" % qid)
    out = {}
    if r is not None and r.status_code == 200:
        txt = UNI.sub(lambda m: chr(int(m.group(1), 16)), r.text).replace('\\', '')
        for nid, cn in re.findall(r'\[url=[^\]]*?npc=(\d+)\]([^[]+?)\[/url\]', txt):
            cn = cn.strip()
            if cn and cn not in out:
                out[cn] = int(nid)
    cache[key] = out
    json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))
    time.sleep(0.4)
    return out

# ── 求解 ────────────────────────────────────────────────────────────────────
resolved, still = {}, []
for cn, qids in sorted(names.items()):
    nid = None
    for qid in qids:
        pairs = _cn_page_pairs(qid)
        nid = pairs.get(cn)
        if not nid:
            sig = ''.join(sorted(cn))
            for nm, i2 in pairs.items():
                if ''.join(sorted(nm)) == sig:
                    nid = i2
                    break
        if nid:
            break
    if nid:
        en = fetch_title("npc", nid)
        if en:
            resolved[cn] = en
            print("ok   %s ← npc%d → %s" % (cn, nid, en))
            continue
    still.append(cn)
json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))

# 合并：classic-cn 解析结果覆盖（NPC 名语义优先），其余保留 fetch3 值
merged_N = dict(N2.N)
merged_N.update(resolved)
merged_Q = dict(N2.Q)

with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write('# -*- coding: utf-8 -*-\n')
    f.write('"""CN→EN 名字映射（enus_fetch2/3/4 生成，禁手改）。"""\n')
    f.write("Q = {\n")
    for k in sorted(merged_Q):
        f.write("    %s: %s,\n" % (json.dumps(k, ensure_ascii=False), json.dumps(merged_Q[k], ensure_ascii=False)))
    f.write("}\nN = {\n")
    for k in sorted(merged_N):
        f.write("    %s: %s,\n" % (json.dumps(k, ensure_ascii=False), json.dumps(merged_N[k], ensure_ascii=False)))
    f.write("}\n")
print("written:", OUT, "N=", len(merged_N))
print("仍需人工:", len(still))
for s in still:
    print("  ", repr(s))
