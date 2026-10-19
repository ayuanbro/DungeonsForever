# -*- coding: utf-8 -*-
import io, json, re, sys
sys.stdout.reconfigure(encoding="utf-8")
cache = json.load(io.open("_enus_wowhead.json", encoding="utf-8"))
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}
UNI = re.compile(r"\\u([0-9a-fA-F]{4})")
ANCHOR = re.compile(r"\[url=[^\]]*?npc=(\d+)\]([^[]+?)\[/url\]")
r = requests.get("https://www.wowhead.com/classic/cn/quest=739", headers=HDRS,
                 proxy="http://127.0.0.1:7897", impersonate="chrome", timeout=20)
print("status", r.status_code)
txt = UNI.sub(lambda m: chr(int(m.group(1), 16)), r.text).replace("\\/", "/")
print("开始/结束锚:", re.findall(r"(?:开始|结束)于：?\s*\[url=[^\]]*?npc=(\d+)\]([^[]+?)\[/url\]", txt)[:6])
print("全部锚:", ANCHOR.findall(txt)[:8])
