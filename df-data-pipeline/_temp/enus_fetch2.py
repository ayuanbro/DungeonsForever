# -*- coding: utf-8 -*-
"""补抓 enus_data_names.py 漏掉的官方名（2026-09-25）。

思路：
1. 重扫 Data_DungeonQuests.lua，跑一遍翻译管线，得到残余中文串集合 R；
2. 把 R 分成三类：
   a) 任务标题（能对上某 questID 的 title）→ 用 /forever/quest=ID 补抓；
   b) NPC 名（QuestPreNpcID npc= 字段 / giver 列，含「 / 」名单拆分）→
      先抓 CN 侧任务页 www.wowhead.com/cn/quest=QID 的锚点对 (npcID, 中文名)，
      反查出 npcID，再抓 EN /npc=ID 拿官方名；
   c) 自由文本（含 。：；，）→ 写进 _enus_hand.txt 人工翻。
3. 产出与 enus_data_names.py 同格式的增量文件 enus_data_names2.py（Q2/N2），
   gen_enus_data.py 两张都吃。

缓存走 _enus_wowhead.json（与 enus_fetch_names.py 共用）。
"""
import io, json, os, re, sys, time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.path.join(HERE, "..", "Core", "Data", "Data_DungeonQuests.lua")
CACHE = os.path.join(HERE, "_enus_wowhead.json")
OUT = os.path.join(HERE, "enus_data_names2.py")
HAND = os.path.join(HERE, "_enus_hand.txt")

import gen_enus_data as G

# ── 残余集合（复用 enus_gap 的扫描）─────────────────────────────────────────
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
residual = []
seen = set()
for lit in literals(body):
    if CJK.search(lit) and lit not in seen:
        seen.add(lit)
        residual.append(lit)

# ── 提取 id↔名字关系 ────────────────────────────────────────────────────────
qrows = re.findall(
    r'\{ (\d{3,6}), "([HA])", (-?\d+|nil), (\d+|nil), "([^"]*)", "([^"]*)", (?:(nil)|"([^"]*)")', src)
title_by_qid = {}
giver_qids = {}   # giver CN → set(qid)
for qid, fac, lv, req, giver, loc, nil_, qname in qrows:
    if qname:
        title_by_qid.setdefault(int(qid), qname)
    if giver:
        giver_qids.setdefault(giver, set()).add(int(qid))

# QuestPreNpcID 行：[qid] = { ..., npc = "名字", lv = n }
npcname_qids = {}  # CN 名（或名单成员）→ set(qid)
for qid, npcfield in re.findall(
        r'\[(\d{4,6})\]\s*=\s*\{[^}]*?npc\s*=\s*"([^"]*)"', src):
    for part in npcfield.split(' / '):
        part = part.strip()
        if part:
            npcname_qids.setdefault(part, set()).add(int(qid))

is_free = lambda s: bool(re.search(r'[。：；，]', s))

quests_todo, npc_todo, hand = set(), {}, []
for s in residual:
    if is_free(s):
        hand.append(s)
        continue
    if s in title_by_qid:
        quests_todo.add(title_by_qid[s])
        continue
    if s in npcname_qids:
        for qid in npcname_qids[s]:
            npc_todo.setdefault(qid, set()).add(s)
        continue
    if s in giver_qids:
        for qid in giver_qids[s]:
            npc_todo.setdefault(qid, set()).add(s)
        continue
    hand.append(s)   # 归不了类的也进人工清单

print("residual=%d  quests=%d  npc-join quests=%d  hand=%d"
      % (len(residual), len(quests_todo), len(npc_todo), len(hand)))

# ── 抓取基建（与 enus_fetch_names.py 同款）─────────────────────────────────
from curl_cffi import requests

PROXY = "http://127.0.0.1:7897"
HDRS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
cache = {}
if os.path.exists(CACHE):
    cache = json.load(io.open(CACHE, encoding="utf-8"))

def _get(url):
    for attempt in range(4):
        try:
            r = requests.get(url, headers=HDRS, proxy=PROXY,
                             impersonate="chrome", timeout=20)
        except Exception as e:
            print("  ERR %s %s" % (url, e)); time.sleep(5); continue
        if r.status_code == 403:
            wait = (15, 25, 35, 45)[attempt]
            print("  403 %s → sleep %ds" % (url, wait)); time.sleep(wait); continue
        return r
    return None

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
NOT_FOUND_HINTS = ("page not found", "couldn't find", "wowhead'da")

def clean_title(t):
    t = re.sub(r"^\[DEPRECATED\]\s*", "", t)
    t = re.sub(r"^\[Deprecated for 4\.x\]\s*", "", t, flags=re.I)
    t = re.sub(r"\s*-\s*(Quest|NPC)\s*-\s*(World of Warcraft|Forever|魔兽世界).*$", "", t).strip()
    return t

def fetch_title(kind, oid):
    """EN 侧 /forever/ 主站双试，返回官方英文名。"""
    key = "%s%d" % (kind, oid)
    if key in cache:
        return cache[key]
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
                if t and not any(h in t.lower() for h in NOT_FOUND_HINTS):
                    cache[key] = t
                    return t
    time.sleep(0.4)
    return None

# CN 页 infobox 是 JS 转义 BBCode 形态：
#   \u63d0\u91cc\u5965... + [url=\/cn\/npc=1855]提里奥·弗丁[\/url]
# 先把 \uXXXX 解码，再抓 BBCode 锚点（不可用 <a href> 正则）。
UNI_RE = re.compile(r'\\u([0-9a-fA-F]{4})')
BB_ANCHOR_RE = re.compile(r'\[url=?\\?/cn\\?/npc=(\d+)\]([^[]+?)\[\\?/?url\]')
BB_ANCHOR_EN_RE = re.compile(r'\[url=?\\?/npc=(\d+)\]([^[]+?)\[\\?/?url\]')

def _decode(t):
    return UNI_RE.sub(lambda m: chr(int(m.group(1), 16)), t)

def _cn_page_title(t):
    m = TITLE_RE.search(t)
    if not m:
        return None
    return clean_title(_decode(m.group(1)).strip())

def fetch_cn_npc_name(nid):
    """/cn/npc=ID 的中文名（标题去尾缀）。"""
    key = "cnnpc%d" % nid
    if key in cache:
        return cache[key]
    r = _get("https://www.wowhead.com/cn/npc=%d" % nid)
    name = None
    if r is not None and r.status_code == 200:
        t = _cn_page_title(r.text)
        if t:
            name = re.sub(r'—NPC—.*$', '', t).strip()
    cache[key] = name or ""
    time.sleep(0.4)
    return cache[key]

def fetch_en_quest_npcs(qid):
    """EN 侧任务页 infobox 锚点 → {npcID: EN名}。"""
    key = "enqn%d" % qid
    if key in cache:
        return cache[key]
    out = {}
    r = _get("https://www.wowhead.com/quest=%d" % qid)
    if r is not None and r.status_code == 200:
        for nid, nm in BB_ANCHOR_EN_RE.findall(_decode(r.text)):
            nid = int(nid)
            if nid not in out:
                out[nid] = nm.strip()
    cache[key] = out
    time.sleep(0.4)
    return cache[key]

def fetch_cn_npc_anchors(qid):
    """CN 侧任务页 → {中文名: npcID}。"""
    key = "cnq%d" % qid
    if key in cache and cache[key]:
        return cache[key]
    r = _get("https://www.wowhead.com/cn/quest=%d" % qid)
    if r is None or r.status_code != 200:
        cache[key] = {}
        return cache[key]
    txt = _decode(r.text)
    pairs = {}
    for nid, cn in BB_ANCHOR_RE.findall(txt):
        cn = cn.strip()
        if cn and cn not in pairs:
            pairs[cn] = int(nid)
    cache[key] = pairs
    time.sleep(0.4)
    return cache[key]

def _fuzzy(pairs, cn):
    """词序不一致兜底：字符多重集相同即算同名（议员X vs X议员）。"""
    sig = ''.join(sorted(cn))
    for name, nid in pairs.items():
        if ''.join(sorted(name)) == sig:
            return nid
    return None

# ── 1) 补任务标题 ───────────────────────────────────────────────────────────
new_q = {}
for qid in sorted(quests_todo):
    t = fetch_title("quest", qid)
    cn = title_by_qid[qid]
    print("quest %d %s → %s" % (qid, cn, t or "(none)"))
    if t:
        new_q[cn] = t
json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))

# ── 2) NPC 名：CN 任务页反查 ID → EN 官方名 ────────────────────────────────
new_n, unresolved = {}, {}
for qid, names in sorted(npc_todo.items()):
    pairs = fetch_cn_npc_anchors(qid)
    json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))
    for cn in names:
        if cn in new_n:
            continue
        nid = pairs.get(cn) or _fuzzy(pairs, cn)
        if not nid:
            # CN 任务页死页兜底：EN 任务页锚点拿候选 npcID → CN npc 页核对中文名
            for cand, en in sorted(fetch_en_quest_npcs(qid).items()):
                cn2 = fetch_cn_npc_name(cand)
                if cn2 and (cn2 == cn or ''.join(sorted(cn2)) == ''.join(sorted(cn))):
                    nid = cand
                    break
        if not nid:
            unresolved.setdefault(cn, set()).add(qid)
            continue
        t = fetch_title("npc", nid)
        print("npc %s ← q%d/%d → %s" % (cn, qid, nid, t or "(none)"))
        if t:
            new_n[cn] = t
        else:
            unresolved.setdefault(cn, set()).add(qid)
json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))

# ── 3) 产出 ─────────────────────────────────────────────────────────────────
with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write('# -*- coding: utf-8 -*-\n')
    f.write('"""CN→EN 名字映射（补抓批次，enus_fetch2.py 生成，禁手改）。"""\n')
    f.write("Q = {\n")
    for k in sorted(new_q):
        f.write("    %s: %s,\n" % (json.dumps(k, ensure_ascii=False), json.dumps(new_q[k], ensure_ascii=False)))
    f.write("}\nN = {\n")
    for k in sorted(new_n):
        f.write("    %s: %s,\n" % (json.dumps(k, ensure_ascii=False), json.dumps(new_n[k], ensure_ascii=False)))
    f.write("}\n")
print("written:", OUT)

with io.open(HAND, "w", encoding="utf-8", newline="\n") as f:
    for s in hand:
        f.write(repr(s) + "\n")
print("hand list:", HAND, len(hand))
print("unresolved npc names:")
for k in sorted(unresolved):
    print("  %r ← qids %s" % (k, sorted(unresolved[k])))
