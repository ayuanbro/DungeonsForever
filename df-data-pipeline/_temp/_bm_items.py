# -*- coding: utf-8 -*-
"""提取 battle-mage 页 Next.js 数据层的 items 映射（键 = itemID）。"""
import re, json

html = open("_bm_page.html", encoding="utf-8").read()

# 定位 items 映射起点，然后按引号转义的大括号做括号配对
key = '\\"items\\":{'
i = html.find(key)
if i < 0:
    raise SystemExit("items map not found")
start = i + len(key) - 1  # 指向 {
depth, j, instr, esc = 0, start, False, False
while j < len(html):
    c = html[j]
    if esc:
        esc = False
    elif c == "\\":
        esc = True
    elif c == '"':
        instr = not instr
    elif not instr:
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
    j += 1
raw = html[start:j + 1]
# 这里是双重转义形态，先反转义一层再解 JSON
s = raw.replace('\\\\', '\x00').replace('\\"', '"').replace('\x00', '\\')
data = json.loads(s)
print(f"== {len(data)} items ==")
for iid, v in data.items():
    name = v.get("name", "?")
    q, ilvl = v.get("quality"), v.get("ilvl")
    print(iid, "|", name, "| q", q, "| ilvl", ilvl, "|", v.get("icon", ""))
    for ln in v.get("lines", [])[:6]:
        print("   ", ln.replace("\t", "")[:90])
open("_bm_items.json", "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
