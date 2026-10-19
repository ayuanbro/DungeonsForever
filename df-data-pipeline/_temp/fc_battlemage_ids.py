# -*- coding: utf-8 -*-
"""战斗法师物品 ID 核实：抓 foreverchanges battle-mage 页原始 HTML，提取 /item= 链接。"""
import re, sys, json
from curl_cffi import requests as creq

URL = "https://foreverchanges.pro/zh-cn/battle-mage"
PROXY = "http://127.0.0.1:7897"

def fetch(url):
    for wait in (0, 15, 25, 35, 45):
        try:
            r = creq.get(url, proxies={"http": PROXY, "https": PROXY},
                         impersonate="chrome", timeout=30)
            if r.status_code == 200:
                return r.text
            print(f"[{r.status_code}] {url}", file=sys.stderr)
        except Exception as e:
            print(f"[ERR] {e}", file=sys.stderr)
        import time; time.sleep(wait + 1)
    return None

html = fetch(URL)
if not html:
    sys.exit("fetch failed")
open("_bm_page.html", "w", encoding="utf-8").write(html)

# 提取所有 item 链接：foreverchanges 的物品引用一般带 href=/forever/cn/item=NNN 或 icon 路径
pairs = []
for m in re.finditer(r'href="(/forever/[a-z\-/]*)?/?(?:cn/)?item=(\d+)"[^>]*>([^<]{0,60})<', html):
    pairs.append((int(m.group(2)), m.group(3).strip()))
# 也抓 icon 引用形态：/icon/inv_sword_05.jpg 旁边的物品块（无 href 时靠名字搜）
seen, uniq = set(), []
for iid, name in pairs:
    if iid not in seen:
        seen.add(iid); uniq.append((iid, name))
print("== href 形态 item 链接 ==")
for iid, name in uniq:
    print(iid, name)

# 兜底：把页面里所有 item= 数字引用都列出来
allids = sorted({int(x) for x in re.findall(r'item=(\d+)', html)})
print("== 页面出现过的全部 item id ==")
print(allids)

# 中文名→ID 需要上下文：抓「名字出现在 NNNN' 之类 JSON 属性」的结构，dump 粗文本供人工核对
ctx = []
for m in re.finditer(r'item=(\d+)', html):
    s = max(0, m.start() - 120); e = min(len(html), m.end() + 120)
    ctx.append((m.group(1), html[s:e].replace("\n", " ")[:240]))
open("_bm_ctx.txt", "w", encoding="utf-8").write("\n----\n".join(f"[{i}] {c}" for i, c in ctx))
print("context saved -> _bm_ctx.txt")
