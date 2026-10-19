# -*- coding: utf-8 -*-
"""Data_ExploreToys.lua（探索页 · 玩具）专用英文对照表（2026-10-04）。

键 = Data_ExploreToys.lua 的 zhCN 原文，值 = 整句人工翻译。
★★ m 子串约束：t 整句的译文必须**包含**它每个 m 标记子串的译文
（PetSplit 在渲染期按译文里的子串切段，缺了 = 可点击段静默消失）。
刷新点坐标一律保留评论原文（wowhead 英文评论区口径）。
"""

TOYS = {
    # ── src 短语 ──
    '守夜人卫兵尸体 · 多位置刷新 最多发现于 乌鸦岭旁17.2,53.8':
        'Night Watch Guard corpse · several spawn points, most often at Raven Hill 17.2,53.8',
    '乌鸦岭旁17.2,53.8': 'Raven Hill 17.2,53.8',  # srcMarks 子串（须含于上行整句）

    # ── step ①（m：守夜人卫兵 → Night Watch Guard，须含于整句译文）──
    '暮色森林里阵亡的「守夜人卫兵」会换地方刷新，出现时小地图弹黄色感叹号；可用 /tar 宏定位':
        'The dead Night Watch Guard in Duskwood moves between spawn points; '
        'a yellow exclamation mark pops on the minimap when it appears; a /tar macro helps you find it',
    '守夜人卫兵': 'Night Watch Guard',

    # ── step ②（四个刷新点标记，全部含于整句译文）──
    '已知刷新点：亮木林 66.1,34.0 · 乌鸦岭旁 17.2,53.8 · 南去荆棘谷路上 47.7,59.4 · 金色村庄边 17,54':
        'Known spawn points: Brightwood Grove 66.1,34.0 · by Raven Hill 17.2,53.8 · '
        'road south to STV 47.7,59.4 · by Jitters 17,54',
    '亮木林 66.1,34.0': 'Brightwood Grove 66.1,34.0',
    '乌鸦岭旁 17.2,53.8': 'by Raven Hill 17.2,53.8',
    '南去荆棘谷路上 47.7,59.4': 'road south to STV 47.7,59.4',
    '金色村庄边 17,54': 'by Jitters 17,54',

    # ── step ③（#q = 客户端任务名占位符，渲染期替换）──
    '右键尸体即完成任务「#q」，火炬（绿色品质）直接进背包；尸体还在时同行玩家可各领一支':
        'Right-click the corpse to complete the quest "#q" and the torch (a green item) goes '
        'straight into your bag; while the corpse remains, everyone in the party can claim one',

    # ── step ④ ──
    '使用可点燃火炬：30 秒冷却、每次燃 5 分钟；进建筑或游泳会熄灭，主城里无法使用':
        'Use to light the torch: 30 sec cooldown, burns for 5 min each time; '
        'it goes out when entering a building or swimming, and cannot be used in major cities',
}
