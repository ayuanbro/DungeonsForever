# -*- coding: utf-8 -*-
import re
from curl_cffi import requests
PX = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
     "Accept": "text/html,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
     "Referer": "https://www.wowhead.com/"}
def get(u):
    r = requests.get(u, headers=H, proxies=PX, impersonate="chrome110", timeout=40)
    return r.status_code, r.text

for u in ["https://www.wowhead.com/forever/cn/quest=96393",
          "https://www.wowhead.com/forever/cn/search?q=%E9%A2%86%E4%B8%BB%E5%A4%A7%E5%8E%85",
          "https://www.wowhead.com/forever/cn/search?q=Thanes"]:
    st, t = get(u)
    print("===== %s -> %s len=%d" % (u, st, len(t)))
    # 结果块
    m = re.search(r'<div id="search-results".{0,900}', t, re.S)
    if m: print("  RESULT:", re.sub(r"\s+", " ", m.group(0))[:400])
    for pat in (r"zone=(\d+)", r"maps?/(\d+)", r"(领主大厅)", r"(hall[- ]of[- ]thanes)", r"(Thanes)"):
        hits = sorted(set(re.findall(pat, t)))[:8]
        if hits: print("   %-22s %s" % (pat, hits))
