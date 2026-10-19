# -*- coding: utf-8 -*-
"""生成 DungeonsForever/Core/Data/Data_BossModel.lua（boss 3D 模型显示 id）。

数据：_temp/_bossmodel_lootified.json（_temp/lootified_bosspos.py 同批提取，
按「副本 id + 首领英文名」对齐——名字是掉落表/攻略/钉点共用的唯一连接键）。

背景（2026-10-10）：我方 boss 模型走 SetCreature(npcid)，但掉落表 npcid 列混有
**显示 id**（如怒焰塔拉加曼存 7970 = display，真 npc 11520）且存在同值撞车
（黑石深渊 Bael'Gar / Magmus 都存 12162）⇒ 模型与 boss 不匹配。
本表登记每个首领的精配 CreatureDisplayInfoID，MapUI 优先 SetDisplayInfo(display)，
没登记的首领照旧走 SetCreature(npcid)。

用法：python gen_boss_model.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
SRC = os.path.join(HERE, "_bossmodel_lootified.json")

HEADER = '''local _, ns = ...
ns.BossModelDisplay = {'''

FOOTER = "}\n"


def main():
    model = json.load(open(SRC, encoding="utf-8"))
    lines = [HEADER]
    n = 0
    for did in sorted(model):
        rows = model[did]
        lines.append('    ["%s"] = {\n' % did)
        for en in sorted(rows):
            lines.append('        ["%s"] = %d,\n' % (en.replace('"', '\\"'), rows[en]))
            n += 1
        lines.append("    },\n")
    lines.append(FOOTER)
    out = os.path.join(DF, "Core", "Data", "Data_BossModel.lua")
    open(out, "w", encoding="utf-8", newline="\n").write("".join(lines))
    print("写出", out)
    print("副本 = %d  首领 = %d" % (len(model), n))


if __name__ == "__main__":
    main()
