# -*- coding: utf-8 -*-
"""掉落补充（2026-10-05）：把 fc 改版新页有、我方 Data_DungeonLoot 缺的内容补进 zhCN 源。

补什么（用户拍板）：
  · FC-ITEM-WE-LACK —— 缺的物品行（全部 t=new 无限新增 ⇒ { id, nil, true }），
    按 fc 每来源的列表逐行补在该来源物品表末尾；
  · FC-BOSS-NOT-IN-OUR-LOOT —— 3 个新来源行：
      sm_graveyard  Scorn  瑟克恩  稀有 · 34 级  14693（经典 3 件，掉率取整）
      shadowfang_keep Sever 塞沃尔 稀有 · 25 级  14682（经典 2 件，掉率取整）
      ruins_of_lordaeron Trash mobs 小怪 副本内任意敌人（3 件全 t=new）
不补什么：
  · CHANCE-DIFF（740 条）= 我方取整 vs fc 两位小数的口径差（>1.5 的真实偏差为 0），
    与「坐标不校准」同一口径 —— 现有掉率一律不动；
  · OUR-ITEM-NOT-ON-FC（3 件）保留（fc 没列 ≠ 不存在）。

对齐：只认英文名（fc display 是服务器号，三卫兵共用 11561，不可信）。

用法：python _fc_loot_fill.py   （写盘前先打印计划，--apply 才落盘）
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fc_compare import SLUG2DID, norm, ROOT  # noqa
from _fc_loot_diff2 import extract_bosses, ours_rows, REF  # noqa

LT = os.path.join(ROOT, "Core", "Data", "Data_DungeonLoot.lua")

# 新来源行（fc 无 wowhead 号，号 = 物品页/检索实锤；掉率四舍五入到我方取整口径）
NEW_ROWS = {
    "sm_graveyard": [
        ('        { "Scorn", "瑟克恩", "稀有 · 34 级", "14693", {\n'
         '            { 23169, 38, false },\n'
         '            { 23170, 28, false },\n'
         '            { 23168, 32, false },\n'
         '        } },\n'),
    ],
    "shadowfang_keep": [
        ('        { "Sever", "塞沃尔", "稀有 · 25 级", "14682", {\n'
         '            { 23173, 51, false },\n'
         '            { 23171, 30, false },\n'
         '        } },\n'),
    ],
    "ruins_of_lordaeron": [
        ('        { "Trash mobs", "小怪", "副本内任意敌人", "", {\n'
         '            { 286980, nil, true },\n'
         '            { 286979, nil, true },\n'
         '            { 286978, nil, true },\n'
         '        } },\n'),
    ],
}

ROW_RE = re.compile(
    r'(?P<head>        \{ "(?P<en>(?:[^"\\]|\\.)*)", "(?P<zh>(?:[^"\\]|\\.)*)", '
    r'"(?P<note>(?:[^"\\]|\\.)*)", "(?P<npc>(?:[^"\\]|\\.)*)", \{\n)'
    r'(?P<items>(?:            \{ \d+, (?:nil|[\d.]+), (?:true|false|nil) \},\n)*?)'
    r'(?P<tail>        \} \},\n)')


def fmt_chance(z):
    return "nil" if z is None else str(round(float(z)))


def fmt_flag(t):
    return "true" if t == "new" else "false"


def main():
    apply = "--apply" in sys.argv
    src = open(LT, encoding="utf-8").read()
    out = src
    n_item = 0
    n_row = 0
    for slug, did in sorted(SLUG2DID.items()):
        p = os.path.join(REF, "dg_%s.html" % slug)
        if not os.path.exists(p):
            continue
        fc = extract_bosses(open(p, encoding="utf-8", errors="replace").read())
        if not fc:
            continue
        ours = ours_rows(did)
        if ours is None:
            continue
        by_en = {}
        for r in ours:
            by_en.setdefault(norm(r["en"]), r)
        # 该副本块的范围（用于新行插入定位）
        blk_i = out.find('    ["%s"] = {' % did)
        if blk_i < 0:
            print("!! 找不到副本块", did)
            continue
        blk_end = out.find("\n    },", blk_i)
        # fc 同名对象合并
        merged = {}
        for b in fc:
            en = b.get("english") or ""
            row = by_en.get(norm(en)) or (by_en.get("trashmobs") if b.get("kind") == "trash" else None)
            if row is None:
                continue
            dst = merged.setdefault(row["en"], {})
            for it in b.get("items") or []:
                dst.setdefault(int(it["i"]), it)
        # 1) 补缺物品：逐行定位（在该副本块内按出现顺序找第 n 个匹配行）
        for r in ours:
            miss = [(iid, it) for iid, it in merged.get(r["en"], {}).items() if iid not in r["items"]]
            if not miss:
                continue
            # 定位该行：在块内按英文名找 head
            head_pat = '        { "%s", ' % r["en"].replace('"', '\\"')
            i = out.find(head_pat, blk_i, blk_end)
            if i < 0:
                print("!! 找不到来源行", did, r["en"])
                continue
            tail_i = out.find("        } },\n", i)
            ins = "".join('            { %d, %s, %s },\n'
                          % (iid, fmt_chance(it.get("z")), fmt_flag(it.get("t")))
                          for iid, it in miss)
            out = out[:tail_i] + ins + out[tail_i:]
            n_item += len(miss)
            blk_end += len(ins)
            print("  +物品 %-20s %-26s %s" % (did, r["en"], [iid for iid, _ in miss]))
        # 2) 补新来源行：插在该副本 Trash mobs 行前（没有就插在块尾）
        for row_txt in NEW_ROWS.get(did, []):
            tr = out.find('        { "Trash mobs", ', blk_i, blk_end)
            pos = tr if tr >= 0 else out.find("\n    },", blk_i) + 1
            out = out[:pos] + row_txt + out[pos:]
            n_row += 1
            blk_end += len(row_txt)
            print("  +来源行 %-20s %s" % (did, row_txt.split('"')[1]))
    print("计划：补物品 %d 行，新来源 %d 行，apply=%s" % (n_item, n_row, apply))
    if apply:
        open(LT, "w", encoding="utf-8", newline="\n").write(out)
        print("已写出", LT)
    else:
        print("（dry-run，--apply 落盘）")


if __name__ == "__main__":
    main()
