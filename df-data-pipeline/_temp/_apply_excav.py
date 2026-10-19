# -*- coding: utf-8 -*-
"""挖掘场：湿地 —— 掉落 / 任务 / 攻略 三块补齐（2026-10-02）。

数据源：
  掉落 = foreverchanges.pro /dungeons/zh-cn/excavation-site.json（9 件，t=new → 掉率 nil + 新增旗标）
         boss npc id：盐脊 260322 / 暗齿 260325 / 高地惊魂 9010 / 遗迹守护者 260326
         （wowhead /forever/npc=260322 等有页者采信 wowhead；高地惊魂 wowhead 无页 → 采信站点 9010）
  任务 = wowhead /forever/quest=<id> 八页 infobox + g_quests JSON（xp/奖励/难度阈值/Start-End NPC）
  攻略 = wowhead 指南页（beta 已开放、机制未公开）+ fc 页概览

幂等：每个锚点命中数必须为 1 才动手；已应用态直接报 [SAME]。
"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = r'D:/workspace/DungeonsForever'
CHECK = r'D:/workspace/DungeonsForever/_temp/df_dungeon_check.py'


def load(p):
    with open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def save(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def sub1(text, pat, repl, tag, flags=0):
    n = len(re.findall(pat, text, flags))
    if n != 1:
        raise SystemExit('[ABORT] %s 锚点命中 %d 次（应为 1）' % (tag, n))
    return re.sub(pat, repl, text, count=1, flags=flags)


# ── 1. Data_DungeonLoot.lua ────────────────────────────────────────────────
LOOT_OLD = '''    ["excavation_wetlands"] = {
        { "Saltspine", "盐脊", "", "", {
        } },
        { "Shadetooth", "暗齿", "", "", {
        } },
        { "Highland Horror", "高地惊魂", "", "", {
        } },
        { "Relic Guardian", "遗物守护者", "", "", {
        } },
    },'''
LOOT_NEW = '''    ["excavation_wetlands"] = {
        { "Saltspine", "盐脊", "", "260322", {
            { 273022, nil, true },
            { 273023, nil, true },
            { 273024, nil, true },
        } },
        { "Shadetooth", "暗齿", "", "260325", {
            { 273027, nil, true },
            { 273025, nil, true },
        } },
        { "Highland Horror", "高地惊魂", "", "9010", {
            { 270180, nil, true },
        } },
        { "Relic Guardian", "遗物守护者", "", "260326", {
            { 273028, nil, true },
            { 270865, nil, true },
            { 273030, nil, true },
        } },
    },'''
GELI_OLD = '''        { "Gelihast", "格里哈斯特", "", "6243", {
            { 6906, 44, false },'''
GELI_NEW = '''        { "Gelihast", "格里哈斯特", "", "6243", {
            { 273840, nil, true },
            { 6906, 44, false },'''

p = ROOT + '/Core/Data/Data_DungeonLoot.lua'
s = load(p)
if LOOT_OLD in s:
    s = sub1(s, re.escape(LOOT_OLD), LOOT_NEW.replace('\\', r'\\'), 'loot-excavation')
    s = sub1(s, re.escape(GELI_OLD), GELI_NEW.replace('\\', r'\\'), 'loot-gelihast')
    save(p, s)
    print('[OK] Data_DungeonLoot.lua 挖掘场 4 来源 9 件 + 黑暗深渊格里哈斯特 +273840')
else:
    print('[SAME] Data_DungeonLoot.lua（挖掘场段已是新形态，核对 Gelihast）')
    if GELI_OLD in s:
        s = sub1(s, re.escape(GELI_OLD), GELI_NEW.replace('\\', r'\\'), 'loot-gelihast')
        save(p, s)
        print('[OK] Data_DungeonLoot.lua 黑暗深渊格里哈斯特 +273840')

# ── 2. Data_Dungeons.lua 计数 ──────────────────────────────────────────────
p = ROOT + '/Core/Data/Data_Dungeons.lua'
s = load(p)
changed = False
if '{ id = "excavation_wetlands"' in s and not re.search(r'\{ id = "excavation_wetlands"[^\n]*dropCount = 9,', s):
    s = sub1(s, r'(\{ id = "excavation_wetlands"[^\n]*?dropCount = )nil', r'\g<1>9', 'dg-exc-count')
    changed = True
if '{ id = "blackfathom_deeps"' in s and not re.search(r'\{ id = "blackfathom_deeps"[^\n]*dropCount = 36,', s):
    s = sub1(s, r'(\{ id = "blackfathom_deeps"[^\n]*?dropCount = )35', r'\g<1>36', 'dg-bfd-count')
    changed = True
if changed:
    save(p, s)
    print('[OK] Data_Dungeons.lua 挖掘场 dropCount 9 / 黑暗深渊 dropCount 36')
else:
    print('[SAME] Data_Dungeons.lua 计数已是新值')

# ── 3. Data_DungeonQuests.lua ──────────────────────────────────────────────
QUESTS_BLOCK = '''    ["excavation_wetlands"] = {
        { 95772, nil, 24, 31, "多林·桑布雷德", "红脊山 - 湖畔镇 25.6,46.6", nil, false, nil, nil, "到维尔加挖掘场一带寻找多林·桑布雷德的兄弟戴温。", "戴温随勘探队进了挖掘场，之后能在副本内他的遗体上接到后续任务。", {{24,1}, {27,2}, {29,3}, {34,4}, {39,5}}, nil, nil, 956, "多林·桑布雷德", { xp = 3150 } },
        { 98815, nil, 24, 28, "詹姆斯·哈洛兰", "湿地 - 米奈希尔港 8,55", "日常供货", false, {469}, nil, "把 4 张灌木丛迅猛龙皮交给米奈希尔港的制皮匠詹姆斯·哈洛兰。", "迅猛龙皮由挖掘场的迅猛龙类掉落；先做完哈洛兰的「日常供货」才能接本任务。", {{24,2}, {26,3}, {31,4}, {36,5}}, nil, nil, 2094, "詹姆斯·哈洛兰", { xp = 1150, money = 1200, rep = { {72, 50, "暴风城"} } } },
        { 95646, "A", 24, 31, "绿色守卫者雷希耶尔", "湿地 56.2,40.6", nil, false, nil, {271667, 271670, 271664}, "在挖掘场杀一只高地惊魂，把它的根核带给湿地的雷希耶尔。", "可怕的根核（#270180）由副本内的高地惊魂掉落，三选一奖励。", {{24,1}, {27,2}, {29,3}, {34,4}, {39,5}}, {270180}, nil, 1244, "绿色守卫者雷希耶尔", { xp = 3150 } },
        { 95647, "A", 24, 31, "凯特林·格拉斯曼", "灰谷", "寻找凯特林", false, {95737}, nil, "在挖掘场找到阿尔丁·格拉斯曼，弄清他遭遇了什么。", "链从灰谷蓝纳（#3970）的「寻找凯特林」开始。", {{24,1}, {27,2}, {29,3}, {34,4}, {39,5}}, nil, nil, 1480, "凯特林·格拉斯曼", { xp = 2500 } },
        { 95795, "A", 24, 31, nil, nil, nil, true, nil, {271769, 271768}, "把戴温的命运带回湖畔镇告诉多林·桑布雷德。", "在副本内戴温的遗体上直接接取，腰甲二选一。", {{24,1}, {27,2}, {29,3}, {34,4}, {39,5}}, nil, nil, nil, nil, { xp = 3150 } },
        { 95697, "H", 24, 31, nil, "奥格瑞玛", nil, false, nil, {250185, 250077}, "进挖掘场带回 4 块灌木丛迅猛龙肉。", "肉（#271100）由副本内迅猛龙类掉落；发布者在奥格瑞玛，暂无确证 NPC。奖励含烹饪食谱。", {{24,1}, {27,2}, {29,3}, {34,4}, {39,5}}, {271100}, nil, nil, nil, { xp = 3150 } },
        { 95664, "H", 24, 31, nil, nil, nil, false, nil, nil, "把泰坦圣物带到雷霆崖长者高地，找能鉴定它的人。", "打完尾王遗迹守卫者后拾取泰坦圣物（#270865），拾取即开启本任务；beta 实测上交后物品可能消失。", {{24,1}, {27,2}, {29,3}, {34,4}, {39,5}}, {270865}, nil, nil, nil, { xp = 630 } },
        { 95810, "A", 24, 31, nil, nil, nil, false, nil, nil, "把泰坦圣物带给湿地的勘察员维尔加。", "拾取泰坦圣物（#270865）开启；联盟方交给维尔加挖掘场的勘察员维尔加（#1077）。", {{24,1}, {27,2}, {29,3}, {34,4}, {39,5}}, {270865}, nil, nil, nil, { xp = 630 } },
    },
'''
ANCHOR_NEXT = '    ["blackfathom_deeps"] = {'
PRE469 = '    [469] = { npc = "艾纳尔·石握", lv = 18 },\n'
PRE469_AFTER = '    [707] = { npc = "勘察员塔伯斯·雷矛", lv = 30 },'
PRE95737 = '    [95737] = { npc = "蓝纳", lv = 24 },\n'
PRE95737_AFTER = '    [8421] = { 8419, npc = "伊普斯", lv = 50 },'

p = ROOT + '/Core/Data/Data_DungeonQuests.lua'
s = load(p)
acts = []
if '["excavation_wetlands"] = {' not in s:
    s = sub1(s, re.escape(ANCHOR_NEXT), QUESTS_BLOCK + ANCHOR_NEXT, 'quests-block')
    acts.append('+挖掘场 8 任务')
if PRE469 not in s:
    s = sub1(s, re.escape(PRE469_AFTER), PRE469 + PRE469_AFTER, 'pre-469')
    acts.append('+PreExtra[469]')
if PRE95737 not in s:
    s = sub1(s, re.escape(PRE95737_AFTER), PRE95737_AFTER + '\n' + PRE95737, 'pre-95737')
    acts.append('+PreExtra[95737]')
if acts:
    save(p, s)
    print('[OK] Data_DungeonQuests.lua ' + ' / '.join(acts))
else:
    print('[SAME] Data_DungeonQuests.lua 已有全部条目')

# ── 4. Data_DungeonGuide.lua 文案 ──────────────────────────────────────────
GUIDE_EDITS = [
    ('"副本 24-29 级（Group Finder 列为 26-33），beta 暂未开放，目前没有任何战斗录像 —— 本攻略后续会随开放补充。",',
     '"副本 24-29 级（Group Finder 列为 26-33），beta 已开放 —— 但 boss 机制仍没有公开的实测资料，打法后续随测试补充。",'),
    ('text = "Inside, the creatures made for the dungeon are raptors (Thicket Lurker, Thicket Hunter, Thicket Matriarch), crocolisks, Highland spiders, a bog beast (Highland Creeper) and turtles — their names match the four areas, so expect themed packs in each zone." },',
     'text = "副本内的生物与四个区域一一对应：迅猛龙（灌木丛潜行者、灌木丛猎人、灌木丛女家长）、鳄鱼、高地蜘蛛、一只沼泽兽（高地爬行者）和陆行龟 —— 每个区域都会遇到对应主题的成组怪。" },'),
    ('text = "数据文件中的首个 boss：一只白色鳄鱼（野兽精英）。还没有人见过这场战斗 —— 副本暂未在 beta 中开放，也没有任何视频拍到过内部。外观信息来自它的模型；正式开放前名称、顺序与打法都可能变化。" },',
     'text = "白色鳄鱼形态的首领（野兽精英）。beta 已开放本副本，但主流攻略与战斗录像尚未给出它的具体机制，打法待补。" },'),
    ('text = "数据文件中的第二个 boss：一只巨大的紫色迅猛龙（野兽精英）。和本副本其余 boss 一样，还没有人打过它 —— beta 尚未开放该副本。名称、顺序与打法都可能有变。" },',
     'text = "巨大的紫色迅猛龙（野兽精英）。机制同样没有公开资料，以 beta 实测为准。" },'),
    ('text = "数据文件中的第三场战斗：一只沼泽兽，外形酷似悲伤沼泽的泥沼领主（元素精英）。它是文件中晚于其余三只加入的，排在第三战。目前还没有任何战斗视频。" },',
     'text = "沼泽兽外形的首领（元素精英），也是联盟任务「在挖掘场杀一只高地惊魂」的猎杀目标。战斗机制暂无公开资料。" },'),
    ('text = "最终 boss：一尊灰色石巨人（元素精英）。击杀它才算完成本副本的 Legacy 挑战。暴雪称副本的危险来自「失控的泰坦构造体」，而它是四者中唯一的构造体。战斗本身尚未有人见过。" },',
     'text = "最终 boss：一尊灰色石巨人（元素精英），击杀它才算完成本副本的 Legacy 挑战。它掉落的泰坦圣物同时开启联盟与部落的圣物上交任务。机制待补。" },'),
]
p = ROOT + '/Core/Data/Data_DungeonGuide.lua'
s = load(p)
acts = []
for old, new in GUIDE_EDITS:
    if new in s and old not in s:
        continue
    if old in s:
        n = s.count(old)
        if n != 1:
            raise SystemExit('[ABORT] guide 锚点命中 %d 次: %s...' % (n, old[:40]))
        s = s.replace(old, new, 1)
        acts.append(old[:18])
if acts:
    save(p, s)
    print('[OK] Data_DungeonGuide.lua 更新 %d 处' % len(acts))
else:
    print('[SAME] Data_DungeonGuide.lua 文案已是新版')

# ── 5. df_dungeon_check.py 断言同步 ────────────────────────────────────────
s = load(CHECK)
acts = []
if 'len(rows) == 1841' in s:
    s = s.replace('len(rows) == 1841', 'len(rows) == 1851', 1)
    acts.append('物品行 1841→1851')
if 'elseif d.id == "excavation_wetlands" then noDropDg = d' in s:
    s = s.replace('elseif d.id == "excavation_wetlands" then noDropDg = d',
                  'elseif d.id == "city_of_dalaran" then noDropDg = d', 1)
    acts.append('noDrop 样例 挖掘场→达拉然城')
if 'shownHdr == 4' in s:
    s = s.replace('shownHdr == 4', 'shownHdr == 9', 1)
    acts.append('未公布掉落标题 4→9')
if 'noteRows == 4' in s:
    s = s.replace('noteRows == 4', 'noteRows == 9', 1)
    acts.append('暂无掉落行 4→9')
if '-- 有名单、掉落未公布（挖掘场：湿地 4 个来源）' in s:
    s = s.replace('-- 有名单、掉落未公布（挖掘场：湿地 4 个来源）',
                  '-- 有名单、掉落未公布（达拉然城 9 个来源）', 1)
if 'ck("未公布掉落：4 个来源标题", shownHdr == 9, shownHdr)' in s:
    s = s.replace('ck("未公布掉落：4 个来源标题", shownHdr == 9, shownHdr)',
                  'ck("未公布掉落：9 个来源标题", shownHdr == 9, shownHdr)', 1)
if 'ck("未公布掉落：4 行「暂无掉落数据」", noteRows == 9, noteRows)' in s:
    s = s.replace('ck("未公布掉落：4 行「暂无掉落数据」", noteRows == 9, noteRows)',
                  'ck("未公布掉落：9 行「暂无掉落数据」", noteRows == 9, noteRows)', 1)
if 'ck("任务清单已装载（28 个副本有数据）", nDgQ == 28, nDgQ)' in s:
    s = s.replace('ck("任务清单已装载（28 个副本有数据）", nDgQ == 28, nDgQ)',
                  'ck("任务清单已装载（29 个副本有数据）", nDgQ == 29, nDgQ)', 1)
    acts.append('任务副本数 28→29')
if acts:
    save(CHECK, s)
    print('[OK] df_dungeon_check.py ' + ' / '.join(acts))
else:
    print('[SAME] df_dungeon_check.py 已同步')
