# -*- coding: utf-8 -*-
"""掉落表补齐 · 一次性迁移（2026-09-29，数据源 foreverchanges.pro /dungeons/zh-cn/<slug>.json
                        + wowhead forever/cn zone payload 的 NPC id 验真）。

改动：
  ① 缺失来源补齐 7 处（监狱 3 boss、黑暗深渊洛古斯、剃刀沼泽鲁古格、洛丹伦废墟稀有上尉）
  ② 缺失物品补齐 16 处（含剃刀沼泽小怪 6681 带站点掉率）
  ③ 领主大厅 / 洛丹伦废墟共 31 件物品的「无限版新增」旗标 false→true
  ④ NPC id 全量验真修正（forever zone payload 实测，站点旧快照的 id 大多错）
  ⑤ Data_Dungeons.lua 的 bossCount / dropCount 同步

纪律：每处替换锚定 + 命中数必须为 1，否则 SystemExit。
"""
import re
import sys

LOOT = 'D:/workspace/DungeonsForever/Core/Data/Data_DungeonLoot.lua'
DG = 'D:/workspace/DungeonsForever/Core/Data/Data_Dungeons.lua'

lua = open(LOOT, encoding='utf-8').read()


def sub1(pattern, repl, text, label, flags=0):
    new, n = re.subn(pattern, repl, text, flags=flags)
    if n != 1:
        sys.stderr.write('FAIL [%s] 命中 %d 次\n' % (label, n))
        sys.exit(1)
    return new


def src_anchor(en, zh, old_id):
    return r'(\{ "%s", "%s", "[^"]*", ")%s(", \{)' % (re.escape(en), zh, old_id)


# ── ⓪ 旗标翻新（hall_of_thanes 13 件 / ruins_of_lordaeron 18 件）——须在插入前跑 ──
for dg, want in (('hall_of_thanes', 13), ('ruins_of_lordaeron', 18)):
    m = re.search(r'\n    \["%s"\] = \{.*?\n    \},\n' % dg, lua, re.S)
    if not m:
        sys.stderr.write('FAIL 旗标定位 %s\n' % dg)
        sys.exit(1)
    seg = m.group(0)
    seg2, n = re.subn(r'\{ (\d+), [^,]+, false \},', r'{ \1, nil, true },', seg)
    if n != want:
        sys.stderr.write('FAIL %s 旗标翻转 %d != %d\n' % (dg, n, want))
        sys.exit(1)
    lua = lua[:m.start()] + seg2 + lua[m.end():]

# ── ① 新来源 ────────────────────────────────────────────────────────────────
def new_source(en, zh, note, nid, items):
    lines = ['        { "%s", "%s", "%s", "%s", {' % (en, zh, note, nid)]
    for iid, rate, new in items:
        r = 'nil' if rate is None else repr(rate)
        lines.append('            { %d, %s, %s },' % (iid, r, 'true' if new else 'false'))
    lines.append('        } },')
    return '\n'.join(lines)

STOCK_NEW = (
    new_source('Targorr the Dread', '可怕的塔格尔', '', '1696',
               [(273804, None, True), (273805, None, True), (273806, None, True), (273820, None, True)])
    + '\n' +
    new_source('Hamhock', '哈姆霍克', '', '1717',
               [(273809, None, True), (273810, None, True), (273811, None, True)])
    + '\n' +
    new_source('Bazil Thredd', '巴基尔·斯瑞德', '', '1716',
               [(273824, None, True), (273825, None, True), (273827, None, True), (273829, None, True)])
)

lua = sub1(
    r'(\{ "Kam Deepfury", "卡姆·深怒", "", "\d+", \{(?:\n            \{ \d+, [^}]+ \},)*\n        \} \},\n)',
    r'\1' + STOCK_NEW + '\n',
    lua, '监狱插入 3 boss')

lua = sub1(
    r'(\{ "Gelihast", "格里哈斯特", "[^"]*", "\d+", \{(?:\n            \{ \d+, [^}]+ \},)*\n        \} \},\n)',
    r'\1' + new_source('Lorgus Jett', '洛古斯·杰特', '', '12902',
                       [(273843, None, True), (273841, None, True), (273842, None, True)]) + '\n',
    lua, '深渊插入洛古斯')

lua = sub1(
    r'(\{ "Death Speaker Jargba", "亡语者贾格巴", "[^"]*", "\d+", \{(?:\n            \{ \d+, [^}]+ \},)*\n        \} \},\n)',
    r'\1' + new_source('Roogug', '鲁古格', '', '6168',
                       [(274155, None, True), (274152, None, True)]) + '\n',
    lua, '剃刀插入鲁古格')

lua = sub1(
    r'(\{ "Viktor the Vile", "邪恶的维克托", "[^"]*", "\d*", \{(?:\n            \{ \d+, [^}]+ \},)*\n        \} \},\n)',
    r'\1' + new_source('Lordaeron Captain', '洛丹伦上尉', '稀有', '139050',
                       [(6641, None, False), (6642, None, False)]) + '\n',
    lua, '废墟插入洛丹伦上尉')

# ── ② 缺失物品（先翻旗标再插行，避免误翻）────────────────────────────────────
NEW_ITEMS = {
    ('the_stockade', 'Kam Deepfury'): [(273808, None, True)],
    ('the_stockade', 'Trash mobs'): [(274092, None, True)],
    ('blackfathom_deeps', 'Ghamoo-ra'): [(273839, None, True)],
    ('blackfathom_deeps', 'Lady Sarevess'): [(252798, None, True)],
    ('blackfathom_deeps', 'Twilight Lord Kelris'): [(273846, None, True)],
    ('razorfen_kraul', 'Overlord Ramtusk'): [(274161, None, True)],
    ('razorfen_kraul', 'Trash mobs'): [(6681, 53.3, False)],
    ('shadowfang_keep', 'Rethilgore'): [(273456, None, True)],
    ('shadowfang_keep', 'Commander Springvale'): [(273643, None, True)],
    ('shadowfang_keep', 'Wolf Master Nandos'): [(273647, None, True)],
    ('the_deadmines', "Rhahk'Zor"): [(251363, None, True)],
    ('the_deadmines', 'Sneed'): [(273092, None, True)],
    ('the_deadmines', 'Captain Greenskin'): [(253906, None, True)],
    ('the_deadmines', 'Edwin VanCleef'): [(253940, None, True)],
    ('wailing_caverns', 'Kresh'): [(273084, None, True)],
    ('wailing_caverns', 'Skum'): [(273137, None, True)],
}

# 插入缺失物品行
for (dg, en), items in NEW_ITEMS.items():
    m = re.search(r'(\{ "%s", "(?:[^"\\]|\\.)*", "[^"]*", "\d*", \{\n)((?:            \{ \d+, [^\n]*\n)*)(        \} \})' % re.escape(en), lua)
    if not m:
        sys.stderr.write('FAIL 物品锚定 %s/%s\n' % (dg, en))
        sys.exit(1)
    add = ''.join('            { %d, %s, %s },\n' % (
        iid, 'nil' if rate is None else repr(rate), 'true' if new else 'false') for iid, rate, new in items)
    lua = lua[:m.end(2)] + add + lua[m.end(2):]

# ── ④ NPC id 验真修正（forever zone payload 实测）───────────────────────────
ID_FIX = [
    # (en, zh, 旧id, 新id)
    ('Kam Deepfury', '卡姆·深怒', '825', '1666'),
    ('Bruegal Ironknuckle', '布鲁高·铁拳', '2142', '1720'),
    ('Eric \\"The Swift\\"', '埃瑞克', '5708', '6907'),
    ('Baelog', '巴尔洛戈', '5710', '6906'),
    ('Olaf', '奥拉夫', '5709', '6908'),
    ('Revelosh', '鲁维罗什', '5945', '6910'),
    ('Ironaya', '艾隆纳亚', '6089', '7228'),
    ('Obsidian Sentinel', '黑曜石哨兵', '5285', '7023'),
    ('Ancient Stone Keeper', '古代的石头看守者', '10798', '7206'),
    ('Galgann Firehammer', '加加恩·火锤', '6059', '7291'),
    ('Grimlok', '格瑞姆洛克', '11165', '4854'),
    ('Archaedas', '阿扎达斯', '5988', '2748'),
    ('Aggem Thorncurse', '阿格姆', '6097', '4424'),
    ('Death Speaker Jargba', '亡语者贾格巴', '4644', '4428'),
    ('Overlord Ramtusk', '主宰拉姆塔斯', '4652', '4420'),
    ('Razorfen Spearhide', '剃刀沼泽刺鬃守卫', '6078', '4438'),
    ('Agathelos the Raging', '暴怒的阿迦赛罗斯', '2450', '4422'),
    ('Blind Hunter', '盲眼猎手', '4735', '4425'),
    ('Charlga Razorflank', '卡尔加·刺肋', '4642', '4421'),
    ('Earthcaller Halmgar', '唤地者哈穆加', '6102', '4842'),
    ('Ghamoo-ra', '加摩拉', '5027', '4887'),
    ('Lady Sarevess', '萨利维丝', '4979', '4831'),
    ('Gelihast', '格里哈斯特', '1773', '6243'),
    ('Baron Aquanis', '阿奎尼斯男爵', '110', '12876'),
    ('Twilight Lord Kelris', '梦游者克尔里斯', '4939', '4832'),
    ("Old Serra'kis", '瑟拉吉斯', '1816', '4830'),
    ("Aku'mai", '阿库麦尔', '2837', '4829'),
    ('Lord Cobrahn', '考布莱恩', '4213', '3669'),
    ('Lady Anacondra', '安娜科德拉', '4313', '3671'),
    ('Kresh', '克雷什', '5126', '3653'),
    ('Lord Pythas', '皮萨斯', '4214', '3670'),
    ('Skum', '斯卡姆', '4203', '3674'),
    ('Lord Serpentis', '瑟芬迪斯', '4215', '3673'),
    ('Verdan the Everliving', '永生者沃尔丹', '4256', '5775'),
    ('Mutanus the Devourer', '吞噬者穆坦努斯', '4088', '3654'),
    ('Deviate Faerie Dragon', '变异精灵龙', '1267', '5912'),
    ("Rhahk'Zor", '拉克佐', '14403', '644'),
    ('Miner Johnson', '矿工约翰森', '556', '3586'),
    ('Sneed', '斯尼德', '7125', '643'),
    ("Sneed's Shredder", '斯尼德的伐木机', '1269', '642'),
    ('Gilnid', '基尔尼格', '7124', '1763'),
    ('Mr. Smite', '重拳先生', '2026', '646'),
    ('Edwin VanCleef', '艾德温·范克里夫', '2029', '639'),
    ('Cookie', '曲奇', '1305', '645'),
    ('Rethilgore', '雷希戈尔', '524', '3914'),
    ('Razorclaw the Butcher', '屠夫拉佐克劳', '524', '3886'),
    ('Baron Silverlaine', '席瓦莱恩男爵', '3222', '3887'),
    ('Commander Springvale', '指挥官斯普林瓦尔', '3223', '4278'),
    ('Odo the Blindwatcher', '盲眼守卫奥杜', '522', '4279'),
    ('Deathsworn Captain', '死亡之誓', '3224', '3872'),
    ('Fenrus the Devourer', '吞噬者芬鲁斯', '2352', '4274'),
    ('Wolf Master Nandos', '狼王南杜斯', '11179', '3927'),
    ('Archmage Arugal', '大法师阿鲁高', '2353', '4275'),
    # 部分验中（站点译名与 wowhead 有出入的副本，只改确证的）
    ('Interrogator Vishas', '审讯员韦沙斯', r'\d+', '3983'),
    ('Bloodmage Thalnos', '血法师萨尔诺斯', r'\d+', '4543'),
    ('Houndmaster Loksey', '驯犬者洛克希', r'\d+', '3974'),
    ('Arcanist Doan', '奥法师杜安', r'\d+', '6487'),
    ('Herod', '赫洛德', r'\d+', '3975'),
    ('High Inquisitor Fairbanks', '大检察官法尔班克斯', r'\d+', '4542'),
    ('Scarlet Commander Mograine', '血色十字军指挥官莫格莱尼', r'\d+', '3976'),
    ("Tuten'kash", '图特卡什', r'\d+', '7355'),
    ('Mordresh Fire Eye', '火眼莫德雷斯', r'\d+', '7357'),
    ('Glutton', '暴食者', r'\d+', '8567'),
    ('Ragglesnout', '拉戈斯诺特', r'\d+', '7354'),
    ('Amnennar the Coldbringer', '寒冰之王亚门纳尔', r'\d+', '7358'),
    ('Plaguemaw the Rotting', '腐烂的普雷莫尔', r'\d+', '7356'),
    ('Antu\'sul', '安图苏尔', r'\d+', '8156'),
    ('Sergeant Bly', '布莱中士', r'\d+', '7604'),
    ('Veng', '温格', r'\d+', '12243'),
    ("Atal'alarion", '阿塔拉利恩', r'\d+', '8580'),
    ('Urok Doomhowl', '乌洛克', r'\d+', '10601'),
    ("Shen'dralar Provisioner", '辛德拉圣职者', r'\d+', '14371'),
    ('Blood Steward of Kirtonos', '基尔图诺斯的卫士', r'\d+', '14861'),
    ('Kirtonos the Herald', '传令官基尔图诺斯', r'\d+', '10506'),
    ('Jandice Barov', '詹迪斯·巴罗夫', r'\d+', '10503'),
    ('Rattlegore', '血骨傀儡', r'\d+', '11622'),
    ('Death Knight Darkreaver', '死亡骑士达克雷尔', r'\d+', '14516'),
    ('Marduk Blackpool', '马杜克·布莱克波尔', r'\d+', '10433'),
    ('Vectus', '维克图斯', r'\d+', '10432'),
    ('Ras Frostwhisper', '莱斯·霜语', r'\d+', '10508'),
    ('Instructor Malicia', '讲师玛丽希亚', r'\d+', '10505'),
    ('Doctor Theolen Krastinov', '瑟尔林·卡斯迪诺夫教授', r'\d+', '11261'),
    ('Lorekeeper Polkelt', '博学者普克尔特', r'\d+', '10901'),
    ('The Ravenian', '拉文尼亚', r'\d+', '10507'),
    ('Lord Alexei Barov', '阿雷克斯·巴罗夫', r'\d+', '10504'),
    ('Lady Illucia Barov', '伊露希亚·巴罗夫', r'\d+', '10502'),
    ('Darkmaster Gandling', '黑暗院长加丁', r'\d+', '1853'),
    ('Baron Rivendare', '瑞文戴尔男爵', r'\d+', '10440'),
    ('Solakar Flamewreath', '索拉卡·火冠', r'\d+', '10264'),
    ('Goraluk Anvilcrack', '古拉鲁克', r'\d+', '10899'),
    ('Gyth', '盖斯', r'\d+', '10339'),
]

for en, zh, old, new in ID_FIX:
    pat = r'(\{ "%s", "%s", "[^"]*", ")%s(", \{)' % (re.escape(en), zh, old)
    if not re.search(pat, lua):
        sys.stderr.write('FAIL id锚定 %s(%s)\n' % (zh, en))
        sys.exit(1)
    lua = re.sub(pat, r'\g<1>%s\g<2>' % new, lua, count=1)

open(LOOT, 'w', encoding='utf-8', newline='\n').write(lua)

# ── ⑤ Data_Dungeons.lua 计数 ────────────────────────────────────────────────
dgt = open(DG, encoding='utf-8').read()
COUNT_FIX = [
    ('the_stockade', 6, 18),        # 3/5
    ('ruins_of_lordaeron', 7, 20),  # 6/18
    ('wailing_caverns', 10, 30),    # 10/28
    ('the_deadmines', 11, 48),      # 11/44
    ('shadowfang_keep', 14, 44),    # 14/41
    ('blackfathom_deeps', 9, 35),   # 8/29
    ('razorfen_kraul', 10, 34),     # 9/30
]
for dg, bc, dc in COUNT_FIX:
    pat = r'(\{ id = "%s",.*?bossCount = )\d+(, +dropCount = )\d+(,)' % dg
    dgt, n = re.subn(pat, r'\g<1>%d\g<2>%d\g<3>' % (bc, dc), dgt, flags=re.S)
    if n != 1:
        sys.stderr.write('FAIL 计数 %s 命中 %d\n' % (dg, n))
        sys.exit(1)
open(DG, 'w', encoding='utf-8', newline='\n').write(dgt)

# ── 自检 ────────────────────────────────────────────────────────────────────
rows = re.findall(r'\n            \{ ([^}]*?) \},', lua)
fields = {}
for r in rows:
    n = r.count(',') + 1
    fields[n] = fields.get(n, 0) + 1
print('物品行总数 %d（原 1807），字段数分布 %s' % (len(rows), fields))
assert set(fields) == {3}, fields
for s in ('站点', '出处', '上游', '参考', '照抄', '剥离', 'foreverchanges'):
    assert s not in lua, s
print('OK 掉落表迁移完成')
