# -*- coding: utf-8 -*-
# 验证：主界面「要准备的材料」按首次使用等级排序（模拟 ProfessionUI 新逻辑）
import re

base = r"D:/workspace/DungeonsForever/Core/Data/enUS"
lv_txt = open(base + r"/Data_ProfLeveling.lua", encoding="utf-8").read()
rc_txt = open(base + r"/Data_ProfRecipes.lua", encoding="utf-8").read()

def block(src, slug):
    i = src.index('["%s"] = {' % slug)
    depth = 1  # 外层表自身的开括号已计入
    for j in range(i + len('["%s"] = {' % slug), len(src)):
        if src[j] == "{": depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
    return src[i:]

for slug in ("leatherworking", "alchemy"):
    b = block(lv_txt, slug)
    steps = [(int(a), int(b2), int(r), int(c)) for a, b2, r, c in
             re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}", b)]
    sm = re.search(r"shopping\s*=\s*\{(.*?)\n\s*\}", b, re.S)
    shop = [(int(a), int(n)) for a, n in re.findall(r"\{\s*(\d+),\s*(\d+)\s*\}", sm.group(1))]
    # 配方行材料
    rb = block(rc_txt, slug)
    DESC = r'"(?:[^"\\]|\\.)*"'
    mats = {}
    for m in re.finditer(r'^\s*\{\s*(\d+),\s*(\d+),\s*1,\s*"[^"]*",\s*"[^"]*",\s*' + DESC +
                         r',\s*\d+,\s*\d+,\s*\d+,\s*\d+,\s*(?:true|false),\s*'
                         r'(\{\s*(?:\{[^{}]*\},?\s*)+\})', rb, re.M):
        rid = int(m.group(1))
        lst = []
        for mm in re.finditer(r"\{\s*(\d+),\s*(\d+)\s*\}", m.group(3)):
            lst.append(int(mm.group(1)))
        mats[rid] = lst
    print("[debug] %s: mats 行数=%d 示例2152=%s" % (slug, len(mats), mats.get(2152)))

    first_at = {}
    for a, b2, r, c in steps:
        for it in mats.get(r, []):
            if it not in first_at or a < first_at[it]:
                first_at[it] = a

    def key(s):
        return (first_at.get(s[0], 10**9), -s[1], s[0])

    print("=== %s ===" % slug)
    print("原始顺序:")
    for s in shop:
        print("   %-6d x%-4d 首用=%s" % (s[0], s[1], first_at.get(s[0], "∞")))
    print("排序后:")
    for s in sorted(shop, key=key):
        print("   %-6d x%-4d 首用等级=%s" % (s[0], s[1], first_at.get(s[0], "∞")))
    print()
