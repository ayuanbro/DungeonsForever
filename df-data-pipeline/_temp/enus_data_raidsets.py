# -*- coding: utf-8 -*-
"""Core/Data/enUS/Data_RaidSets.lua 专属英文对照表（2026-10-07 加）。

口径与 `enus_data*.py` 各家一致：**只收官方英文原文，不机翻**。
本表只承担「按文件覆盖」层（gen_enus_data.py 的 FILE_SPECIFIC），
故同名中文在别的数据文件里另有语义时不受影响。

★ 本次（2026-10-07）只补 **9 套 Forever 专属套装** 的英文名 + 批次分区标签。
  目录里另有 13 套 T1 套装名与 72 条套装效果文案仍是简体中文 —— 那是**存量缺口**
  （生成器 EXACT 表从来没有团本套装的效果英译），用户 2026-10-07 拍板
  「本次只补 9 套英文名，存量缺口另开一轮专修」，故本表**刻意不补**。

英文名来源：
  · 外部数据挖掘页已直接给出英文原名的，照抄（Rotmender's … / Signet of the Soulless Rider …）；
  · 其余按 wowhead `item-set` 命名惯例 + 同族已定名套装的词干推导。
"""
RS = {
    # ── 批次分区标签（界面上屏）──
    "海加尔峰 T1": "Mount Hyjal T1",
    "Forever 专属": "Forever Exclusive",

    # ── 9 套 Forever 专属套装（本次新增）──
    "迪菲亚执行者的套装": "Defias Enforcer's Raiment",
    "克罗多克战甲": "Krodedor Battlegear",
    "紫罗兰巫师的法衣": "Violet Sorcerer's Raiment",
    "腐疗者的法衣": "Rotmender's Raiment",
    "卡利姆多的祝福": "Kalimdor's Blessing",
    "同谋佳偶": "Conspiring Couple",
    "瘟疫之地骑手": "Plaguelands Rider",
    "加利亚斯适应外衣": "Galia's Adaptive Vestments",
    "祝福板甲": "Blessed Plate",
}
