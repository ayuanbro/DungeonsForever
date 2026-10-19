# -*- coding: utf-8 -*-
"""R7 修复：Skyborne 统一 + 中英夹杂补译。默认 dry-run（打印逐条 before→after，不落盘）。
用法：python _r7_fix.py [--apply]
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TD = os.path.join(HERE, '_cg_trans')
APPLY = '--apply' in sys.argv

# ---- 全局短语替换（纯字符串，长词在前） ----
PH = [
    # Skyborne 拉丁短语（长在前）
    ('Skyborne Elves', '天裔精灵'),
    ('Skyborne Elf', '天裔精灵'),
    ('High Order Skyborne', '高阶天裔'),
    ('Windshaper Skyborne', '掠风天裔'),
    ('Alliance Skyborne', '联盟天裔'),
    ('Skyborne（天裔）', '天裔'),
    ('Skyborne', '天裔'),
    # CN 侧 Skyborne 各种写法 → 规范名（长在前）
    ('掠风天空裔', '掠风天裔'),
    ('尊主天空裔', '高阶天裔'),
    ('高空天行者', '高阶天裔'),
    ('天空之裔', '天裔'),
    ('天空之灵', '天裔'),
    ('天空之民', '天裔'),
    ('天空之城', '天裔'),
    ('天空行者', '天裔'),
    ('天裔族', '天裔'),
    ('天空裔', '天裔'),
    ('空中族', '天裔'),
    ('天翔族', '天裔'),
    ('天生族', '天裔'),
    ('空中精灵', '天裔'),
    ('驭风者', '天裔'),
    ('驭空', '天裔'),
]

# ---- 全局词替换（正则，词边界；顺序敏感：debuff 先于 buff） ----
WORD = [
    (r'(?<![A-Za-z])debuff(?![A-Za-z])', '减益'),
    (r'(?<![A-Za-z])buff(?![A-Za-z])', '增益'),
    (r'(?<![A-Za-z])BUFF(?![A-Za-z])', '增益'),
    (r'(?<![A-Za-z])endgame(?![A-Za-z])', '终局'),
    (r'(?<![A-Za-z])incoming damage(?![A-Za-z])', '承受伤害'),
    (r'(?<![A-Za-z])GCD(?![A-Za-z])', '公共冷却'),
    (r'(?<![A-Za-z])Natural Talent(?![A-Za-z])', '天生特质'),
    (r'(?<![A-Za-z])tinkers(?![A-Za-z])', '工程道具'),
    (r'(?<![A-Za-z])build(?![A-Za-z])', '流派'),
]

# ---- 收尾：替换词两侧 ASCII 空格若旁为 CJK 则合并 ----
_CJK = r'\u4e00-\u9fff'
_GLUE = r'(?:天裔|减益|增益|终局|工程道具|天生特质|承受伤害|公共冷却|流派|看情况|神圣保护|回响|吸取生命|灵魂链接)'
CLEAN = [
    (re.compile(r'([%s])\s+(%s)' % (_CJK, _GLUE)), r'\1\2'),
    (re.compile(r'(%s)\s+([%s])' % (_GLUE, _CJK)), r'\1\2'),
]

# ---- 定向替换（spec, key, idx）→ [(find, repl)]，作用于该元素全部字符串 ----
TARGETED = {
    ('mage_arcane', 'races', 0): [('虚空精灵', '天裔精灵')],
    ('mage_fire', 'races', 0): [('凤凰', '天裔精灵')],
    ('paladin_protection', 'changes', 2): [('、 protection和', '、神圣保护和')],
    ('paladin_retribution', 'changes', 2): [('在与Samanarr合作时，', ''), ('“Echo”', '“回响”')],
    ('warlock_affliction', 'viability', 0): [('SL/SL', '吸取生命/灵魂链接')],
    ('warlock_demonology', 'viability', 0): [('SL/SL', '吸取生命/灵魂链接')],
    ('warlock_demonology', 'beginner', 0): [
        ('在拥有|s17924|时施放|s440870|up。', '在|s440870|生效时施放|s17924|。')],
    ('warlock_destruction', 'viability', 0): [
        ('|s25307|to|s1293813|. ', '|s25307|变为|s1293813|。')],
    ('warlock_destruction', 'sw', 0): [
        ('|s18932|and|s18871|. ', '|s18932|和|s18871|。'),
        ('|s11684|and|s11678|', '|s11684|和|s11678|')],
    ('warlock_destruction', 'sw', 1): [('|s18871|and|s18932|', '|s18871|和|s18932|')],
    ('shaman_elemental', 'races', 6): [
        ('\u0003- 天裔的种族特长\u0004', '\u0003天裔\u0004'),
        ('空中翱翔的种族特长', '天裔的种族特长')],
    ('warlock_affliction', 'races', 8): [('虽然 situational，但', '虽然要看情况，但')],
    ('priest_shadow', 'sw', 1): [('团本raid', '团本')],
}

CHANGES = []


def apply_global(s):
    orig = s
    for a, b in PH:
        if a in s:
            s = s.replace(a, b)
    for pat, b in WORD:
        s = re.sub(pat, b, s)
    for rx, b in CLEAN:
        s = rx.sub(b, s)
    if s != orig:
        CHANGES.append(('GLOBAL', orig, s))
    return s


def apply_targeted(s, rules):
    orig = s
    for a, b in rules:
        if a in s:
            s = s.replace(a, b)
    if s != orig:
        CHANGES.append(('TARGET', orig, s))
    return s


def transform(o, fn):
    if isinstance(o, str):
        return fn(o)
    if isinstance(o, list):
        return [transform(x, fn) for x in o]
    if isinstance(o, dict):
        return {k: transform(v, fn) for k, v in o.items()}
    return o


def main():
    specs = sorted(f[:-5] for f in os.listdir(TD) if f.endswith('.json'))
    total_changed_files = 0
    for spec in specs:
        p = os.path.join(TD, spec + '.json')
        raw = io.open(p, encoding='utf-8').read()
        obj = json.loads(raw)
        # 全局
        new = transform(obj, apply_global)
        # 定向
        for (s2, key, idx), rules in TARGETED.items():
            if s2 != spec:
                continue
            for sec in new.get('sections', []):
                if sec.get('key') != key:
                    continue
                fl = sec.get('flow', [])
                if idx < len(fl):
                    fl[idx] = transform(fl[idx], lambda x: apply_targeted(x, rules))
        out = json.dumps(new, ensure_ascii=False, indent=1)
        if out != raw:
            total_changed_files += 1
            if APPLY:
                io.open(p, 'w', encoding='utf-8').write(out)
    print('changed files = %d  (apply=%s)' % (total_changed_files, APPLY))
    # 输出变更明细
    seen = set()
    lines = []
    for tag, a, b in CHANGES:
        if (a, b) in seen:
            continue
        seen.add((a, b))
        lines.append('[%s] %s\n      -> %s' % (tag, a, b))
    with io.open(os.path.join(HERE, '_r7_fix_diff.txt'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('diff lines = %d  -> _r7_fix_diff.txt' % len(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
