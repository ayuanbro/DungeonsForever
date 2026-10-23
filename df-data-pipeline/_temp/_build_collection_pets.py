# -*- coding: utf-8 -*-
"""组装 Data_CollectionPets.lua 的新增行（43 只分类页宠物）。
输入：_companions_names.json / whb_companions_cat.html（图标）/
      whb_<id>.html（来源区块标记）。
输出：_companions_rows.lua 片段（人工审读后并入数据文件）。
"""
import json
import re

HERE = "_companions"
NAMES = json.load(open("_companions_names.json", encoding="utf-8"))
KNOWN = {13582, 13583, 13584, 268109, 275682, 280456, 280614, 282047}

# 分类页 id→图标 slug
raw = open("whb_companions_cat.html", encoding="utf-8").read()
icons = {}
for tr in re.findall(r"<tr[^>]*>.*?</tr>", raw, re.S):
    m = re.search(r'href="[^"]*?[/?]item[=](\d+)', tr)
    if not m:
        continue
    iid = int(m.group(1))
    ic = re.search(r"icons/(?:medium|large)/([a-z0-9_-]+)\.(?:jpg|png)", tr)
    if ic:
        icons[iid] = ic.group(1)

# 来源区块 → 类型短语
VENDOR = "商人出售"
DROP = "怪物掉落"
PENDING = "获取方式待补充"


def display_of(iid):
    """直接扫已存 HTML 取 data-mv-display-id（权威）；缺失返回空串。"""
    try:
        raw = open("whb_%s.html" % iid, encoding="utf-8").read()
    except FileNotFoundError:
        return ""
    m = re.search(r'data-mv-display-id="(\d+)"', raw)
    return m.group(1) if m else ""


def source_of(iid):
    try:
        raw = open("whb_%s.html" % iid, encoding="utf-8").read()
    except FileNotFoundError:
        return PENDING
    if "Vendor Locations" in raw:
        return VENDOR
    if "Dropped by" in raw:
        return DROP
    return PENDING


rows = []
for iid_s in sorted(NAMES, key=int):
    iid = int(iid_s)
    if iid in KNOWN:
        continue
    disp = display_of(iid_s)
    src = source_of(iid_s)
    if src == PENDING:
        step = "获取方式待补充"
    elif src == VENDOR:
        step = "商人出售获得，具体商人与位置待补充"
    else:
        step = "怪物掉落获得，具体掉落来源待补充"
    icon = icons.get(iid, "")
    lines = []
    lines.append("    [%d] = {" % (len(rows) + 5))  # [1]-[4] 为商城宠物
    lines.append('        %d, "%s", nil, "unknown",' % (iid, icon))
    lines.append('        false, false, false, "%s",' % src)
    if disp:
        lines.append("        __display = %s," % disp)
    lines.append("        {")
    lines.append('            { t = "%s" },' % step)
    lines.append("        },")
    lines.append("    },")
    rows.append((iid, NAMES[iid_s], disp or "-", src, "\n".join(lines)))

with open("_companions_rows.lua", "w", encoding="utf-8") as f:
    for iid, nm, disp, src, block in rows:
        f.write(block + "\n")

print("共 %d 行" % len(rows))
nodisp = [iid for iid, nm, disp, src, b in rows if disp == "-"]
vendor_n = sum(1 for r in rows if r[3] == VENDOR)
print("无 displayId: %s" % ",".join(str(i) for i in nodisp))
print("商人出售 %d / 待补充 %d" % (vendor_n, len(rows) - vendor_n))
for iid, nm, disp, src, b in rows:
    print("%s %-14s disp=%-7s %s" % (iid, nm, disp, src))
