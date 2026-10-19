# -*- coding: utf-8 -*-
import io, json, re, sys, time
sys.stdout.reconfigure(encoding="utf-8")
cache = json.load(io.open("_enus_wowhead.json", encoding="utf-8"))
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}
UNI = re.compile(r"\\u([0-9a-fA-F]{4})")
ANCHOR = re.compile(r"\[url=[^\]]*?npc=(\d+)\]([^[]+?)\[/url\]")

def _get(url):
    for a in range(4):
        try:
            r = requests.get(url, headers=HDRS, proxy="http://127.0.0.1:7897",
                             impersonate="chrome", timeout=20)
        except Exception as e:
            print(" ERR", e); time.sleep(5); continue
        if r.status_code == 403:
            time.sleep((15, 25, 35, 45)[a]); continue
        return r
    return None

def save():
    json.dump(cache, io.open("_enus_wowhead.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)

def ccnq(qid):
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

def title(kind, oid):
    key = "%s%d" % (kind, oid)
    if key in cache:
        return cache[key]
    for base in ("", "forever/"):
        r = _get("https://www.wowhead.com/%s%s=%d" % (base, kind, oid))
        if r is None:
            continue
        if r.status_code == 404:
            cache[key] = None; break
        if r.status_code == 200:
            m = re.search(r"<title>(.*?)</title>", r.text, re.S)
            if m:
                t = re.sub(r"\s*[-—]\s*(Quest|NPC)\s*[-—]\s*.*$", "", m.group(1).strip())
                if t and "couldn't find" not in t.lower():
                    cache[key] = t; break
        time.sleep(1)
    save()
    return cache.get(key)

for qid in (720, 2278, 4083, 4742, 738, 17):
    page = ccnq(qid)
    print("== q%d ==" % qid)
    if not page:
        print("  no page"); continue
    ms = re.findall(r"(?:开始|结束)于：?\s*\[url=[^\]]*?npc=(\d+)\]([^[]+?)\[/url\]", page)
    print("  开始/结束锚:", ms[:6])
    all_a = ANCHOR.findall(page)
    print("  全部npc锚(前8):", all_a[:8])
print("q738 EN title:", title("quest", 738))
