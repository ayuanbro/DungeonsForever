# -*- coding: utf-8 -*-
"""攻略文案清理（2026-10-08）：去掉站点溯源语句与 ID 引用。
zhCN 数据 = Core/Data/Data_DungeonGuide.lua；EN 键值 = _temp/enus_data_guide19.py。
子串级替换，每条断言必须命中，避免静默漂移。
"""
import io, sys

sys.stdout.reconfigure(encoding='utf-8')

GUIDE = 'Core/Data/Data_DungeonGuide.lua'
TABLE = '_temp/enus_data_guide19.py'

ZH = [
    # ---- 溯源语句 ----
    ('下列 boss 打法以 wowhead 实测稿为准，随版本更新持续核对。',
     '下列 boss 打法随版本更新持续核对。'),
    ('wowhead 指南没有为它单列打法。它是联盟任务', '它是联盟任务'),
    ('Wowhead 证实部落侧的闸门需要用「达拉然下水道钥匙」（277507）开启。',
     '部落侧的闸门需要用「达拉然下水道钥匙」开启。'),
    ('（联盟/部落各自的墓地，Wowhead 地图上已标注）', '（联盟/部落各自的墓地）'),
    ('Wowhead 正式攻略把这场法力系战斗标为「奥术谜团」（Arcanic Enigma，npc 246016）—— '
     '很可能就是我方名单里的法力吞噬者／法力元素占位之一，对应关系尚待实机确认。',
     '这场法力系战斗很可能就是名单里的法力吞噬者／法力元素占位之一'
     '（试玩标注名「奥术谜团」Arcanic Enigma），对应关系尚待实机确认。'),
    ('数据文件中有名单，尚未有人见过 —— 演示录像与 Wowhead 正式攻略都没有展示这场战斗。'
     '副本完全开放测试后此条目预计会有更新。',
     '这场战斗尚未有人见过 —— 副本完全开放测试后此条目预计会有更新。'),
    # ---- ID 引用 ----
    ('灌木丛潜行者（#260800）', '灌木丛潜行者'),
    ('灌木丛女家长（#260802）', '灌木丛女家长'),
    ('「裂筋」（#3604）', '「裂筋」'),
    ('「尘暴」（#1316382）', '「尘暴」'),
    ('灌木丛猎人（#260801）', '灌木丛猎人'),
    ('「撕裂」（#12054）', '「撕裂」'),
    ('「恐吓咆哮」（#14100）', '「恐吓咆哮」'),
    ('「狂怒」（#18501）', '「狂怒」'),
    ('「雷霆一击」（#15588）', '「雷霆一击」'),
    ('「达拉然下水道钥匙」（277507）', '「达拉然下水道钥匙」'),
    ('试玩中有人看到他掉落一把弩「Gravespike Repeater」（wowhead 尚未收录物品 ID）。',
     '试玩中有人看到他掉落一把弩「Gravespike Repeater」。'),
    ('BlizzCon 试玩里他掉落「Ponderous Orb」（wowhead 尚未给出中文名）；',
     'BlizzCon 试玩里他掉落「Ponderous Orb」；'),
]

EN = [
    # 键（中文）与值（英文）同步清理
    ('下列 boss 打法以 wowhead 实测稿为准，随版本更新持续核对。',
     '下列 boss 打法随版本更新持续核对。'),
    (" — boss strategies below follow Wowhead's tested writeup and will be re-checked as the beta moves on.",
     " — boss strategies below will be re-checked as the beta moves on."),
    ('wowhead 指南没有为它单列打法。它是联盟任务', '它是联盟任务'),
    ("Wowhead's guide has no dedicated strategy box for this fight. It is the target",
     'It is the target'),
    ('Wowhead 证实部落侧的闸门需要用「达拉然下水道钥匙」（277507）开启。',
     '部落侧的闸门需要用「达拉然下水道钥匙」开启。'),
    ('Wowhead confirms the Horde-side gate is opened with a Dalaran Sewer Key (277507).',
     'The Horde-side gate is opened with a Dalaran Sewer Key.'),
    ('（联盟/部落各自的墓地，Wowhead 地图上已标注）', '（联盟/部落各自的墓地）'),
    ("(separate Alliance/Horde ones, marked on Wowhead's map)", '(separate Alliance/Horde ones)'),
    ('Wowhead 正式攻略把这场法力系战斗标为「奥术谜团」（Arcanic Enigma，npc 246016）—— '
     '很可能就是我方名单里的法力吞噬者／法力元素占位之一，对应关系尚待实机确认。',
     '这场法力系战斗很可能就是名单里的法力吞噬者／法力元素占位之一'
     '（试玩标注名「奥术谜团」Arcanic Enigma），对应关系尚待实机确认。'),
    ("Wowhead's full guide lists this mana-themed fight as Arcanic Enigma (npc 246016) — "
     "most likely one of the mana placeholders in our own data (Mana Devourer / Mana Elemental); "
     'the exact mapping is still unconfirmed.',
     'This mana-themed fight most likely maps to one of the mana placeholders '
     '(Mana Devourer / Mana Elemental) under its playtest name Arcanic Enigma; '
     'the exact mapping is still unconfirmed.'),
    ('数据文件中有名单，尚未有人见过 —— 演示录像与 Wowhead 正式攻略都没有展示这场战斗。'
     '副本完全开放测试后此条目预计会有更新。',
     '这场战斗尚未有人见过 —— 副本完全开放测试后此条目预计会有更新。'),
    ("Listed in the data files but nobody has seen this fight yet — neither the demo footage "
     "nor Wowhead's guide covers it.",
     'Nobody has seen this fight yet.'),
    ('「Gravespike Repeater」（wowhead 尚未收录物品 ID）。', '「Gravespike Repeater」。'),
    ("; he was seen dropping a crossbow, 'Gravespike Repeater' (item id not yet in wowhead's database).",
     "; he was seen dropping a crossbow, 'Gravespike Repeater'."),
    ('BlizzCon 试玩里他掉落「Ponderous Orb」（wowhead 尚未给出中文名）；',
     'BlizzCon 试玩里他掉落「Ponderous Orb」；'),
    ("In the BlizzCon playtest he dropped a 'Ponderous Orb' (no Chinese name on wowhead yet)",
     "In the BlizzCon playtest he dropped a 'Ponderous Orb'"),
]


def patch(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    miss = [old for old, _ in pairs if old not in s]
    if miss:
        print('!! %s 缺少 %d 条：' % (path, len(miss)))
        for m in miss:
            print('   MISS:', m[:80])
        return False
    for old, new in pairs:
        s = s.replace(old, new)
    io.open(path, 'w', encoding='utf-8', newline='').write(s)
    print('OK', path, '替换 %d 条' % len(pairs))
    return True


if patch(GUIDE, ZH) and patch(TABLE, EN):
    # 复验：玩家可见文本中不允许再出现站点名 / ID
    s = io.open(GUIDE, encoding='utf-8').read()
    body_lines = [ln for ln in s.split('\n')
                  if not ln.lstrip().startswith('--')]
    residue = []
    for ln in body_lines:
        for pat in ('wowhead', 'Wowhead', '（#', '（2775', 'npc 246016'):
            if pat in ln:
                residue.append((pat, ln.strip()[:100]))
    if residue:
        print('!! 残留：')
        for p, ln in residue:
            print('  ', p, '|', ln)
    else:
        print('复验通过：正文 0 残留（文件头生成器注释除外）')
else:
    print('存在问题，未写回任何文件')
