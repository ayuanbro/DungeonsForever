# -*- coding: utf-8 -*-
"""第五轮译源修正：A(3 处无限+杂词) + B(全库未翻译散文补译)。
文本级替换（保留原文件格式）；每处先断言 old 存在，缺失即报错。"""
import io
import os

TD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_cg_trans')

# (文件, old, new) —— old/new 为文件文本中的字面内容（\u0003 以 6 字符转义形式给出）
EDITS = [
    # ---------- A. 无限 + 杂词 ----------
    ('rogue_assassination.json',
     '在《无限》怀旧服中，联盟盗贼通常会优先选择',
     '在无限服中，联盟盗贼通常会优先选择'),
    ('rogue_assassination.json',
     '在《无限》怀旧服中，部落盗贼会更倾向于',
     '在无限服中，部落盗贼会更倾向于'),
    ('warlock_affliction.json',
     '所有专业都已随《无限》资料片重做。',
     '所有专业都已随《无限》重做。'),

    # ---------- B. druid_restoration/changes 未翻译/半翻译 ----------
    # #2 tb row0（收尾悬空「…牧师职业的」）
    ('druid_restoration.json',
     '而是锁定作用于目标的小队成员。|s408120|现在更接近|s25316|牧师职业的"',
     '而是锁定作用于目标的小队成员。|s408120|现在更接近牧师职业的|s25316|。"'),
    # #2 tb row2（半翻译）
    ('druid_restoration.json',
     '将我们的|s1430|、|s408120|和|s18562|down to one second. As a new talent to classic, '
     'we see Blizzard start to paint the picture of fast HoTs being a powerful tool to handle '
     'healing situations. This will enable us to set up quick raid-wide HoT blankets to handle '
     'AoE situations, and pepper in|s408120|just as fast to catch any group that is dipping too low."',
     '将我们的|s1430|、|s408120|和|s18562|的公共冷却时间缩短至一秒。作为经典版本新增的天赋，'
     '我们可以看到暴雪正着手描绘「快速 HoT 是应对治疗情境的强力工具」这一图景。这将使我们能够'
     '快速铺开全团 HoT 覆盖以应对 AoE 场合，并以同样快的速度补上|s408120|，接住任何掉血过快的队伍。"'),
    # #2 tb row3
    ('druid_restoration.json',
     'A 5% buff to our HoTs at max level. An easy pick-up for any talent build since it\'s in the '
     'first tier of Balance talents."',
     '满级时为我们的 HoT 提供 5% 加成。由于它位于平衡天赋树的第一层，任何天赋构筑都能轻松点出。"'),
    # #2 tb row4
    ('druid_restoration.json',
     'An extra 4% crit to our heals at max rank. All our HoTs can now crit, so this talent is a '
     'great pickup to improve our healing throughput."',
     '满级时使我们的治疗额外获得 4% 暴击。我们的所有 HoT 现在都能暴击，因此这个天赋是提升治疗'
     '输出量的绝佳选择。"'),
    # #2 tb row5（半翻译）
    ('druid_restoration.json',
     'Lengthens the duration of our|s1430|和|s8938|HoTs. This talent has great synergy with|s18562|, '
     'which now heals for the total duration of the HoT instead of a static amount of seconds."',
     '延长我们的|s1430|和|s8938|的 HoT 持续时间。这个天赋与|s18562|联动极佳，后者现在的治疗量'
     '取整个 HoT 的持续时间总量，而不再是固定的秒数。"'),
    # #3 p
    ('druid_restoration.json',
     '"v": "There are many changes to our existing abilities and talents. We are seeing fresh '
     'updates on familiar effects that change how we think about their healing impact."',
     '"v": "我们现有的技能和天赋有许多改动。我们看到那些熟悉的效应得到了全新的更新，改变了我们'
     '对它们治疗影响力的看法。"'),
    # #4 tb row0
    ('druid_restoration.json',
     '"Now scales the returned damage by the caster\'s Spell Power."',
     '"现在使反弹的伤害按施法者的法术强度缩放。"'),
    # #4 tb row1
    ('druid_restoration.json',
     '"Significantly cheaper, and the HoT portion can now crit."',
     '"法力消耗大幅降低，且其 HoT 部分现在可以暴击。"'),
    # #4 tb row2（半翻译）
    ('druid_restoration.json',
     'Now baseline and can trigger off spell casts. Watching for the buff and then casting a large'
     '|s408120|、|s5188|, or|s8938|将对法力效率有极大帮助。"',
     '现在成为基础技能，且可由施法触发。留意该增益，随后施放一个大型的|s408120|、|s5188|或|s8938|，'
     '将对法力效率有极大帮助。"'),

    # ---------- B. 其它未翻译 ----------
    ('hunter_beast-mastery.json',
     '"v": "Pets"',
     '"v": "宠物"'),
    ('mage_arcane.json',
     '"v": "High Order Skyborne"',
     '"v": "高阶天裔"'),
    ('rogue_subtlety.json',
     '"v": "Dwarf"',
     '"v": "矮人"'),
    ('rogue_subtlety.json',
     '"v": "\\u0003Horde\\u0004"',
     '"v": "\\u0003部落\\u0004"'),
    ('rogue_subtlety.json',
     '"v": "Orc"',
     '"v": "兽人"'),
    ('rogue_subtlety.json',
     '"v": "Undead"',
     '"v": "亡灵"'),
    ('rogue_subtlety.json',
     '"v": "Troll"',
     '"v": "巨魔"'),
    ('warlock_demonology.json',
     '"+5% damage to Beasts and Dragonkin."',
     '"+5% 对野兽和龙类的伤害。"'),
    # mage_arcane/systems ul#0（半翻译）
    ('mage_arcane.json',
     '获得一层负面效果，最多叠加 4 层——每层都会提高下一次奥术冲击的法力消耗，并提升其伤害'
     '\\u0003其他\\u0004spell you use after. This other spell will clear the stacks back to 0. '
     'This is used to build up stacks and then use them to buff a meaningful spell afterwards; '
     'this is expected to be done with Arcane Missiles buffed by|s400588|, but there could be '
     'different iterations."',
     '获得一层负面效果，最多叠加 4 层——每层都会提高下一次奥术冲击的法力消耗，并提升你随后使用的'
     '任何一个\\u0003其他\\u0004法术的伤害。这个后续法术会将层数清零。玩法就是先叠层，然后用它们'
     '强化之后一个有意义的大法术；通常这会是用|s400588|强化过的奥术飞弹来完成，但也可能存在不同的变体。"'),
    # warlock_destruction/changes #3（半翻译）
    ('warlock_destruction.json',
     '不再作用于其他人的伤害。|s18119|increases|s348|的直接伤害并附加减速效果|s18932|。'
     '|s17959|现在需要5点天赋点而非1点。|s17927|仅用于增益|s17923|\'s Crit chance; now it also '
     'increases the damage of every Destruction spell."',
     '不再作用于其他人的伤害。|s18119|提升|s348|的直接伤害，并为|s18932|附加减速效果。'
     '|s17959|现在需要5点天赋点而非1点。|s17927|过去仅用于提升|s17923|的暴击几率；现在它还会'
     '提高每一个毁灭系法术的伤害。"'),
]


def main():
    ok = 0
    for fn, old, new in EDITS:
        p = os.path.join(TD, fn)
        text = io.open(p, encoding='utf-8').read()
        if old not in text:
            raise SystemExit('!! MISS in %s:\n%r' % (fn, old[:120]))
        cnt = text.count(old)
        if cnt != 1:
            raise SystemExit('!! NOT UNIQUE (%d) in %s:\n%r' % (cnt, fn, old[:120]))
        io.open(p, 'w', encoding='utf-8', newline='').write(text.replace(old, new))
        ok += 1
        print('OK  %-28s %s' % (fn, old[:48].replace('\n', ' ')))
    print('共应用 %d 处。' % ok)


if __name__ == '__main__':
    main()
