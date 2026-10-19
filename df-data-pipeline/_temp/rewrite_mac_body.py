# -*- coding: utf-8 -*-
"""把与参考插件逐字符相同的 29 条宏体改写为我方版本。

每条改写的独立理由（不为不同而不同）：
  ① 目标获取链：/cleartarget [dead] + /targetenemy [noharm] —— 目标死了/没目标时自动续上
  ② 焦点/鼠标指向：把「必须切目标」改成焦点或鼠标指向优先
  ③ 掐读条：需要即时生效的技能补 /stopcasting
  ④ 治疗回落链：[@player] → [@mouseover,help,nodead][help,nodead][@player]
  ⑤ 图标跟随状态：#showtooltip 带条件，图标按分支切换
  ⑥ 变身/上马：#dismount 先下坐骑；!形态 编进名字防误取消

用法：python _temp/rewrite_mac_body.py [--apply]
"""
import re
import sys

ENTRIES = {}


def E(cls, cn, en, legacy, body, what_cn, what_en, ec, ee):
    ENTRIES[(cls, cn)] = dict(cls=cls, cn=cn, en=en, legacy=legacy, body=body,
                              what_cn=what_cn, what_en=what_en, ec=ec, ee=ee)


E('WARRIOR', '冲锋', 'Charge', None,
  '#showtooltip {Charge}\n/cleartarget [dead]\n/startattack\n/cast {Charge}',
  '冲过去，目标死了会自动换人。', 'Charge in; if your target is dead it picks a new one.',
  ['图标显示「冲锋」。', '目标已经死了就清掉目标。', '落地后自动开始普攻。', '施放冲锋。'],
  ['The icon shows Charge.', 'Clears your target if it is already dead.',
   'Starts auto-attacking as soon as you land.', 'Then cast Charge.'])

E('WARRIOR', '压制', 'Overpower', None,
  '#showtooltip {Overpower}\n/startattack\n/cast [nostance:1] {Battle Stance}; {Overpower}',
  '顺手开始普攻，需要时先切战斗姿态。', 'Starts auto-attacking too, switching stance when needed.',
  ['图标显示「压制」。', '先开始普攻，压制就绪那一下不会白挨。',
   '不在战斗姿态就先切过去（要按两下）；在战斗姿态直接放压制。'],
  ['The icon shows Overpower.', 'Starts auto-attacking so the swing is not wasted.',
   'Switches to Battle Stance first if needed (press twice); otherwise Overpower.'])

E('WARRIOR', '顺劈', 'Strike', None,
  '#showtooltip [mod:shift] {Cleave}; {Heroic Strike}\n/startattack\n/cast [mod:shift] {Cleave}; {Heroic Strike}',
  '英勇打击；Shift 改顺劈。图标跟着变。', 'Heroic Strike; Shift for Cleave. The icon follows.',
  ['图标按当前分支显示（按住 Shift 时显示「顺劈斩」）。', '先开始普攻。',
   '默认打英勇打击；按住 Shift 时改打顺劈斩。'],
  ['The icon follows the branch (Shift shows Cleave).', 'Starts auto-attacking.',
   'Heroic Strike by default; Shift switches it to Cleave.'])

E('WARRIOR', '拦截', 'Intercept', None,
  '#showtooltip {Intercept}\n/startattack\n/cast [nostance:3] {Berserker Stance}; {Intercept}',
  '切狂暴姿态并拦截，顺手开始普攻。', 'Switches to Berserker Stance, Intercepts and starts attacking.',
  ['图标显示「拦截」。', '先开始普攻。', '不在狂暴姿态时先切过去（要按两下）。', '施放拦截。'],
  ['The icon shows Intercept.', 'Starts auto-attacking.',
   'Switches to Berserker Stance first if needed (press twice).', 'Then Intercept.'])

E('PALADIN', '审判', 'Judgement', None,
  '#showtooltip {Judgement}\n/cleartarget [dead]\n/startattack\n/cast {Judgement}',
  '审判圣印并开始攻击，目标死了自动换人。', 'Judges your seal; retargets if the target is dead.',
  ['图标显示「审判」。', '目标已经死了就清掉目标。', '同时开始普攻。', '施放审判，把圣印打出去。'],
  ['The icon shows Judgement.', 'Clears your target if it is already dead.',
   'Starts auto-attacking.', 'Then Judge, releasing the seal.'])

E('PALADIN', '制裁', 'Hammer', None,
  '#showtooltip {Hammer of Justice}\n/stopcasting\n/cast [@mouseover,harm,nodead][] {Hammer of Justice}',
  '掐读条晕住鼠标指向的敌人，不用切目标。', 'Stuns the enemy under your mouse without switching target.',
  ['图标显示「制裁之锤」。', '先掐掉自己正在读的法术。',
   '优先晕鼠标指向的敌人；没指向时晕当前目标。'],
  ['The icon shows Hammer of Justice.', 'Cancel your own cast first.',
   'Stuns your mouseover first, otherwise your current target.'])

E('PALADIN', '自我治疗', 'Self Heal', None,
  '#showtooltip\n/cast [@mouseover,help,nodead][help,nodead][@player] {Flash of Light|Holy Light}',
  '鼠标指向谁就治谁，没指向治目标，再没有治自己。', 'Heals mouseover, then target, then yourself.',
  ['图标显示当前会用的那道治疗。',
   '优先级：鼠标指向的友方 → 当前目标（友方）→ 你自己；自动挑你会的最好的那一道。'],
  ['The icon shows which heal will be used.',
   'Order: friendly mouseover, then target, then yourself; picks your best known heal.'])

E('HUNTER', '攻击', 'Attack', None,
  '#showtooltip\n/targetenemy [noharm]\n/startattack\n/petattack',
  '没目标会自动选最近的敌人，然后你和宠物一起开打。',
  'Picks the nearest enemy if you have none, then you and the pet attack.',
  ['图标跟着显示这个按钮要做的事。', '没有可打目标时自动选最近的敌人。',
   '点一下立刻开始普攻。', '宠物也扑向同一个目标。'],
  ['The icon shows what the button does.', 'Picks the nearest enemy when you have none.',
   'One click starts auto-attacking.', 'Your pet charges the same target.'])

E('HUNTER', '开怪', 'Opener', 'DF Opener',
  "#showtooltip\n/cleartarget [dead]\n/targetenemy [noharm]\n/petattack\n/castsequence reset=target {Hunter's Mark}, {Serpent Sting}",
  '自动找敌、宠物扑上、上标记再挂毒蛇钉刺。', 'Finds a target, sends the pet, marks it, then stings it.',
  ['图标跟着显示下一个要放的法术。', '目标已经死了就清掉。', '没有可打目标时自动选最近的敌人。',
   '宠物先扑上去，替你把目标拉住。',
   '连按两下：第一下上猎人印记，第二下挂毒蛇钉刺；换目标会自动从头开始。'],
  ['The icon shows the next spell in the sequence.', 'Clears a dead target.',
   'Picks the nearest enemy when you have none.', 'Your pet charges in first to hold the target.',
   'Press twice: the first marks with Hunter\u2019s Mark, the second applies Serpent Sting; changing target resets it.'])

E('ROGUE', '起手', 'Open', None,
  '#showtooltip\n/startattack\n/cast [stealth] {Cheap Shot|Garrote}; {Sinister Strike}',
  '潜行用起手技，出潜行当普攻键，顺便开始普攻。', 'Opener from Stealth, otherwise Sinister Strike, plus auto-attack.',
  ['图标跟着显示本次会放哪个技能。', '先开始普攻。',
   '潜行时放起手技（随你学到的自动升级），出潜行后放影袭。'],
  ['The icon shows which one will fire.', 'Starts auto-attacking.',
   'In Stealth it opens with your best opener; otherwise Sinister Strike.'])

E('ROGUE', '匕首', 'Dagger', None,
  '#showtooltip\n/startattack\n/cast [stealth] {Ambush}; {Backstab}',
  '带匕首时：潜行伏击，平时背刺，顺便开始普攻。',
  'With a dagger: Ambush from Stealth, Backstab otherwise, plus auto-attack.',
  ['图标跟着显示本次会放哪个技能。', '先开始普攻。',
   '潜行时放伏击；平时放背刺（都要站在敌人背后）。'],
  ['The icon shows which one will fire.', 'Starts auto-attacking.',
   'Ambush from Stealth; Backstab otherwise (both need you behind the enemy).'])

E('ROGUE', '踢击', 'Kick', None,
  '#showtooltip {Kick}\n/cast [@focus,harm,nodead][] {Kick}',
  '优先打断焦点目标，不用切目标。', 'Interrupts your focus target first, without switching target.',
  ['图标显示「踢击」。', '优先打断焦点目标（设焦点：选中敌人后打 /focus）；没设焦点就打断当前目标。'],
  ['The icon shows Kick.',
   'Interrupts your focus target first (set one with /focus on an enemy); otherwise your current target.'])

E('ROGUE', '消失', 'Vanish', None,
  '#showtooltip {Vanish}\n/stopcasting\n/stopattack\n/cast {Vanish}',
  '掐读条、停手、消失，一次进潜行。', 'Cancels your cast, stops attacking and vanishes.',
  ['图标显示「消失」。', '先掐掉正在读的技能。', '再停止攻击，免得刚消失就被打出来。',
   '施放消失，脱战并进入潜行。'],
  ['The icon shows Vanish.', 'Cancel any cast first.', 'Stop attacking so you are not knocked back out.',
   'Then Vanish: drop combat and slip into stealth.'])

E('PRIEST', '护盾', 'Shield', None,
  '#showtooltip {Power Word: Shield}\n/cast [help,nodead][@player] {Power Word: Shield}',
  '给友方目标套盾；目标是敌人或没目标就套自己。',
  'Shields a friendly target, otherwise yourself.',
  ['图标显示「真言术：盾」。',
   '当前目标是友方就套给他；否则套给自己——给队友加盾不用切目标也能用。'],
  ['The icon shows Power Word: Shield.',
   'Shields a friendly target, otherwise yourself, so you can cover a teammate without retargeting.'])

E('PRIEST', '恢复', 'Renew', None,
  '#showtooltip {Renew}\n/cast [help,nodead][@player] {Renew}',
  '给友方目标挂恢复；否则挂自己。', 'Renews a friendly target, otherwise yourself.',
  ['图标显示「恢复」。', '当前目标是友方就挂给他；否则挂给自己。'],
  ['The icon shows Renew.', 'Renews a friendly target, otherwise yourself.'])

E('PRIEST', '自我治疗', 'Self Heal', None,
  '#showtooltip\n/cast [@mouseover,help,nodead][help,nodead][@player] {Flash Heal|Heal|Lesser Heal}',
  '鼠标指向谁就治谁，不用切目标。', 'Heals whoever your mouse is over, without switching targets.',
  ['图标显示当前会用的那道治疗。',
   '优先级：鼠标指向的友方 → 当前目标 → 你自己；学会更好的治疗后自动跟着换。'],
  ['The icon shows which heal will be used.',
   'Order: friendly mouseover, then target, then yourself; follows along as you learn better heals.'])

E('SHAMAN', '打断', 'Interrupt', None,
  '#showtooltip {Earth Shock}\n/stopcasting\n/cast [@focus,harm,nodead][] {Earth Shock}',
  '掐读条，优先打断焦点目标。', 'Cancels your cast and interrupts your focus target first.',
  ['图标显示「地震术」。', '先掐掉自己正在读的法术。',
   '优先打断焦点目标；没设焦点就打断当前目标。'],
  ['The icon shows Earth Shock.', 'Cancel your own cast first.',
   'Interrupts your focus target first, otherwise your current target.'])

E('SHAMAN', '武器附魔', 'Imbue', None,
  '#showtooltip\n/cast [mod:shift] {Flametongue Weapon|Rockbiter Weapon}; {Windfury Weapon|Flametongue Weapon|Rockbiter Weapon}',
  '给武器上最好的附魔；Shift 换成法伤类附魔。',
  'Puts your best weapon imbue on; Shift switches to the spell-damage ones.',
  ['图标跟着显示本次会上哪个附魔。',
   '默认按顺序挑你会的最好的一个（风怒优先）；按住 Shift 时改用火焰/石肤这类，方便临时换手感。'],
  ['The icon shows which imbue will be used.',
   'By default the best one you know (Windfury first); Shift switches to Flametongue or Rockbiter for a quick change.'])

E('SHAMAN', '自我治疗', 'Self Heal', None,
  '#showtooltip\n/cast [@mouseover,help,nodead][help,nodead][@player] {Lesser Healing Wave|Healing Wave}',
  '鼠标指向谁就治谁，不用切目标。', 'Heals whoever your mouse is over, without switching targets.',
  ['图标显示当前会用的那道治疗。',
   '优先级：鼠标指向的友方 → 当前目标 → 你自己；学会次级治疗波之后优先用它。'],
  ['The icon shows which heal will be used.',
   'Order: friendly mouseover, then target, then yourself; prefers the faster Lesser Healing Wave once known.'])

E('MAGE', '收尾', 'Finish', None,
  '#showtooltip {Fire Blast}\n/targetenemy [noharm]\n/stopcasting\n/cast {Fire Blast}',
  '没目标自动选敌，掐读条用火焰冲击收尾。', 'Picks a target if you have none, stops casting and fires.',
  ['图标显示「火焰冲击」。', '没有可打目标时自动选最近的敌人。',
   '先掐掉自己正在读的法术。', '施放瞬发的火焰冲击，补最后一下。'],
  ['The icon shows Fire Blast.', 'Picks the nearest enemy when you have no target.',
   'Cancel your own cast first.', 'Then the instant Fire Blast to finish it off.'])

E('MAGE', '冰霜新星', 'Nova', None,
  '#showtooltip {Frost Nova}\n/stopcasting\n/cast [@player] {Frost Nova}',
  '掐读条，把身边的敌人冻住（对谁都能放）。',
  'Stops your cast and freezes nearby enemies, regardless of your target.',
  ['图标显示「冰霜新星」。', '先掐掉自己正在读的法术。',
   '以自己为中心施放——目标不在范围或是友方的时候照样能放出来。'],
  ['The icon shows Frost Nova.', 'Cancel your own cast first.',
   'Casts at your own position, so it works even when your target is friendly or out of range.'])

E('MAGE', '变形术', 'Polymorph', None,
  '#showtooltip {Polymorph}\n/cast [@focus,harm,nodead][@mouseover,harm,nodead][] {Polymorph}',
  '优先变焦点，其次鼠标指向，都不用切目标。',
  'Sheeps your focus first, then your mouseover, without switching target.',
  ['图标显示「变形术」。',
   '优先级：焦点目标 → 鼠标指向的敌人 → 当前目标；只对敌对目标生效，不会误变队友。'],
  ['The icon shows Polymorph.',
   'Order: focus, then hostile mouseover, then current target; only hostile targets so teammates are safe.'])

E('WARLOCK', '持续伤害', 'DoT', None,
  '#showtooltip {Corruption}\n/cleartarget [dead]\n/targetenemy [noharm]\n/cast {Corruption}\n/petattack',
  '自动找敌、上腐蚀术、宠物扑上。', 'Finds a target, applies Corruption and sends the pet.',
  ['图标显示「腐蚀术」。', '目标已经死了就清掉。', '没有可打目标时自动选最近的敌人。',
   '给目标上腐蚀术。', '宠物同时扑向同一个目标。'],
  ['The icon shows Corruption.', 'Clears a dead target.', 'Picks the nearest enemy when you have none.',
   'Applies Corruption.', 'Your pet charges the same target.'])

E('WARLOCK', '生命分流', 'Life Tap', None,
  '#showtooltip {Life Tap}\n/stopcasting\n/cast {Life Tap}',
  '掐读条立刻分流，不耽误下一发。', 'Cancels your cast and taps immediately.',
  ['图标显示「生命分流」。', '先掐掉正在读的法术，分流不排队。',
   '蓝不够、血还安全时用；之后靠吃东西或吸取生命补回来。'],
  ['The icon shows Life Tap.', 'Cancels your cast so the tap does not queue behind it.',
   'Use it when mana is low and health is safe; get the health back by eating or with Drain Life.'])

E('WARLOCK', '恐惧', 'Fear', None,
  '#showtooltip {Fear}\n/cast [@focus,harm,nodead][@mouseover,harm,nodead][] {Fear}',
  '优先恐焦点，其次鼠标指向。', 'Fears your focus first, then your mouseover.',
  ['图标显示「恐惧」。',
   '优先级：焦点目标 → 鼠标指向的敌人 → 当前目标；只对敌对目标生效。小心它跑进别的怪堆里。'],
  ['The icon shows Fear.',
   'Order: focus, then hostile mouseover, then current target; only hostile targets. Careful: it may run into more enemies.'])

E('WARLOCK', '生命通道', 'Funnel', None,
  '#showtooltip {Health Funnel}\n/stopcasting\n/cast {Health Funnel}',
  '掐读条马上开始给宠物输血。', 'Cancels your cast and starts feeding your pet immediately.',
  ['图标显示「生命通道」。', '先掐掉正在读的法术。',
   '宠物快死了、而你还安全时用。'],
  ['The icon shows Health Funnel.', 'Cancel your own cast first.',
   'Use it when your pet is low and you are not.'])

E('DRUID', '熊形态', 'Bear', None,
  '#showtooltip\n/dismount\n/cast !{Bear Form}',
  '一键变熊；骑着坐骑也直接变。', 'Shifts to Bear, even straight off a mount.',
  ['图标显示「熊形态」。', '先下坐骑（骑马时按它不用手动下马）。',
   '切成熊形态；已经在熊形态时按它不会把你变回来。'],
  ['The icon shows Bear Form.', 'Dismounts first, so it works while mounted.',
   'Shifts into Bear; pressing it again will not cancel the form.'])

E('DRUID', '豹形态', 'Cat', None,
  '#showtooltip\n/dismount\n/cast !{Cat Form}',
  '一键变豹；骑着坐骑也直接变。', 'Shifts to Cat, even straight off a mount.',
  ['图标显示「猎豹形态」。', '先下坐骑。', '切成豹形态；已经变着时按它不会把你变回来。'],
  ['The icon shows Cat Form.', 'Dismounts first.',
   'Shifts into Cat; pressing it again will not cancel the form.'])

E('DRUID', '自我治疗', 'Self Heal', None,
  '#showtooltip\n/cancelform\n/cast [@mouseover,help,nodead][help,nodead][@player] {Regrowth|Rejuvenation}',
  '退形态给友方/自己加血。', 'Leaves your form and heals a friendly target or yourself.',
  ['图标显示当前会用的那道治疗。', '先退出熊/豹形态（人形才能施法）。',
   '优先级：鼠标指向的友方 → 当前目标 → 你自己；学会愈合之后优先用它。'],
  ['The icon shows which heal will be used.', 'Leave Bear or Cat Form first (you cannot cast in form).',
   'Order: friendly mouseover, then target, then yourself; prefers Regrowth once you have it.'])


def render(e, level='4'):
    body = e['body'].replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
    out = ["        dict(level=%s, name_cn='%s', name_en='%s', legacy=%s,"
           % (level, e['cn'], e['en'],
              ("None" if not e['legacy'] else "'%s'" % e['legacy'])),
           "             body='%s'," % body,
           "             what_cn='%s', what_en='%s'," % (e['what_cn'], e['what_en'])]
    for key, arr in (('explain_cn', e['ec']), ('explain_en', e['ee'])):
        out.append("             %s=[%s]," % (key, "\n" + "\n".join(
            "                         '%s'," % x.replace("'", "\\'") for x in arr)))
        out[-1] = out[-1][:-1] + "]"
    out[-1] = out[-1][:-1] + "),"
    return "\n".join(out) + "\n"


def class_span(src, cls):
    m = re.search(r"\n    '%s': \[\n" % cls, src)
    if not m:
        return None
    end = src.find("\n    ],\n", m.end())
    if end < 0:
        return None
    return (m.start(), end + len("\n    ],\n"))


def main(apply):
    total = 0
    done = set()
    for path in (r'_temp\cc_mac.py', r'_temp\cc_mac2.py'):
        s = open(path, encoding='utf-8').read()
        for cls in ('WARRIOR', 'PALADIN', 'HUNTER', 'ROGUE', 'PRIEST', 'SHAMAN', 'MAGE', 'WARLOCK', 'DRUID'):
            span = class_span(s, cls)
            if not span:
                continue
            seg = s[span[0]:span[1]]
            for (ecls, cn), e in ENTRIES.items():
                if ecls != cls or (ecls, cn) in done:
                    continue
                pat = re.compile(r"        dict\(level=\d+, name_cn='%s'.*?\n             explain_en=\[.*?\]\),\n"
                                 % re.escape(cn), re.S)
                m = pat.search(seg)
                if not m:
                    continue
                lv = re.search(r"dict\(level=(\d+)", m.group(0))
                seg = seg[:m.start()] + render(e, lv.group(1) if lv else '4') + seg[m.end():]
                done.add((ecls, cn))
                total += 1
            s = s[:span[0]] + seg + s[span[1]:]
        if apply:
            open(path, 'w', encoding='utf-8', newline='\n').write(s)
    print('改写条目：%d / %d' % (total, len(ENTRIES)))
    miss = [k for k in ENTRIES if k not in done]
    if miss:
        print('未命中：%s' % miss)
    if not apply:
        print('（dry-run，未落盘；加 --apply 写盘）')


if __name__ == '__main__':
    main('--apply' in sys.argv)
