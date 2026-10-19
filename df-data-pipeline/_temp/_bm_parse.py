# -*- coding: utf-8 -*-
"""解析 battle-mage 页 Next.js 数据层里的物品 JSON。"""
import re, json, sys

html = open("_bm_page.html", encoding="utf-8").read()

# 物品对象形如 \"name\":\"X\",\"quality\":1,\"ilvl\":10,\"icon\":\"Y\",\"lines\":[...]
pat = re.compile(r'\\"name\\":\\"(.+?)\\",\\"quality\\":(\d+),\\"ilvl\\":(\d+),\\"icon\\":\\"(.+?)\\",\\"lines\\":\[(.*?)\]\]', re.S)
rows = []
for m in pat.finditer(html):
    name, q, ilvl, icon, lines = m.groups()
    rows.append((name, int(q), int(ilvl), icon, lines[:200]))

seen = set()
for r in rows:
    if r[0] in seen:
        continue
    seen.add(r[0])
    print(json.dumps(r[:4], ensure_ascii=False), "|", r[4].replace("\\\\", "")[:110])
print(f"== {len(seen)} uniq / {len(rows)} total")
