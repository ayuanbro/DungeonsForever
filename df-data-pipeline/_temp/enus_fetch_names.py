# -*- coding: utf-8 -*-
"""从 Data_DungeonQuests.lua 提取 questID→名 / npcID→名，批量抓 wowhead 官方英文名。

- 走 Clash Verge 代理 127.0.0.1:7897，curl_cffi Chrome 指纹；
- 先试主站 /quest=ID、/npc=ID，404 再试 /forever/；
- 结果缓存 _temp/_enus_wowhead.json（增量续跑）；
- 最后产出 CN→EN 映射 _temp/enus_data_names.py（冲突留 TODO 注释）。
"""
import io, json, os, re, sys, time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "Core", "Data", "Data_DungeonQuests.lua")
CACHE = os.path.join(HERE, "_enus_wowhead.json")
OUT = os.path.join(HERE, "enus_data_names.py")

from curl_cffi import requests

PROXY = "http://127.0.0.1:7897"
HDRS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

src = io.open(SRC, encoding="utf-8").read()

# ── 提取 ────────────────────────────────────────────────────────────────────
# 任务行：{ questID, "H"/"A", lv, req, "giver", "loc", "questname"|nil, ...
qrows = re.findall(
    r'\{ (\d{3,6}), "([HA])", (-?\d+|nil), (\d+|nil), "([^"]*)", "([^"]*)", (?:(nil)|"([^"]*)")', src)
qname_by_id = {}
giver_names = set()
for qid, fac, lv, req, giver, loc, nil_, qname in qrows:
    if giver:
        giver_names.add(giver)
    if qname:
        qname_by_id.setdefault(int(qid), qname)

# 行尾 npcID, "名字"（giver 实体的 ID+名）
npc_by_id = {}
for nid, nm in re.findall(r'(\d{3,6}), "([\u4e00-\u9fff][^"]*)", \{\s*xp', src):
    npc_by_id.setdefault(int(nid), nm)

# giver 名 → ID 反查（补没有 xp 块的 giver）
giver_by_id = {}
for nid, nm in npc_by_id.items():
    giver_by_id[nm] = nid

# PreExtra 起始环里 "名字" 前后的 npcID 形态：QuestPreNpcID 键
for pid, nm in re.findall(r'\[(\d{3,6})\]\s*=\s*"([\u4e00-\u9fff][^"]*)"', src):
    npc_by_id.setdefault(int(pid), nm)

# 注释中的 QuestPreNpcID 表（在生成器/其他文件中，先只处理本文件可见的）
qids = sorted(qname_by_id)
npcs = sorted(npc_by_id)
print("unique quests: %d, unique npcs: %d" % (len(qids), len(npcs)))

# ── 抓取 ────────────────────────────────────────────────────────────────────
cache = {}
if os.path.exists(CACHE):
    cache = json.load(io.open(CACHE, encoding="utf-8"))

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
NOT_FOUND_HINTS = ("page not found", "wowhead'da", "couldn't find")

def fetch(kind, oid):
    key = "%s%d" % (kind, oid)
    if key in cache:
        return cache[key]
    for base in ("", "forever/"):
        url = "https://www.wowhead.com/%s%s=%d" % (base, kind, oid)
        for attempt in range(4):
            try:
                r = requests.get(url, headers=HDRS, proxy=PROXY,
                                 impersonate="chrome", timeout=20)
            except Exception as e:
                print("  ERR %s %s" % (url, e))
                time.sleep(5)
                continue
            if r.status_code == 403:
                wait = (15, 25, 35, 45)[attempt]
                print("  403 %s → sleep %ds" % (url, wait))
                time.sleep(wait)
                continue
            if r.status_code == 404:
                break
            if r.status_code == 200:
                m = TITLE_RE.search(r.text)
                if m:
                    t = m.group(1).strip()
                    t = re.sub(r"^\[DEPRECATED\]\s*", "", t)
                    t = re.sub(r"\s*-\s*(Quest|NPC)\s*-\s*World of Warcraft.*$", "", t).strip()
                    if t and not any(h in t.lower() for h in NOT_FOUND_HINTS):
                        cache[key] = t
                        return t
                break
        time.sleep(0.4)
    return None

def clean_title(t):
    t = re.sub(r"^\[DEPRECATED\]\s*", "", t)
    t = re.sub(r"^\[Deprecated for 4\.x\]\s*", "", t, flags=re.I)
    t = re.sub(r"\s*-\s*(Quest|NPC)\s*-\s*(World of Warcraft|Forever).*$", "", t).strip()
    return t

def is_name(s):
    """过滤混进来的注记值（如 QuestPreNpcID 表里的说明文字）。"""
    return not re.search(r'[。：；，]', s)

def run(kind, ids):
    todo = [i for i in ids if ("%s%d" % (kind, i)) not in cache]
    print("%s: %d to fetch" % (kind, len(todo)))
    for i, oid in enumerate(todo):
        t = fetch(kind, oid)
        print("  %s%d %s" % (kind, oid, t or "(none)"))
        if i % 20 == 0:
            json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))
    json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))

run("quest", qids)
run("npc", npcs)

# ── 产出映射 ────────────────────────────────────────────────────────────────
cn2en_q, cn2en_n, conflicts = {}, {}, []
for qid, cn in qname_by_id.items():
    if not is_name(cn):
        continue
    en = clean_title(cache["quest%d" % qid]) if cache.get("quest%d" % qid) else None
    if not en:
        continue
    if cn in cn2en_q and cn2en_q[cn] != en:
        conflicts.append(("quest", qid, cn, cn2en_q[cn], en))
    cn2en_q[cn] = en
for nid, cn in npc_by_id.items():
    if not is_name(cn):
        continue
    en = clean_title(cache["npc%d" % nid]) if cache.get("npc%d" % nid) else None
    if not en:
        continue
    if cn in cn2en_n and cn2en_n[cn] != en:
        conflicts.append(("npc", nid, cn, cn2en_n[cn], en))
    cn2en_n[cn] = en

if conflicts:
    print("CONFLICTS:")
    for c in conflicts:
        print(" ", c)

with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write('# -*- coding: utf-8 -*-\n')
    f.write('"""CN→EN 名字映射（wowhead 官方英文名，由 enus_fetch_names.py 生成）。\n')
    f.write('Q = 任务名 / N = NPC 名。重抓直接重跑 enus_fetch_names.py，禁手改。\n"""\n')
    f.write("Q = {\n")
    for k in sorted(cn2en_q):
        f.write("    %s: %s,\n" % (json.dumps(k, ensure_ascii=False), json.dumps(cn2en_q[k], ensure_ascii=False)))
    f.write("}\nN = {\n")
    for k in sorted(cn2en_n):
        f.write("    %s: %s,\n" % (json.dumps(k, ensure_ascii=False), json.dumps(cn2en_n[k], ensure_ascii=False)))
    f.write("}\n")
print("written:", OUT)
