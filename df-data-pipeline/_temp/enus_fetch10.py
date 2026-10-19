# -*- coding: utf-8 -*-
import io, json, re, sys, time
sys.stdout.reconfigure(encoding="utf-8")
cache = json.load(io.open("_enus_wowhead.json", encoding="utf-8"))
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}

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

# 1) npc 10299 双端标题
for url in ("https://www.wowhead.com/npc=10299",
            "https://www.wowhead.com/classic/cn/npc=10299",
            "https://www.wowhead.com/forever/cn/npc=10299"):
    r = _get(url)
    t = None
    if r is not None and r.status_code == 200:
        m = re.search(r"<title>(.*?)</title>", r.text, re.S)
        t = m.group(1).strip() if m else None
    print(url, "->", r.status_code if r else None, t)
    time.sleep(1)

# 2) EN 任务页里嵌的 npc/object 线索
for qid in (2278, 4083):
    r = _get("https://www.wowhead.com/quest=%d" % qid)
    if r is None or r.status_code != 200:
        print("q%d: no page" % qid); continue
    body = r.text
    hits = sorted(set(re.findall(r"(npc|object)=(\d+)[^0-9]{0,3}", body)))[:20]
    names = sorted(set(re.findall(r"Norgannon[^<\"']*", body)))[:6]
    chal = sorted(set(re.findall(r"[A-Za-z']*[Cc]halice[^<\"']*", body)))[:6]
    ser = sorted(set(re.findall(r">([^<>]*?)(?:Thunderheart|Senad|Sened|Samir)[^<>]{0,20}<", body)))[:6]
    print("q%d: npc/obj refs=%s" % (qid, hits))
    print("  Norgannon-ish:", names)
    print("  chalice-ish:", chal)
    print("  thunderheart-ish:", ser)
