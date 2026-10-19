# -*- coding: utf-8 -*-
"""wowhead 评论仲裁 3 本坐标分歧书（走 7897 代理 + Chrome 指纹）"""
import re, io, sys
from curl_cffi import requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BOOKS = [
    (209849, "Crimes Against Anatomy"),
    (228135, "A Study of the Light"),
    (209850, "Runes of the Sorcerer-Kings"),
    (215683, "Geomancy (复核)"),
]
PROXY = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

for iid, name in BOOKS:
    url = f"https://www.wowhead.com/classic/item={iid}#comments"
    try:
        r = requests.get(url, proxies=PROXY, impersonate="chrome", timeout=30)
    except Exception as e:
        print(f"== {name} ({iid}): 请求失败 {e}")
        continue
    print(f"== {name} ({iid}): HTTP {r.status_code}")
    if r.status_code != 200:
        continue
    html = r.text
    # 评论里抓坐标片段与对象引用
    hits = set()
    for m in re.finditer(r"(\d{1,2}\.\d)\s*[,，&]\s*(\d{1,2}\.\d)", html):
        hits.add(f"{m.group(1)}, {m.group(2)}")
    objs = set(re.findall(r"/classic/object=(\d+)\"[^>]*>([^<]{3,60})<", html))
    print("  坐标片段:", sorted(hits)[:20])
    for oid, oname in list(objs)[:8]:
        print(f"  关联对象 object={oid} {oname.strip()}")
    print()
