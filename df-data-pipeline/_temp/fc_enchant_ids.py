# -*- coding: utf-8 -*-
"""fc_enchant_ids.py —— Skillwright 第四源：附魔 spellID / createdItem 注入。

输入：客户端 Skillwright/Data/Recipes.lua（无限端 build 1.60.1.70009 生成器产物）
      [333] Enchanting 段，每行行尾注释 = 英文名（与 fc 中间数据 enchants[].name 同源）。
输出：_fc/data/enchant_ids.json = { 英文名: {spell, created} }，并打印与 prof_enchanting.json
      的匹配率。fc_gen.main() 经 inject_enchant_ids() 消费（与 inject_vendor_ids 同模式，
      爬虫重跑后只需重跑本脚本补 join 表）。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SW_RECIPES = (r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns'
              r'\Skillwright\Data\Recipes.lua')
OUT = os.path.join(HERE, '_fc', 'data', 'enchant_ids.json')


def parse_skillwright_enchanting(path):
    """[333] 段 → {英文名: {spell, created}}。行尾注释取英文名。"""
    src = open(path, encoding='utf-8').read()
    m = re.search(r'\[\s*333\s*\]\s*=\s*\{\s*"Enchanting",\s*\{', src)
    if not m:
        sys.exit('fc_enchant_ids: Skillwright [333] Enchanting 段未找到')
    seg = src[m.end():]
    nxt = re.search(r'\n    \[\d+\]', seg)
    if nxt:
        seg = seg[:nxt.start()]
    out = {}
    for line in seg.splitlines():
        rm = re.match(r'\s*\{\s*(\d+)\s*,\s*(\d+)\s*,.*--\s*(.+?)\s*$', line)
        if not rm:
            continue
        spell, created, name = int(rm.group(1)), int(rm.group(2)), rm.group(3)
        if name in out:
            continue  # 重名取首条（同配方名在数据里唯一，防御性）
        out[name] = {'spell': spell, 'created': created if created else None}
    return out


def main():
    sw = parse_skillwright_enchanting(SW_RECIPES)
    prof = json.load(open(os.path.join(HERE, '_fc', 'data', 'prof_enchanting.json'),
                          encoding='utf-8'))
    ench = prof.get('enchants') or []
    hit = miss = 0
    for e in ench:
        j = sw.get(e.get('name'))
        if j:
            hit += 1
            e['_sw'] = j
        else:
            miss += 1
    json.dump(sw, open(OUT, 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    print('Skillwright 附魔 %d 条 · 我们 enchants %d 条 · 命中 %d · 未中 %d'
          % (len(sw), len(ench), hit, miss))
    if miss:
        for e in ench:
            if e.get('name') not in sw:
                print('  未中: %s' % e.get('name'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
