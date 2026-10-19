# -*- coding: utf-8 -*-
"""终局解析 v4：修 qrows 正则漏行问题。

旧正则遇到 loc=nil / giver=nil 的行整行失配 → 大批任务标题没进 title_by_qid。
本版用引号感知的字段切分器解析每一行：
- col0=questID, col4=giver, col6=title, 行尾 (npcID, "CN名") 对；
- 残余名 → title 路由（同 qids 全一致才收）/ 行尾 npcID 路由；
- 产出覆盖 enus_data_names2.py 的 Q/N。
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

# ── 引号感知行解析 ──────────────────────────────────────────────────────────
def split_fields(row):
    """按顶层逗号切分一行 { ... } 内容，引号与花括号感知。"""
    fields, buf, depth, in_str, i, n = [], [], 0, False, 0, len(row)
    while i < n:
        c = row[i]
        if in_str:
            buf.append(c)
            if c == '\\':
                buf.append(row[i+1] if i+1 < n else '')
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            buf.append(c)
        elif c == '{':
            depth += 1
            buf.append(c)
        elif c == '}':
            depth -= 1
            buf.append(c)
        elif c == ',' and depth == 0:
            fields.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(c)
        i += 1
    if buf:
        fields.append(''.join(buf).strip())
    return fields

def unquote(f):
    if len(f) >= 2 and f[0] == '"' and f[-1] == '"':
        return f[1:-1]
    return None

src = io.open(SRC, encoding="utf-8").read()

title_by_qid, giver_qids, tail_name_id = {}, {}, {}
for m in re.finditer(r'\{ (\d{3,6}), .{0,8000}?\},\r?\n', src):
    row = m.group(0).strip()
    row = row[1:row.rfind('}')]   # 剥掉最外层 { }，逗号切分才落在 depth 0
    fields = split_fields(row)
    if len(fields) < 8:
        continue
    qid = int(fields[0])
    if len(fields) > 6:
        t = unquote(fields[6])
        if t and CJK.search(t):
            title_by_qid.setdefault(qid, t)
    if len(fields) > 4:
        gv = unquote(fields[4])
        if gv and CJK.search(gv):
            giver_qids.setdefault(gv, set()).add(qid)
    # 行尾 npcID, "CN" 对
    for nid, cn in re.findall(r',\s*(\d{3,6}),\s*"([\u4e00-\u9fff][^"]*)"', row):
        tail_name_id.setdefault(cn, set()).add(int(nid))

print("title_by_qid=%d giver=%d tail_name=%d" % (len(title_by_qid), len(giver_qids), len(tail_name_id)))

# 反向：标题 → qids（残余以中文名查任务 ID）
qid_by_title = {}
for qid, t in title_by_qid.items():
    qid_by_title.setdefault(t, set()).add(qid)

# ── 残余扫描 ────────────────────────────────────────────────────────────────
def literals(s):
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == '-' and s[i:i+2] == '--':
            j = s.find('\n', i)
            i = n if j < 0 else j
            continue
        if c == '"' or c == "'":
            q = c; j = i + 1; buf = []
            while j < n:
                if s[j] == '\\':
                    buf.append(s[j:j+2]); j += 2; continue
                if s[j] == q:
                    break
                buf.append(s[j]); j += 1
            out.append(''.join(buf)); i = j + 1
            continue
        if s[i:i+2] == '[[':
            j = s.find(']]', i + 2)
            out.append(s[i+2:j if j >= 0 else n]); i = (j + 2) if j >= 0 else n
            continue
        i += 1
    return out

body, _ = G.transform(src)
residual, seen = [], set()
for lit in literals(body):
    if CJK.search(lit) and lit not in seen:
        seen.add(lit)
        residual.append(lit)

is_free = lambda s: bool(re.search(r'[。：；，]', s))

cache = json.load(io.open(CACHE, encoding="utf-8"))
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0"}
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
    t = re.sub(r"^\[Deprecated for 4\.x\]\s*", "", t, flags=re.I)
    t = re.sub(r"\s*[-—]\s*(Quest|NPC)\s*[-—].*$", "", t).strip()
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

new_q, new_n, hand = dict(N2.Q), dict(N2.N), []
for s in residual:
    if is_free(s):
        hand.append(s)
        continue
    if s in qid_by_title:
        got = None
        for qid in sorted(qid_by_title[s]):
            t = fetch_title("quest", qid)
            if t:
                got = t
                break
        if got:
            new_q[s] = got
            print("Q %s ← quest%s → %s" % (s, sorted(qid_by_title[s]), got))
            continue
    if s in tail_name_id:
        got = None
        for nid in sorted(tail_name_id[s]):
            t = fetch_title("npc", nid)
            if t:
                got = t
                break
        if got:
            new_n[s] = got
            print("N %s ← npc%s → %s" % (s, sorted(tail_name_id[s]), got))
            continue
    hand.append(s)
json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))

with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write('# -*- coding: utf-8 -*-\n')
    f.write('"""CN→EN 名字映射（enus_fetch2/3/4/7 生成，禁手改）。"""\n')
    f.write("Q = {\n")
    for k in sorted(new_q):
        f.write("    %s: %s,\n" % (json.dumps(k, ensure_ascii=False), json.dumps(new_q[k], ensure_ascii=False)))
    f.write("}\nN = {\n")
    for k in sorted(new_n):
        f.write("    %s: %s,\n" % (json.dumps(k, ensure_ascii=False), json.dumps(new_n[k], ensure_ascii=False)))
    f.write("}\n")
print("written:", OUT, "Q=", len(new_q), "N=", len(new_n))
print("hand:", len(hand))
with io.open(os.path.join(HERE, "_enus_hand4.txt"), "w", encoding="utf-8", newline="\n") as f:
    for s in hand:
        f.write(repr(s) + "\n")
