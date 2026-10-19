# -*- coding: utf-8 -*-
import io, json, re, sys, time
sys.stdout.reconfigure(encoding="utf-8")
cache = json.load(io.open("_enus_wowhead.json", encoding="utf-8"))
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0 Safari/537.36"}
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

def title(url):
    r = _get(url)
    if r is None or r.status_code != 200:
        print(url, "->", r.status_code if r else None); return None
    m = re.search(r"<title>(.*?)</title>", r.text, re.S)
    t = m.group(1).strip() if m else None
    print(url.split("wowhead.com/")[-1], "->", t)
    return t

for iid in (15853, 15854, 15805, 15806, 13544, 18746, 18880):
    title("https://www.wowhead.com/item=%d" % iid)
    time.sleep(1)

r = _get("https://www.wowhead.com/classic/cn/quest=3907")
if r is not None and r.status_code == 200:
    txt = UNI.sub(lambda m: chr(int(m.group(1), 16)), r.text).replace("\\/", "/")
    ms = re.findall(r"(?:开始|结束)于：?\s*\[url=[^\]]*?npc=(\d+)\]([^[]+?)\[/url\]", txt)
    print("ccnq3907 锚:", ms[:4])
    if ms:
        nid = int(ms[0][0])
        title("https://www.wowhead.com/npc=%d" % nid)

r = _get("https://www.wowhead.com/quest=4742")
if r is not None and r.status_code == 200:
    v = len(re.findall(r"Vaelan", r.text)); a = len(re.findall(r"Acride", r.text))
    print("q4742 EN 页提及: Vaelan=%d Acride=%d" % (v, a))
