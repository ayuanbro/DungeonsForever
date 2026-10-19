# -*- coding: utf-8 -*-
"""正则解析 WTF descScan rows（多行 savedvars 格式）→ 缺描述清单。"""
import json
import os
import re
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
WTF = r"D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
text = open(WTF, encoding="utf-8").read()
i = text.find('["descScan"]')
assert i >= 0, "descScan not found"
body = text[i:]

ENT = re.compile(
    r'\{\s*(\d+)\s*,\s*("(?:[^"\\]|\\.)*"|nil)?\s*,?\s*("(?:[^"\\]|\\.)*"|nil)?\s*,?\s*\}',
    re.S)
items = []
for m in ENT.finditer(body):
    sid = int(m.group(1))
    nm = None if (not m.group(2) or m.group(2) == "nil") else m.group(2)[1:-1]
    ds = None if (not m.group(3) or m.group(3) == "nil") else m.group(3)[1:-1]
    items.append((sid, nm, ds))
print("parsed =", len(items))

def unesc(s):
    return s.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')

items = [(sid, unesc(nm) if nm else None, unesc(ds) if ds else None) for sid, nm, ds in items]

no_desc = sorted([sid for sid, nm, ds in items if not ds])
has_desc = [sid for sid, nm, ds in items if ds]
no_name = [sid for sid, nm, ds in items if not nm]
print("有描述 =", len(has_desc), " 无描述 =", len(no_desc), " 连名字都没有 =", len(no_name))

id_map = json.load(open(os.path.join(HERE, "_id_map.json"), encoding="utf-8"))
by_dun = OrderedDict()
for sid in no_desc:
    for e in id_map.get(str(sid), []):
        by_dun.setdefault(e["dungZh"], OrderedDict()).setdefault(
            e["bossZh"] or e["bossEn"], []).append(sid)

lines = []
for dzh, bb in by_dun.items():
    lines.append("## %s" % dzh)
    for bz, sids in bb.items():
        lines.append("  %s：%s" % (bz, "、".join(map(str, sids))))
out = "\n".join(lines)
open(os.path.join(HERE, "_desc_missing_by_dungeon.txt"), "w", encoding="utf-8").write(out)
json.dump({"has_desc": has_desc, "no_desc": no_desc, "no_name": no_name},
          open(os.path.join(HERE, "_desc_scan_summary.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print()
print(out[:2500])
