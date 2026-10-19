# -*- coding: utf-8 -*-
"""全数据文件残余收口层（2026-09-25 晚，gen 后审计 enus_gap_all.py 的 61 distinct）。

- RESID = EXACT 词条（附魔全名/装备类目/专精/附魔子名/BIS 槽位标签）；
- EXTRA_RULES = 数字变体（附魔应用语、命中吸收、元素伤害/治疗加成），
  gen_enus_data.py 把它接在 D1.RULES 之后（先于 GLOSS）。
"""

import re

RESID = {
    # BIS 附魔全名（GLOSS 段替换到「-」后半挂的子名）
    '附魔靴子 - 初级速度': 'Enchant Boots - Minor Speed',
    '附魔武器 - 攻击': 'Enchant Weapon - Attack',      # 训练师教学附魔，武器伤害 +3
    # 副本名漏网
    '祖尔法拉克': "Zul'Farrak",
    # BIS 附魔槽位标签
    '腿部': 'Legs',
    # 装备类目（配方显示名，与既有 "Mail Chest, Lv N" 风格一致）
    '布甲头盔': 'Cloth Helm', '布甲披风': 'Cloth Cloak', '布甲靴': 'Cloth Boots',
    '布甲护腿': 'Cloth Leggings',
    '锁甲头盔': 'Mail Helm', '皮甲腰带': 'Leather Belt', '腰带': 'Belt',
    # 专精限制标签
    '暗影': 'Shadow', '平衡': 'Balance', '惩戒': 'Retribution', '狂怒': 'Fury',
    '生存': 'Survival', '射击': 'Marksmanship', '刺杀': 'Assassination',
    '战斗': 'Combat', '野性': 'Feral',
    # 附魔子名 / 效果关键词
    '初级速度': 'Minor Speed', '初级属性': 'Minor Stats', '次级属性': 'Lesser Stats',
    '强效属性': 'Greater Stats',
    '属性': 'Stats', '高级采矿': 'Advanced Mining', '高级采药': 'Advanced Herbalism',
    '高级剥皮': 'Advanced Skinning', '骑术': 'Riding Skill', '法力回复': 'Mana Regeneration',
    '躲闪': 'Dodge', '潜行': 'Stealth', '敏锐': 'Subtlety', '威胁': 'Threat',
    '屠魔': 'Demonslaying', '法术强度': 'Spell Power', '任务': 'Quest',
    '主手杂项': 'Main-hand misc',
    # 套装名
    '风暴布法衣': 'Stormshroud Armor',
}

_ELEM = {'火焰': 'Fire', '冰霜': 'Frost', '神圣': 'Holy',
         '自然': 'Nature', '奥术': 'Arcane', '暗影': 'Shadow'}

EXTRA_RULES = [
    (re.compile(r'^永久附着于物品$'), lambda m: 'Permanently attaches to item'),
    (re.compile(r'^永久附着于物品，(\d+) 级$'),
     lambda m: 'Permanently attaches to item, level %s' % m.group(1)),
    (re.compile(r'^每次命中时有 (\d+)% 的几率获得 (\d+) 点伤害吸收。每 5 秒最多触发一次。$'),
     lambda m: '%s%% chance on hit to gain %s damage absorption. '
               'At most once every 5 sec.' % (m.group(1), m.group(2))),
    (re.compile(r'^(火焰|冰霜|神圣|自然|奥术|暗影)法术伤害 \+(\d+)$'),
     lambda m: '%s Spell Damage +%s' % (_ELEM[m.group(1)], m.group(2))),
    (re.compile(r'^(火焰|冰霜|神圣|自然|奥术|暗影)伤害 \+(\d+)$'),
     lambda m: '%s Damage +%s' % (_ELEM[m.group(1)], m.group(2))),
    (re.compile(r'^治疗法术 \+(\d+)$'), lambda m: 'Healing +%s' % m.group(1)),
    # ★ 2026-10-03：30级 BIS 卷的「任务：<任务名>」备注（任务名本身已是英文，
    #   只有前缀是中文）。EXACT/GLOSS 都命中不了整串 ⇒ 用前缀规则统一剥掉。
    (re.compile(r'^任务：(.*)$'), lambda m: 'Quest: %s' % m.group(1).strip()),
]
