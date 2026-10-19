# -*- coding: utf-8 -*-
import re
from curl_cffi import requests
PX = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
     "Accept": "text/html,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
     "Referer": "https://www.wowhead.com/"}
r = requests.get("https://www.wowhead.com/forever/cn/search?q=Hall+of+Thanes", headers=H, proxies=PX, impersonate="chrome110", timeout=40)
t = r.text
for m in re.finditer("Hall of Thanes", t):
    a, b = max(0, m.start()-400), m.end()+400
    print("---- @%d ----" % m.start())
    print(t[a:b].replace("\n", " ")[:800])
