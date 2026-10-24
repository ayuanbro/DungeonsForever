# -*- coding: utf-8 -*-
"""职业指南页 · 职业排行数据管线：wowhead 无限服三页排行 → Core/Data/Data_ClassTier.lua。

一条命令跑完全链（抓取 → 解析 → 落盘）。

抓取纪律（本机约定，2026-09-29 实测）：
- 该站有 CloudFront 地区封锁 + AWS WAF 双层。可用姿势只有一条：
  curl_cffi + impersonate='chrome110' + 完整浏览器头 + 7897 代理。
  只带 impersonate='chrome' 且缺完整头时会被 WAF 挡在 202 挑战页（实测连挂 3 轮）。
- 正文**不在 HTML 里**：<div id="guide-body"> 是空的，内容由
  WH.markup.printHtml("<json 字符串>", "guide-body", …) 注入。
  故从该 JS 字符串字面量 json.loads 出 BBCode 风格 markup 再解析。
- 梯队表开标签是 `[tier-list=rows]`（不是 `[tier-list]`）。
- 缓存 _tier_probe/<key>.html；缺页现抓，串行 + 退避。

产物只落三类东西：专精键（职业枚举名 + 专精短键）、档位归属、文本说明。
专精名与图标走本文件的 SPEC_DIR 静态目录（客户端没有跨版本稳定的「专精枚举 → 名称」接口）。

用法：
    python _temp/fc_tier.py              # 有缓存用缓存
    python _temp/fc_tier.py --force      # 无视缓存强制重抓
    python _temp/fc_tier.py --offline    # 只用缓存，不联网（回归用）
"""
import argparse
import json
import os
import re
import sys
import time

PROXY = 'http://127.0.0.1:7897'
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '_tier_probe')
DST = os.path.join(os.path.dirname(HERE), 'Core', 'Data', 'Data_ClassTier.lua')

URLS = [
    ('dps', 'https://www.wowhead.com/forever/cn/guide/classes/tier-lists/dps-pve-rankings'),
    ('tank', 'https://www.wowhead.com/forever/cn/guide/classes/tier-lists/tank-pve-rankings'),
    ('healer', 'https://www.wowhead.com/forever/cn/guide/classes/tier-lists/healer-pve-rankings'),
]

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.wowhead.com/forever/cn',
}

# 产物级红线（与 AGENTS.md 同口径）：这些词出现即拒落盘
LEAK = ['站点', '出处', '上游', '参考', '照抄', '抄它', '剥离', '抽取段',
        'foreverchanges', 'ForeverChanges', 'AtlasQuest']

# ── ① 专精目录：职业枚举名 → 三个专精（顺序与游戏内天赋树一致）────────────────
# icon 走客户端 Interface\Icons 全路径；路径不存在的图标客户端会画成空图，
# 查不到就留空，界面回落问号兜底。
SPEC_DIR = [
    ('WARRIOR', [
        ('arms',  '武器', 'Arms',          r'Interface\\Icons\\ability_warrior_savageblow'),
        ('fury',  '狂怒', 'Fury',          r'Interface\\Icons\\ability_warrior_innerrage'),
        ('prot',  '防护', 'Protection',    r'Interface\\Icons\\ability_warrior_defensivestance'),
    ]),
    ('PALADIN', [
        ('holy',  '神圣', 'Holy',          r'Interface\\Icons\\Spell_Holy_HolyBolt'),
        ('prot',  '防护', 'Protection',    r'Interface\\Icons\\Spell_Holy_DevotionAura'),
        ('ret',   '惩戒', 'Retribution',   r'Interface\\Icons\\Spell_Holy_AuraOfLight'),
    ]),
    ('HUNTER', [
        ('bm',    '兽王', 'Beast Mastery', r'Interface\\Icons\\Ability_Hunter_BeastTaming'),
        ('mm',    '射击', 'Marksmanship',  r'Interface\\Icons\\Ability_Marksmanship'),
        ('surv',  '生存', 'Survival',      r'Interface\\Icons\\Ability_Hunter_SwiftStrike'),
    ]),
    ('ROGUE', [
        ('assa',  '奇袭', 'Assassination', r'Interface\\Icons\\ability_rogue_eviscerate'),
        ('combat', '战斗', 'Combat',       r'Interface\\Icons\\ability_backstab'),
        ('sub',   '敏锐', 'Subtlety',      r'Interface\\Icons\\ability_stealth'),
    ]),
    ('PRIEST', [
        ('disc',  '戒律', 'Discipline',    r'Interface\\Icons\\spell_holy_wordfortitude'),
        ('holy',  '神圣', 'Holy',          r'Interface\\Icons\\spell_holy_guardianspirit'),
        ('shadow', '暗影', 'Shadow',       r'Interface\\Icons\\spell_shadow_shadowwordpain'),
    ]),
    ('SHAMAN', [
        ('ele',   '元素', 'Elemental',     r'Interface\\Icons\\spell_nature_lightning'),
        ('enh',   '增强', 'Enhancement',   r'Interface\\Icons\\spell_nature_lightningshield'),
        ('resto', '恢复', 'Restoration',   r'Interface\\Icons\\Spell_Nature_HealingWaveGreater'),
    ]),
    ('MAGE', [
        ('arcane', '奥术', 'Arcane',       r'Interface\\Icons\\inv_misc_rune_03'),
        ('fire',  '火焰', 'Fire',          r'Interface\\Icons\\spell_fire_firebolt02'),
        ('frost', '冰霜', 'Frost',         r'Interface\\Icons\\spell_frost_frostbolt02'),
    ]),
    ('WARLOCK', [
        ('affli', '痛苦', 'Affliction',    r'Interface\\Icons\\spell_shadow_deathcoil'),
        ('demo',  '恶魔', 'Demonology',    r'Interface\\Icons\\spell_shadow_metamorphosis'),
        ('destro', '毁灭', 'Destruction',  r'Interface\\Icons\\spell_shadow_rainoffire'),
    ]),
    ('DRUID', [
        ('balance', '平衡', 'Balance',     r'Interface\\Icons\\spell_nature_starfall'),
        ('feral', '野性', 'Feral',         r'Interface\\Icons\\ability_racial_bearform'),
        ('resto', '恢复', 'Restoration',   r'Interface\\Icons\\Spell_Nature_HealingTouch'),
    ]),
]

# ② 排行页上的专精标识 → (职业枚举名, 专精短键)
SLUG_CLASS = {
    'warrior': 'WARRIOR', 'paladin': 'PALADIN', 'hunter': 'HUNTER',
    'rogue': 'ROGUE', 'priest': 'PRIEST', 'shaman': 'SHAMAN',
    'mage': 'MAGE', 'warlock': 'WARLOCK', 'druid': 'DRUID',
}
SPEC_ALIAS = {
    'beast-mastery': 'bm', 'marksmanship': 'mm', 'survival': 'surv',
    'arcane': 'arcane', 'fire': 'fire', 'frost': 'frost',
    'enhancement': 'enh', 'elemental': 'ele', 'restoration': 'resto',
    'retribution': 'ret', 'protection': 'prot', 'holy': 'holy',
    'arms': 'arms', 'fury': 'fury',
    'subtlety': 'sub', 'assassination': 'assa', 'combat': 'combat',
    'feral': 'feral', 'balance': 'balance',
    'demonology': 'demo', 'affliction': 'affli', 'destruction': 'destro',
    'shadow': 'shadow', 'discipline': 'disc',
}

# ③ 页面文案（wowhead 原文的中文译文；正文里的法术节点已还原成名字）
TEXT = {
    'dps': {
        'intro': '本页依据伤害输出与为队伍带来的价值，对无限服的输出专精进行排名。',
        'factors': [
            ('输出强度', '该专精为队伍贡献的伤害量。'),
            ('增益价值', '该专精为队友带来的增益。'),
            ('非增益价值', '更难量化的价值，例如在危急时临时充当坦克。'),
            ('生存价值', '权重较小的一项，但倒下的输出等于没有输出；默认就能打得更安全，也意味着能更长时间黏在目标身上。'),
        ],
        'notes': [
            '在此等级段，各专精之间的差距很小（少数例外除外），因此分档更多代表职业，而不一定代表单个专精。',
            '本排行基于当前测试版本，且严格限定在等级上限 30 的范围内；一切都还可能调整，本页会随之更新。',
            '请谨慎看待这份榜单：它只是一次关于「哪些专精更有价值」的讨论，不该用来决定你玩哪个专精，也不该用来决定让公会里的人玩哪个专精。',
            '需要注意的是，即便你的专精排得比预期低，无限服的所有输出专精都能打通全部内容，只是会比高排名专精更吃力一些。',
            '实际表现因人、因场合而异。最明显的例子是法师与术士：在这个等级段它们拥有全游戏最高的群体伤害，但如果队伍一次只拉 2 到 3 只怪，法师的优势就会被大幅掩盖；猎人在这种环境下极强，但群体伤害较弱。',
            '总体而言，除法师与术士这两个特例，等级 30 的物理输出表现最好。法系大体还能跟上，但主要靠高价值的持续伤害效果或群体伤害大招，其余时间基本在丢魔杖。',
            '平衡德在垫底位置比较特殊，因为它没有任何丢魔杖的输出手段，不过它能给坦克上一个高法术强度的荆棘术作为补偿。',
        ],
    },
    'tank': {
        'intro': '本页依据单体与群体拉怪能力，以及为队伍提供的增益、减益、大招等价值，对无限服的坦克专精进行排名。',
        'factors': [
            ('生存能力', '作为主坦承受高伤害的能力，包括减伤技能、大招、整体耐久与自我维持手段。'),
            ('伤害与仇恨', '在保证生存、履行主坦职责的前提下，该专精能打出的伤害与能建立的仇恨量。'),
            ('小怪与群拉', '主要看群体仇恨的建立能力与小怪阶段的生存能力。'),
            ('团队增益', '该专精对整支队伍有帮助的价值。'),
        ],
        'notes': [
            '每个坦克都有比别的坦克更擅长或更吃力的场景，排名高并不代表它在所有方面都强。但在等级 30，群体仇恨与群体伤害的价值远高于满级阶段，这会让榜单产生偏移。',
            '荣誉提名：增强萨具备一定的坦克支援能力，但没有完整的坦克工具箱。作为地下城坦克完全够用、甚至不错，但带萨满坦去打更难的内容并不明智。',
            '本排行基于当前测试版本，且严格限定在等级上限 30 的范围内；一切都还可能调整，本页会随之更新。',
            '请谨慎看待这份榜单：它只是一次关于「哪些专精更有价值」的讨论，不该用来决定你玩哪个专精，也不该用来决定让公会里的人玩哪个专精。',
            '如上所述，分档时考虑了不少方面，但某个坦克实际好不好用，还取决于你在打什么内容、队伍或团队需要什么。',
            '话虽如此，无限服的所有内容用任何坦克专精都能通关。每个坦克都有自己的定位；若某个坦克变得不好用，通常也会拿到调整，被拉回与其他坦克相近的水平。',
            '保护圣骑在等级 30 格外突出：它能用上二级奉献，惩罚光环随法术强度成长，再加上盾牌专精这类天赋，法力顾虑基本消除，它从不缺仇恨，多数时候都能稳定待在伤害榜首位；新到手的 30 级大招圣殿骑士壁垒，在前期也比其他坦克的大招价值更高。',
            '防护战士与野性德的表现同样不差。战士通过复仇这类技能拥有更高的仇恨系数，如今还能在防御姿态下使用雷霆一击；盾牌格挡不耗怒气、冷却又短，让他们体感更扎实——毕竟其他坦克还没有同等工具。',
            '德鲁伊可以自己上荆棘术，这在等级 30 伤害很高，也有能提升挥击伤害的天赋——挥击目前虽不吃攻击强度加成，但官方已确认后续测试版本会补上；即便没有攻强加成，靠野性本能与野蛮暴怒这类天赋，它依然能打出可观的伤害。野德在等级 30 还能用上原始之咬与兽群领袖，价值巨大。',
        ],
    },
    'healer': {
        'intro': '本页依据治疗与吸收输出、功能性与整体表现，对无限服的治疗专精进行排名。',
        'factors': [
            ('治疗与吸收', '该专精在治疗或预防伤害方面的表现，也就是坦克与团队会承受的那部分伤害。'),
            ('法力效率', '该专精治疗时的效率，以及有多容易遇到法力不足。'),
            ('大招覆盖', '该专精应对高额伤害期或其他棘手情况的大招。'),
            ('团队增益', '该专精对整支队伍有帮助的增益与功能性。'),
            ('输出贡献', '在战斗允许的前提下，该专精能为团队贡献多少伤害。'),
        ],
        'notes': [
            '本排行基于当前测试版本，且严格限定在等级上限 30 的范围内；一切都还可能调整，本页会随之更新。',
            '请谨慎看待这份榜单：它只是一次关于「哪些专精更有价值」的讨论，不该用来决定你玩哪个专精，也不该用来决定让公会里的人玩哪个专精。',
            '需要注意，即便你的专精排得比预期低，无限服的所有治疗专精都能打通全部内容。',
            '这份榜单想给出各治疗专精强度的一个基准认知。值得一提的是，本次治疗之间的平衡比以往版本接近得多，不同首领与环境下各有所长。',
            '如上所述，分档时考虑了不少方面，但治疗实际好不好用，取决于你的团队是在刷已通关的团本，还是在首次推进。',
            '所有治疗专精在测试服的表现都不错，但各自工具箱的差异影响了排名。牧师整体表现良好，点出魔杖专精后可以在不消耗法力、也不打断 5 秒回蓝规则的情况下打出相当可观的伤害；它法力效率高、产出也强，真言术：盾在关头时刻同样关键——尤其它现在不再阻止战士与德鲁伊产生怒气。',
            '恢复萨是扎实的治疗者，它带来的图腾也很有价值，但在拿到风怒图腾之前，它缺少其他治疗免费提供的那部分伤害；话虽如此，萨满用灼热图腾与火焰新星同样能打出不错的伤害。在等级 30 它法力效率很高，能让队伍保持节奏而不必停下回蓝；还可以顺便下增强系点出强化风暴打击与精神敏锐（配合传承系统拿到的额外天赋点），让它既能轻松应付野外，又是一个能打出有竞争力伤害的强力治疗。',
            '恢复德之所以突出有两个主要原因：一是它拥有非常全面的工具箱，持续性治疗强劲、法力回复高；二是在当前法术强度成长下，给坦克上的荆棘术价值极高。',
            '神圣骑拥有惩罚光环，作用与荆棘术类似。不过在等级 30，它的治疗产出与法力回复都略低于其他治疗，靠大量增益与功能性来补足。',
        ],
    },
}

# 梯队档位自上而下；wowhead 用品质色标档，D 档通常为空
TIER_KEYS = ['S', 'A', 'B', 'C', 'D']


def die(msg):
    sys.stderr.write('fc_tier: %s\n' % msg)
    sys.exit(1)


# ── ④ 抓取 ──────────────────────────────────────────────────────────────────

def fetch(key, url, force, offline):
    dst = os.path.join(CACHE, key + '.html')
    if not force and os.path.exists(dst) and os.path.getsize(dst) > 20000:
        return 'cached'
    if offline:
        die('缓存缺失且指定了 --offline：%s' % dst)
    try:
        from curl_cffi import requests as cr
    except ImportError:
        die('需要 curl_cffi：pip install curl_cffi')
    s = cr.Session(impersonate='chrome110',
                   proxies={'http': PROXY, 'https': PROXY}, headers=HEADERS)
    os.makedirs(CACHE, exist_ok=True)
    for attempt in range(4):
        if attempt:
            time.sleep(20)
        try:
            r = s.get(url, timeout=40)
        except Exception as e:
            print('   [err] %s %s' % (key, str(e)[:80]))
            continue
        if r.status_code == 200 and len(r.text) > 20000:
            with open(dst, 'w', encoding='utf-8') as f:
                f.write(r.text)
            return 'fetched %d' % len(r.text)
        print('   [%s] %s len=%d' % (key, r.status_code, len(r.text)))
    die('抓取失败：%s' % url)


# ── ⑤ 解析 ──────────────────────────────────────────────────────────────────

def braces_json(h, start):
    i = h.index('{', start)
    depth, in_str, esc = 0, False, False
    for j in range(i, len(h)):
        c = h[j]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return h[i:j + 1]
    return '{}'


def parse(path):
    """从缓存页取出梯队结构。返回 [{key, specs=[(class, spec)]}, ...]（含空档）。"""
    h = open(path, encoding='utf-8').read()
    m = re.search(r'WH\.markup\.printHtml\(\s*("(?:[^"\\]|\\.)*")', h, re.S)
    if not m:
        die('找不到正文 markup：%s' % path)
    mk = json.loads(m.group(1))
    tl = re.search(r'\[tier-list[^\]]*\](.*?)\[/tier-list\]', mk, re.S)
    if not tl:
        die('找不到梯队表：%s' % path)
    found = {}
    for tier in re.finditer(r'\[tier\](.*?)\[/tier\]', tl.group(1), re.S):
        blk = tier.group(1)
        lab = re.search(r'\[tier-label[^\]]*\]\s*([A-Za-z][+-]?)\s*\[/tier-label\]', blk)
        if not lab:
            continue
        out = []
        for slug in re.findall(r'\[spec-badge=([a-z0-9\-]+)\]', blk):
            parts = slug.split('-')
            cls = SLUG_CLASS.get(parts[-1])
            spec = SPEC_ALIAS.get('-'.join(parts[:-1]))
            if not cls or not spec:
                die('未知专精标识：%s' % slug)
            out.append((cls, spec))
        found[lab.group(1).upper()] = out
    return [{'key': k, 'specs': found.get(k, [])} for k in TIER_KEYS]


def esc(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')


def lua_str(s):
    return '"%s"' % esc(s)


# ── ⑥ 落盘 ──────────────────────────────────────────────────────────────────

HEAD = '''local _, ns = ...
ns.ClassTier = {'''


def build_lua(tiers_by_page):
    out = [HEAD]
    out.append('    meta = {\n')
    out.append('        patch = "1.60.1",\n')
    out.append('        level = 30,\n')
    out.append('        updated = "2026/10/06",\n')
    out.append('    },\n\n')
    out.append('    specs = {\n')
    for cls, specs in SPEC_DIR:
        out.append('        %s = {\n' % cls)
        for key, name, nameen, icon in specs:
            out.append('            { key = "%s", name = %s, nameEn = "%s", icon = "%s" },\n'
                       % (key, lua_str(name), nameen, icon))
        out.append('        },\n')
    out.append('    },\n\n')
    out.append('    pages = {\n')
    for key, _ in URLS:
        t = TEXT[key]
        out.append('        {\n')
        out.append('            key = "%s",\n' % key)
        out.append('            intro = %s,\n' % lua_str(t['intro']))
        out.append('            tiers = {\n')
        for tier in tiers_by_page[key]:
            if tier['specs']:
                items = ', '.join('{ class = "%s", spec = "%s" }' % (c, s)
                                  for c, s in tier['specs'])
                out.append('                { key = "%s", specs = { %s } },\n'
                           % (tier['key'], items))
            else:
                out.append('                { key = "%s", specs = {} },\n' % tier['key'])
        out.append('            },\n')
        out.append('            factors = {\n')
        for name, desc in t['factors']:
            out.append('                { %s, %s },\n' % (lua_str(name), lua_str(desc)))
        out.append('            },\n')
        out.append('            notes = {\n')
        for n in t['notes']:
            out.append('                %s,\n' % lua_str(n))
        out.append('            },\n')
        out.append('        },\n')
    out.append('    },\n')
    out.append('}\n')
    return ''.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--offline', action='store_true')
    args = ap.parse_args()

    os.makedirs(CACHE, exist_ok=True)
    tiers_by_page = {}
    for key, url in URLS:
        st = fetch(key, url, args.force, args.offline)
        tiers = parse(os.path.join(CACHE, key + '.html'))
        tiers_by_page[key] = tiers
        stat = ' / '.join('%s:%d' % (t['key'], len(t['specs'])) for t in tiers)
        print('[%s] %-22s %s' % (key, st, stat))

    lua = build_lua(tiers_by_page)
    for w in LEAK:
        if w in lua:
            die('产物含禁用词「%s」，拒落盘' % w)
    with open(DST, 'w', encoding='utf-8', newline='\n') as f:
        f.write(lua)
    print('→ %s  %d 行' % (DST, lua.count('\n')))


if __name__ == '__main__':
    main()
