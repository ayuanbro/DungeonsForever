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

def title(url, pat=None):
    r = _get(url)
    if r is None or r.status_code != 200:
        print(url, "->", r.status_code if r else None); return None
    m = re.search(r"<title>(.*?)</title>", r.text, re.S)
    t = m.group(1).strip() if m else None
    print(url, "->", t)
    if pat:
        print("   grep:", sorted(set(re.findall(pat, r.text)))[:8])
    return t

# q739 giver + q720 starter item
for u, pat in (
    ("https://www.wowhead.com/classic/cn/quest=739", r"\[url=[^\]]*?npc=(\d+)\]([^[]+?)\[/url\]"),
    ("https://www.wowhead.com/quest=739", r"npc=(\d+)[\"'&][^;]{0,40}?name[\"']?[:=][\"']([^\"']+)[\"']"),
    ("https://www.wowhead.com/quest=720", r"[Cc]rumpled[^<\"']{0,40}"),
    ("https://www.wowhead.com/classic/cn/quest=720", r"弄皱[^<\]]{0,30}"),
):
    title(u, pat)
    time.sleep(1)
