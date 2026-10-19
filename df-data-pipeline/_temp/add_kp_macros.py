# -*- coding: utf-8 -*-
"""按 KP_MacTol 的成熟写法给职业宏加条目 / 升级指派链。

来源对照（写法取自 KP_MacTol，技能换成我们 30 级能用的，占位符走本方体系）：
  冲锋/拦截合一   ← KP「冲锋/拦截/援护」（两行式：先切姿态再施放）
  潜行/消失合一   ← KP「潜行/消失」（[nocombat]潜行 / [combat]消失）
  水陆形态         ← KP「一键旅行形态(智能)」（条件切形态）
  一键团盾         ← KP「一键团盾(找队友盾)」（/targetfriendplayer + 回切目标）
  造水造食双键     ← KP「宝石制作使用」（[button:1]/[button:2] 一键双功能）
  饰品爆发         ← KP「一键爆发」的 /use 13 + /use 14
  治疗指派链       ← KP「圣光滚轮」（鼠标指向→焦点→目标→自己）

用法：python _temp/add_kp_macros.py [--apply]
"""
import re
import sys

ADD = {}      # (cls, 插入位置序号或 None=追加) -> [entry dict]
MOD = {}      # (cls, name_cn) -> explain 替换


def A(cls, **kw):
    ADD.setdefault(cls, []).append(kw)


TRINKET_CN = ['饰品爆发', '饰品爆发']
TRINKET_BODY = '#showtooltip\n/use 13\n/use 14'


def trinket(cls, lv):
    return dict(level=lv, cn='饰品爆发', en='Trinkets', legacy=None, body=TRINKET_BODY,
                what_cn='一个键同时开两个饰品。', what_en='Fires both trinkets with one key.',
                ec=['图标显示第一个饰品。', '使用饰品栏 1。', '使用饰品栏 2。'],
                ee=['The icon shows your first trinket.', 'Uses trinket slot 1.', 'Uses trinket slot 2.'])


A('WARRIOR', level=20, cn='冲锋拦截', en='Charge & Intercept', legacy=None,
  body='#showtooltip [combat] {Intercept}; {Charge}\n/startattack\n/cast [combat,nostance:3] {Berserker Stance}\n/cast [combat] {Intercept}; {Charge}',
  what_cn='不在战斗就冲锋，战斗中拦截，一个键两用。',
  what_en='Charges out of combat, Intercepts in combat — one key for both.',
  ec=['图标跟着显示这次会放哪个（战斗中显示「拦截」）。', '先开始普攻。',
      '战斗中且不在狂暴姿态时先切过去（要按两下）。', '不在战斗就冲锋，战斗中拦截。'],
  ee=['The icon follows the situation (Intercept in combat).', 'Starts auto-attacking.',
      'Switches to Berserker Stance first when needed (press twice).',
      'Charge out of combat, Intercept in combat.'])

A('ROGUE', level=22, cn='潜行消失', en='Stealth & Vanish', legacy=None,
  body='#showtooltip [combat] {Vanish}; {Stealth}\n/stopattack\n/cast [combat] {Vanish}; !{Stealth}',
  what_cn='不在战斗进潜行，战斗中直接消失。', what_en='Stealth out of combat, Vanish in combat.',
  ec=['图标跟着显示这次会放哪个（战斗中显示「消失」）。', '先停止攻击，免得刚潜就被打出来。',
      '不在战斗进潜行（连按不会取消）；战斗中直接消失脱战。'],
  ee=['The icon follows the situation (Vanish in combat).', 'Stop attacking first so you are not knocked out.',
      'Stealth out of combat (spamming will not cancel it); Vanish in combat.'])

A('DRUID', level=20, cn='水陆形态', en='Swim or Run', legacy=None,
  body='#showtooltip [swimming] {Aquatic Form}; {Travel Form}\n/dismount\n/cancelform\n/cast [swimming] {Aquatic Form}; {Travel Form}',
  what_cn='水里切水栖形态，陆地上切旅行形态。', what_en='Aquatic Form in water, Travel Form on land.',
  ec=['图标跟着显示这次会变哪个（水里显示「水栖形态」）。', '先下坐骑。', '退出当前形态。',
      '在水里切水栖形态，否则切旅行形态。'],
  ee=['The icon follows the situation (Aquatic Form in water).', 'Dismount first.',
      'Leave your current form.', 'Aquatic Form in water, otherwise Travel Form.'])

A('PRIEST', level=6, cn='一键团盾', en='Raid Shield', legacy=None,
  body='#showtooltip {Power Word: Shield}\n/targetfriendplayer\n/cast [help,nodead] {Power Word: Shield}\n/targetlasttarget',
  what_cn='自动选中最近的队友套盾，然后切回原目标。',
  what_en='Shields the nearest party member, then swaps back to your old target.',
  ec=['图标显示「真言术：盾」。', '自动选中最近的队友（包括队友的宠物）。',
      '给他套盾。', '切回原来的目标。'],
  ee=['The icon shows Power Word: Shield.', 'Targets the nearest party member.',
      'Shields them.', 'Swaps back to your previous target.'])

TRINKET_LEVEL = {'WARRIOR': 30, 'PALADIN': 30, 'HUNTER': 30, 'ROGUE': 30, 'PRIEST': 30,
                 'SHAMAN': 30, 'MAGE': 30, 'WARLOCK': 30, 'DRUID': 30}

HEAL_CHAIN_OLD = '[@mouseover,help,nodead][help,nodead][@player]'
HEAL_CHAIN_NEW = '[@mouseover,help,nodead][@focus,help,nodead][help,nodead][@player]'
HEAL_EX_CN = ['图标显示当前会用的那道治疗。',
              '优先级：鼠标指向的友方 → 焦点（把队友设成焦点就能一直照看他）→ 当前目标 → 你自己。']
HEAL_EX_EN = ['The icon shows which heal will be used.',
              'Order: friendly mouseover, then your focus (set a teammate as focus to keep them covered), then target, then yourself.']



A('WARRIOR', level=40, cn='嗜血或致死', en='Bloodthirst / Mortal Strike', legacy=None,
  body='#showtooltip {Bloodthirst|Mortal Strike}\n/startattack\n/cast {Bloodthirst|Mortal Strike}',
  what_cn='40 级的主力伤害技：狂怒用嗜血，武器/防护用致死打击。',
  what_en='Your level-40 main hit: Bloodthirst for Fury, Mortal Strike otherwise.',
  ec=['图标显示当前会用的那个（跟着你学到的走）。', '同时开始普攻。', '打出主力伤害技。'],
  ee=['The icon shows which one will fire.', 'Starts auto-attacking at the same time.', 'Casts your main hit.'])

A('WARRIOR', level=36, cn='旋风斩', en='Whirlwind', legacy=None,
  body='#showtooltip {Whirlwind}\n/startattack\n/cast {Whirlwind}',
  what_cn='旋风斩，多目标时很划算。', what_en='Whirlwind, great against several targets.',
  ec=['图标显示「旋风斩」。', '先开始普攻。', '施放旋风斩（狂暴姿态）。'],
  ee=['The icon shows Whirlwind.', 'Starts auto-attacking.', 'Casts Whirlwind (Berserker Stance).'])

A('PALADIN', level=34, cn='圣盾术', en='Divine Shield', legacy=None,
  body='#showtooltip {Divine Shield}\n/stopcasting\n/cast {Divine Shield}',
  what_cn='掐读条开无敌，硬吃一波。', what_en='Cancels your cast and pops Divine Shield.',
  ec=['图标显示「圣盾术」。', '先掐掉正在读的法术。', '开无敌，短时间内几乎免伤。'],
  ee=['The icon shows Divine Shield.', 'Cancel your cast first.', 'Pops the bubble to soak a burst.'])

A('PALADIN', level=44, cn='愤怒之锤', en='Hammer of Wrath', legacy=None,
  body='#showtooltip {Hammer of Wrath}\n/cast [@mouseover,harm,nodead][] {Hammer of Wrath}',
  what_cn='斩杀锤：目标血量低时打，鼠标指向优先。',
  what_en='Executioner hammer; works on low-health targets, mouseover first.',
  ec=['图标显示「愤怒之锤」。', '优先打鼠标指向的敌人；没指向时打当前目标。'],
  ee=['The icon shows Hammer of Wrath.', 'Hits your mouseover first, otherwise your current target.'])

A('HUNTER', level=34, cn='爆炸陷阱', en='Explosive Trap', legacy=None,
  body='#showtooltip {Explosive Trap}\n/cast [@cursor] {Explosive Trap}',
  what_cn='直接在鼠标位置下陷阱，省掉落地那一下。',
  what_en='Drops the trap at your cursor, skipping the ground click.',
  ec=['图标显示「爆炸陷阱」。', '鼠标指哪放哪，不用再点一次地面。'],
  ee=['The icon shows Explosive Trap.', 'It lands wherever your cursor is, no ground click needed.'])

A('HUNTER', level=40, cn='箭雨', en='Volley', legacy=None,
  body='#showtooltip {Volley}\n/cast [@cursor] {Volley}',
  what_cn='鼠标位置下箭雨。', what_en='Rains arrows wherever your cursor is.',
  ec=['图标显示「箭雨」。', '鼠标指哪打哪。'],
  ee=['The icon shows Volley.', 'It lands wherever your cursor is.'])

A('PRIEST', level=32, cn='暗言术：灭', en='Shadow Word: Death', legacy=None,
  body='#showtooltip {Shadow Word: Death}\n/cast [@mouseover,harm,nodead][] {Shadow Word: Death}',
  what_cn='斩杀技：目标血量低时用它收尾。', what_en='Your execute; use it to finish low targets.',
  ec=['图标显示「暗言术：灭」。', '优先打鼠标指向的敌人；没指向时打当前目标。'],
  ee=['The icon shows Shadow Word: Death.', 'Hits your mouseover first, otherwise your current target.'])

A('PRIEST', level=40, cn='愈合祷言', en='Prayer of Mending', legacy=None,
  body='#showtooltip {Prayer of Mending}\n/cast [@mouseover,help,nodead][@focus,help,nodead][help,nodead][@player] {Prayer of Mending}',
  what_cn='挂上愈合祷言，它会自己跳到下一个受伤的队友身上。',
  what_en='Applies Prayer of Mending, which hops to the next hurt teammate on its own.',
  ec=['图标显示「愈合祷言」。', '优先级：鼠标指向 → 焦点 → 当前目标 → 你自己。'],
  ee=['The icon shows Prayer of Mending.', 'Order: mouseover, then focus, then target, then yourself.'])

A('SHAMAN', level=32, cn='闪电链', en='Chain Lightning', legacy=None,
  body='#showtooltip {Chain Lightning}\n/cast {Chain Lightning}',
  what_cn='多目标用法术，会连锁到附近敌人。', what_en='Hits several enemies, chaining to nearby ones.',
  ec=['图标显示「闪电链」。', '施放闪电链，会自动跳到旁边的敌人身上。'],
  ee=['The icon shows Chain Lightning.', 'It jumps on to nearby enemies by itself.'])

A('SHAMAN', level=32, cn='风怒图腾', en='Windfury Totem', legacy=None,
  body='#showtooltip {Windfury Totem}\n/cast {Windfury Totem}',
  what_cn='给近战组放风怒图腾。', what_en='Drops Windfury for your melee group.',
  ec=['图标显示「风怒图腾」。', '在脚下放风怒图腾，附近的近战都能吃到。'],
  ee=['The icon shows Windfury Totem.', 'Drops it at your feet so nearby melee benefit.'])

A('MAGE', level=40, cn='寒冰护体', en='Ice Barrier', legacy=None,
  body='#showtooltip {Ice Barrier}\n/stopcasting\n/cast [@player] {Ice Barrier}',
  what_cn='掐读条给自己套寒冰护体。', what_en='Cancels your cast and shields yourself.',
  ec=['图标显示「寒冰护体」。', '先掐掉正在读的法术。', '给自己套上护盾，先手接怪/被追时用。'],
  ee=['The icon shows Ice Barrier.', 'Cancel your cast first.', 'Shields yourself before a pull or while being chased.'])

A('WARLOCK', level=40, cn='恐惧嚎叫', en='Howl of Terror', legacy=None,
  body='#showtooltip {Howl of Terror}\n/stopcasting\n/cast [@player] {Howl of Terror}',
  what_cn='掐读条把周围敌人一起吓跑。', what_en='Cancels your cast and fears everything around you.',
  ec=['图标显示「恐惧嚎叫」。', '先掐掉正在读的法术。', '以自己为中心施放，把身边的敌人一起吓走。'],
  ee=['The icon shows Howl of Terror.', 'Cancel your cast first.',
      'Casts around you, sending nearby enemies running.'])

A('DRUID', level=32, cn='凶猛撕咬', en='Ferocious Bite', legacy=None,
  body='#showtooltip {Ferocious Bite}\n/cast {Ferocious Bite}',
  what_cn='猫形态的终结技，攒满连击点放。', what_en='Cat finisher; use it with combo points saved up.',
  ec=['图标显示「凶猛撕咬」。', '攒够连击点之后用它收尾。'],
  ee=['The icon shows Ferocious Bite.', 'Use it to finish once you have combo points built up.'])

A('DRUID', level=36, cn='狂暴回复', en='Frenzied Regeneration', legacy=None,
  body='#showtooltip {Frenzied Regeneration}\n/cast {Frenzied Regeneration}',
  what_cn='熊形态把怒气换成血。', what_en='Bear form: converts rage into healing.',
  ec=['图标显示「狂暴回复」。', '熊形态下怒气多、血又掉得快时用，把怒气换成血。'],
  ee=['The icon shows Frenzied Regeneration.', 'Use it in Bear form when you have rage and need health.'])

def main(apply):
    ins = 0
    for path in (r'_temp\cc_mac.py', r'_temp\cc_mac2.py'):
        s = open(path, encoding='utf-8').read()
        for cls in sorted(set(list(ADD.keys()) + list(TRINKET_LEVEL.keys()))):
            span = None
            m = re.search(r"\n    '%s': \[\n" % cls, s)
            if m:
                end = s.find("\n    ],\n", m.end())
                span = (m.end(), end + 1)
            if not span:
                continue
            seg = s[span[0]:span[1]]
            add = []
            for e in ADD.get(cls, []):
                add.append(e)
            if cls in TRINKET_LEVEL and not any('饰品爆发' in x for x in re.findall(r"name_cn='([^']*)'", seg)):
                add.append(dict(trinket(cls, TRINKET_LEVEL[cls])))
            if add:
                txt = []
                for e in add:
                    txt.append(render(e))
                seg = seg.rstrip('\n') + '\n' + "".join(txt)
                ins += len(add)
            s = s[:span[0]] + seg + s[span[1]:]
        if apply:
            open(path, 'w', encoding='utf-8', newline='\n').write(s)
    print('新增条目：%d' % ins)
    if not apply:
        print('（dry-run，未落盘；加 --apply 写盘）')


def render(e):
    body = e['body'].replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
    out = ["        dict(level=%s, name_cn='%s', name_en='%s', legacy=%s,"
           % (e['level'], e['cn'], e['en'], ("None" if not e.get('legacy') else "'%s'" % e['legacy'])),
           "             body='%s'," % body,
           "             what_cn='%s', what_en='%s'," % (e['what_cn'], e['what_en'])]
    for key, arr in (('explain_cn', e['ec']), ('explain_en', e['ee'])):
        out.append("             %s=[" % key)
        for x in arr:
            out.append("                         '%s'," % x.replace("'", "\\'"))
        out.append("             ],")
    txt = "\n".join(out)
    idx = txt.rfind("             ],")
    txt = txt[:idx] + "             ])," + txt[idx + len("             ],"):]
    return txt + "\n"


if __name__ == '__main__':
    main('--apply' in sys.argv)
