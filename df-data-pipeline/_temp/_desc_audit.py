# -*- coding: utf-8 -*-
"""首领技能「描述可得性」审计（可复用）。

口径：以本地 wowhead 页面缓存（_temp/**/*.html 里 WH.Gatherer.addData(6,…) 块）
为离线真源，逐条判定技能表里每个 id 的名字/描述在数据侧是否存在，
从而区分三类：
  A 有名字 + 有描述   → 数据侧有料（本地 ns.SpellTips 覆盖的就是这批）
  B 有名字 + 描述为空 → wowhead 也没有 → 暴雪 DBC 大概率没写
  C 中文页缺条目      → 只有英文页（抓取覆盖缺口，可联网补）

用法：python _temp/_desc_audit.py [--write]
      --write 同时落一份 _temp/_desc_audit.txt
"""
import json, re, glob, os, sys

T = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(T), "Core", "Data", "Data_BossSkills.lua")
BLOCK = re.compile(r"WH\.Gatherer\.addData\(\s*6\s*,\s*\d+\s*,\s*(\{.*?\})\s*\)\s*;", re.S)

out = []
def P(*a):
    s = " ".join(str(x) for x in a)
    out.append(s)
    print(s)

# ---- 技能表 ----
src = open(DATA, encoding="utf-8").read()
all_ids = sorted(set(int(x) for x in re.findall(r'\{ "", "", (\d+)', src)))
tips_ids = set(int(x) for x in re.findall(r'^\s*\[(\d+)\] = \{', src, re.M))
cust = [i for i in all_ids if i > 1000000]

# ---- 挖缓存：分语言 ----
zh, en = {}, {}
n_files = n_block = 0
for f in sorted(set(glob.glob(os.path.join(T, "*.html"))
                    + glob.glob(os.path.join(T, "**", "*.html"), recursive=True))):
    n_files += 1
    try:
        s = open(f, encoding="utf-8", errors="ignore").read()
    except Exception:
        continue
    if "Gatherer.addData(6" not in s:
        continue
    m = BLOCK.search(s)
    if not m:
        continue
    n_block += 1
    try:
        obj = json.loads(m.group(1))
    except Exception:
        continue
    if not isinstance(obj, dict):
        continue
    for k, v in obj.items():
        if isinstance(v, dict) and k.isdigit():
            i = int(k)
            if "name_zhcn" in v:
                zh.setdefault(i, v)
            if "name_enus" in v:
                en.setdefault(i, v)

P("cache: html=%d  gatherer-block=%d  zh-entry=%d  en-entry=%d"
  % (n_files, n_block, len(zh), len(en)))
P("table: ids=%d (custom>1e6=%d)  SpellTips=%d  orphan-tips=%s"
  % (len(all_ids), len(cust), len(tips_ids), sorted(tips_ids - set(all_ids))))
P("")

A, B, C = [], [], []
for i in all_ids:
    v = zh.get(i)
    if v is None:
        C.append(i)
        continue
    (A if (v.get("description_zhcn") or "").strip() else B).append(i)

P("A 有名字+有描述 : %d" % len(A))
P("B 有名字+描述空  : %d" % len(B))
P("C 中文页缺条目   : %d" % len(C))
P("")
P("== B 清单（wowhead 也无描述）==")
for i in B:
    P("   %-9d %-24s tips=%s" % (i, zh[i].get("name_zhcn"), "Y" if i in tips_ids else "-"))
P("")
P("== C 清单（英文页状态）==")
for i in C:
    v = en.get(i)
    if v is None:
        P("   %-9d (en 也没有)" % i)
    else:
        d = (v.get("description_enus") or "").strip()
        P("   %-9d en=%-22s enDesc=%s" % (i, v.get("name_enus"), ("有" if d else "空")))
P("")
P("== 自定义法术（>1e6）==")
for i in cust:
    v = zh.get(i) or {}
    P("   %-9d %-16s desc=%s" % (i, v.get("name_zhcn"), "有" if (v.get("description_zhcn") or "").strip() else "空"))

if "--write" in sys.argv:
    open(os.path.join(T, "_desc_audit.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n-> _temp/_desc_audit.txt")
