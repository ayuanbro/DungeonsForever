# -*- coding: utf-8 -*-
"""挖掘场上游更新落库（2026-10-03）：boss 打法 + 技能行 + trash + 掉落 273029。

数据源：wowhead 指南页 2026-10-03 版（_wh_excavation_guide3.html）
  · 盐脊：裂筋 3604 + 尘暴 1316382（命中 -25%，10 码）
  · 暗齿：撕裂 12054 + 恐吓咆哮 14100（5 秒不可驱散恐惧）+ 狂怒 18501（30%）；带 2 只灌木丛猎人 260801
  · 遗迹守卫者：雷霆一击 15588（10 码重减速+伤害）；开场按「档案面板」机关
  · trash：盐脊区草丛 = 宝可梦式刷新（260800 潜行者 / 260802 女家长低血尖叫召援）
  · 掉落：遗迹守卫者 +273029（远程武器）→ 10 件
幂等：重复执行报告 [SAME]。
"""
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = r'D:/workspace/DungeonsForever'


def load(p):
    with open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def save(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


# ── 1. _batch19/excavation_wetlands_guide.json ─────────────────────────────
p = ROOT + '/_temp/_batch19/excavation_wetlands_guide.json'
d = json.load(open(p, encoding='utf-8'))
meta = d['meta']
meta['tagline']['zh'] = '湿地上方维尔加挖掘场一带被蓝雾笼罩的新挖掘场：失控的泰坦构造体在此苏醒，共 4 个 boss。'
meta['tagline']['en'] = meta['tagline']['en'].replace("Whelgar's Excavation", "Whelgar's Excavation")
meta['tips'][0] = {
    'en': 'The dungeon is listed at levels 24-29 (Group Finder says 26-33) and is now open in the beta — boss strategies below follow Wowhead\'s tested writeup and will be re-checked as the beta moves on.',
    'zh': '副本 24-29 级（Group Finder 列为 26-33），beta 已开放 —— 下列 boss 打法以 wowhead 实测稿为准，随版本更新持续核对。',
}
meta['entrance']['H'] = meta['entrance']['H'].replace('威尔加', '维尔加')
meta['entrance']['A'] = [s.replace('威尔加', '维尔加') for s in meta['entrance']['A']]
meta['trash'] = [
    {
        'title': {'en': 'Living grass (Pokémon mechanic)', 'zh': '会「刷怪」的草丛'},
        'text': {
            'en': 'The most dangerous section is the grass around Saltspine: Thicket Lurkers (260800) are not stealthed — walking through tall grass spawns them, Pokémon-style. Thicket Matriarchs (260802) are spread around the area and screech for Lurker reinforcements at low health. Stay out of the grass, take the narrow path, fight in open areas, and when fighting Matriarchs kill the non-Matriarch mobs first so the screech summons as few extras as possible.',
            'zh': '整个副本最危险的区域是盐脊一带的草丛：灌木丛潜行者（#260800）并不是潜行在草里 —— 在草丛中走动几步就会像宝可梦遇敌一样直接刷新接战。灌木丛女家长（#260802）散布在周边，血量低时会尖叫召唤潜行者支援。应对：别踩草、走窄道、在开阔区接怪；与非女家长的怪群作战时先速杀非女家长，让尖叫召出的增援尽量少。',
        },
    },
    {
        'title': {'en': 'Themed packs', 'zh': '按区域分主题的怪群'},
        'text': {
            'en': 'The creatures inside are raptors (Thicket Lurker, Thicket Hunter, Thicket Matriarch), crocolisks, Highland spiders, a bog beast (Highland Creeper) and turtles — their names match the four areas.',
            'zh': '副本内的原生生物包括迅猛龙（灌木丛潜行者、灌木丛猎人、灌木丛女家长）、鳄鱼、高地蜘蛛、沼泽兽（高地爬行者）与陆行龟 —— 名字与四个区域一一对应。',
        },
    },
]
AB = {
    'Saltspine': [3604, 1316382],
    'Shadetooth': [12054, 14100, 18501],
    'Highland Horror': [],
    'Relic Guardian': [15588],
}
TEXTS = {
    'Saltspine': {
        'en': 'A very simple fight as long as you clear out the nearby mobs first. Saltspine casts Thunder Clap (3604) on the tank — a heavy slow that does not change how you play — and periodically Dust Storm (1316382) on everyone within 10 yards, reducing attacks\' chance to hit by 25%; casters should stay out of melee range.',
        'zh': '先清干净盐脊周边的小怪，这场战斗本身非常简单。它会不断对坦克施放「裂筋」（#3604），减速很重但不影响整体打法；周期性对 10 码内的目标施放「尘暴」（#1316382），命中几率降低 25% —— 远程职业别站在近战位里。',
    },
    'Shadetooth': {
        'en': 'Shadetooth is joined by two Thicket Hunters (260801); fighting all three at once is very difficult unless overleveled — either CC the adds for the whole fight, or CC one and kill the other first. Dispel the Hunters\' poison quickly. Once only the boss remains: Tendon Rip (12054) hits the tank moderately, and Terrifying Roar (14100) is a 5-second undispellable fear — easy to get feared into grass-spawned raptors or uncleared adds. Clear the crocodile cove to the left and fight there; the Hunters cannot swim, so dragging the boss back into the previous boss area resets it. The boss can be slowed and stunned, which is especially useful during Frenzy (18501) below 30%.',
        'zh': '暗齿带着两只灌木丛猎人（#260801）现身，同时硬打三个目标非常吃力 —— 要么全程把小怪控制住单点 boss，要么控制一个先集火杀掉另一个；猎人对当前目标施放的毒要尽快驱散。只剩 boss 后注意两点：「撕裂」（#12054）对坦克伤害不低；「恐吓咆哮」（#14100）是 5 秒不可驱散的恐惧 —— 很容易被恐进草丛里刷新的迅猛龙或没清完的小怪群。清空左侧的鳄鱼湾、把 boss 拉到那片开阔区打；灌木丛猎人不会游泳，把它拖回上一个 boss 的区域会直接重置战斗。boss 可以被减速和眩晕 —— 它 30% 血以下进入「狂怒」（#18501）时尤其有用。',
    },
    'Highland Horror': {
        'en': 'Wowhead\'s guide has no dedicated strategy box for this fight. It is the target of the Alliance quest "Horrors in the Highland" — kill it inside the dungeon and bring the root core back to Rethiel the Greenwarden.',
        'zh': 'wowhead 指南没有为它单列打法。它是联盟任务「高地的恐怖」的猎杀目标 —— 在副本内击杀后拾取可怕的根核，带回给绿色守卫者雷希耶尔。战斗机制以实机为准。',
    },
    'Relic Guardian': {
        'en': 'The encounter starts by pressing the Archival Panel on the right side of the inactive boss. This is a gear and level check: the difficulty comes from high tank damage and a large health pool. The boss casts Thunder Clap (15588) on everyone within 10 yards — a heavy movement/attack-speed slow plus moderate damage. The tank is periodically knocked back and sometimes stunned for 5 seconds. The boss can be stunned and slowed: use CC liberally and kite between the nearby structures.',
        'zh': '战斗从按下未激活 boss 右侧的「档案面板」机关开始。这是一场装备与等级的检查：难点是它对坦克的高伤害和大血池。它会对 10 码内的所有人施放「雷霆一击」（#15588），大幅减速移动与攻击速度并造成中等伤害；坦克还会周期性被击退、偶尔被眩晕 5 秒。boss 可以被眩晕与减速 —— 勤交控制技能，也可以利用附近的建筑卡位风筝。',
    },
}
for b in d['bosses']:
    b['abilities'] = AB[b['en']]
    b['text'] = TEXTS[b['en']]
json.dump(d, open(p, 'w', encoding='utf-8', newline=''), ensure_ascii=False, indent=1)
print('[OK] excavation_wetlands_guide.json 4 boss 打法/abilities + tips/trash/entrance 更新')

# ── 2. _wh_guide_raw.json（gen_boss_skills 输入） ──────────────────────────
p = ROOT + '/_temp/_wh_guide_raw.json'
d = json.load(open(p, encoding='utf-8'))
ex = d['excavation_wetlands']
for b in ex:
    ex[b]['spells'] = AB.get(b, [])
    if b in TEXTS:
        ex[b]['text'] = TEXTS[b]['en']
json.dump(d, open(p, 'w', encoding='utf-8', newline=''), ensure_ascii=False, indent=1)
print('[OK] _wh_guide_raw.json excavation spells/text 更新')

# ── 3. _wh_spell_icons.json + 6 slug ──────────────────────────────────────
p = ROOT + '/_temp/_wh_spell_icons.json'
d = json.load(open(p, encoding='utf-8'))
icons = {3604: 'ability_criticalstrike', 12054: 'ability_gouge', 14100: 'ability_devour',
         18501: 'spell_shadow_unholyfrenzy', 15588: 'spell_nature_thunderclap',
         1316382: 'spell_shadow_mindsteal'}
added = [k for k in icons if str(k) not in d and k not in d]
for k, v in icons.items():
    if str(k) not in d and k not in d:
        d[str(k)] = v
json.dump(d, open(p, 'w', encoding='utf-8', newline=''), ensure_ascii=False, indent=1)
print('[OK] _wh_spell_icons.json +', len(added), 'slug')
