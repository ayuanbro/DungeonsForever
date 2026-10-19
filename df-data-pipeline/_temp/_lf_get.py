# -*- coding: utf-8 -*-
"""下载 community listfile（走代理），本地存一份用于盘点。"""
import os
from curl_cffi import requests
PX = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
U = "https://github.com/wowdev/wow-listfile/releases/latest/download/community-listfile.csv"
OUT = r"D:/workspace/DungeonsForever/_temp/_community-listfile.csv"
if os.path.exists(OUT) and os.path.getsize(OUT) > 10_000_000:
    print("已存在", os.path.getsize(OUT)); raise SystemExit
try:
    r = requests.get(U, proxies=PX, impersonate="chrome110", timeout=180, allow_redirects=True)
    print("status", r.status_code, "len", len(r.content))
    if r.status_code == 200 and len(r.content) > 5_000_000:
        open(OUT, "wb").write(r.content)
        print("saved", os.path.getsize(OUT))
    else:
        print("body head:", r.text[:300])
except Exception as e:
    print("ERR", e)
