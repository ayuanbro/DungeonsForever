# -*- coding: utf-8 -*-
"""最后一批存疑键的 ID 级核实。

对象：hand4 里语义不明的任务名/ giver 名（q17/720/721/1193/2278/2284/2318/
2768/4082/4083/4742/5103/5582）。
两路：
1) EN 主站 /quest=ID 的 <title> = 官方英文任务名（fetch_title 同 fetch4）；
2) /classic/cn/quest=ID 的「开始于」锚点 → giver npcID → EN /npc=ID 官方 NPC 名。
只打印映射，不改表；由人工择优回填 hand 表。
"""
import io, json, os, re, sys, time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_enus_wowhead.json")

QUESTS = [17, 721, 720, 1193, 2278, 2284, 2318, 2768, 4082, 4083, 4742, 5103, 5582]
# giver 是 NPC 名的键：CN 名直接取该任务的 classic-cn 开始锚
GIVER_IS_NPC = {2768: "比格维兹", 4083: "塞娜尼·雷心", 4742: "维埃兰"}

cache = json.load(io.open(CACHE, encoding="utf-8"))
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
UNI = re.compile(r"\\u([0-9a-fA-F]{4})")
ANCHOR = re.compile(r"\[url=[^\]]*?npc=(\d+)\]([^[]+?)\[/url\]")

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
    t = re.sub(r"\s*[-—]\s*(Quest|NPC)\s*[-—]\s*.*$", "", t).strip()
    return t

def save():
    json.dump(cache, io.open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)

def fetch_title(kind, oid):
    key = "%s%d" % (kind, oid)
    if key in cache and cache[key]:
        return clean_title(cache[key])
    for base in ("", "forever/"):
        r = _get("https://www.wowhead.com/%s%s=%d" % (base, kind, oid))
        if r is None:
            continue
        if r.status_code == 404:
            cache[key] = None
            break
        if r.status_code == 200:
            m = TITLE_RE.search(r.text)
            if m:
                t = clean_title(m.group(1).strip())
                if t and "couldn't find" not in t.lower():
                    cache[key] = t
                    save()
                    return t
        time.sleep(1)
    save()
    return cache.get(key)

def fetch_ccnq(qid):
    key = "ccnq%d" % qid
    if key in cache:
        return cache[key]
    r = _get("https://www.wowhead.com/classic/cn/quest=%d" % qid)
    if r is None or r.status_code != 200:
        cache[key] = None
    else:
        txt = UNI.sub(lambda m: chr(int(m.group(1), 16)), r.text).replace("\\/", "/")
        cache[key] = txt
    save()
    return cache[key]

print("== EN quest titles ==")
for qid in QUESTS:
    t = fetch_title("quest", qid)
    print("q%-5d %s" % (qid, t))

print("\n== giver NPC (classic-cn anchor -> EN npc title) ==")
for qid, cn in GIVER_IS_NPC.items():
    page = fetch_ccnq(qid)
    if not page:
        print("q%-5d %s -> no ccnq page" % (qid, cn))
        continue
    ms = ANCHOR.findall(page)
    if not ms:
        print("q%-5d %s -> no anchors" % (qid, cn))
        continue
    npc_id, npc_cn = ms[0]
    en = fetch_title("npc", int(npc_id))
    print("q%-5d giver cn=%s (npc%s %s) -> en=%s" % (qid, cn, npc_id, npc_cn, en))

print("\n== npc 739 ==")
print(fetch_title("npc", 739))
save()
