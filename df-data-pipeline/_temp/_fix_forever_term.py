# -*- coding: utf-8 -*-
"""_cg_trans/*.json 版本名术语归一：把 wowhead 英文 Forever / WoW Forever 的误译
（简/繁「永恒·永恆」「永久」、以及未翻译的 latin「Forever」/《Forever》/《WoW Forever》）
统一改写为本项目版本/服务器的中文名「无限」，并做空白规整。

- 仅命中「版本指代」语境（书名号版本名、服指代、版/版本、in Forever 短语、固定标题短语）。
- 放过副词性「永久」（永久提高 / 永久提升 / 永久（性地）重做·重新设计 = permanently）；
  唯 wowhead 原句 “…changed for Forever” 两处经英文核对属版本指代，另列纠正。
- 裸「永恒/永恆」按版本指代处理，但加 (?!之) 负向保护（「永恒之井」等专名不受影响）。
- 归一后做一次空白规整：版本名前后不留半角空格。
- 原始文件按文本级替换改写，保留 JSON 原有缩进/转义格式。

用法：python _temp/_fix_forever_term.py
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, '_cg_trans')

CANON_TITLE = '无限服新增的职业-种族组合'

# ① 固定标题短语（wowhead races 板块标题 “New Class-Race Combinations Available for
#    Forever” 的各种误译/半译形态）——文本级字面替换，最先执行。
TITLE_LITERALS = [
    '永久》可用的全新职业—种族组合',
    '《永久》新增可用的职业—种族组合',
    '经典永恒版本新增的种族与职业组合',
    '《永恒》版本可用的全新种族职业组合',
    '《永恒》新增的职业-种族组合',
    '《永恒》新增的职业与种族组合',
    '《永久》新增的职业-种族组合',
    '永久新增的种族-职业组合',
    '永久开放的新职业种族组合',
    '永久开放全新职业-种族组合',
    '永久开放全新的种族-职业组合',
    '永久可用的全新种族-职业组合',
    '永久开放的全新种族-职业组合',
    '全新职业-种族组合永久开放',
    '全新职业种族组合永久开放',
    '永恒服新增可用的职业-种族组合',
    '《永久经典》中开放的新职业-种族组合',
    '新增的种族与职业组合(适用于《永恒》)',
    'Forever 中新增的职业-种族组合',
    'Forever中可用的新职业-种族组合',
    '《Forever》新增的职业与种族组合',
]

# ② 英文核对后确认属「版本指代」（EN: "…changed for Forever"）的整句纠正。
PHRASE_LITERALS = [
    ('所有专业都已被永久重做', '所有专业都已随《无限》重做'),
    ('所有专业都被永久性地重新设计了', '所有专业都已随《无限》重做'),
]

# ③ 通用版本指代规则（顺序敏感：长/具体在前）。命中「版本指代」，放过副词性「永久」。
REGEX_RULES = [
    # 全称（含书名号）
    (r'《WoW\s*[Ff]orever》', '《魔兽世界：无限》'),
    (r'《魔兽世界[：:·]\s*(?:[Ff]orever|永恒|永恆|永久)》', '《魔兽世界：无限》'),
    # 简称（书名号，先长后短）
    (r'《[Ff]orever》', '《无限》'),
    (r'《永久经典》', '《无限》'),
    (r'《永久[ _]?[bB]eta》', '无限测试服'),
    (r'《永恒》', '《无限》'),
    (r'《永恆》', '《无限》'),
    (r'《永久》', '《无限》'),
    # 全称（无书名号）
    (r'魔兽世界[：:·]经典永恒版本', '《魔兽世界：无限》'),
    (r'WoW[：:]?\s*[Ff]orever', '《魔兽世界：无限》'),
    (r'魔兽世界[：:·]?\s*[Ff]orever', '魔兽世界：无限'),
    (r'魔兽世界[：:·]?\s*(?:永恒|永恆)', '魔兽世界：无限'),
    (r'魔兽世界[：:·]?\s*永久', '魔兽世界：无限'),
    # 残缺书名号（译文丢左书名号）
    (r'(?:永恒|永恆|永久)》', '《无限》'),
    # 引号式简称
    (r'“(?:永恒|永恆)”版本', '《无限》版本'),
    (r'“永久”版本', '《无限》版本'),
    # beta
    (r'[Ff]orever\s*[Bb]eta', '无限测试服'),
    (r'《无限》测试服', '无限测试服'),
    # in Forever（含 latin）
    (r'在\s*[Ff]orever\s*中', '在无限服中'),
    (r'于\s*[Ff]orever\s*中', '于无限服中'),
    # 服务器指代
    (r'《永久》怀旧服', '无限服'),
    (r'永久经典怀旧服', '无限服'),
    (r'永久怀旧服', '无限服'),
    (r'(?:永恒|永恆)服', '无限服'),
    (r'永久服', '无限服'),
    (r'永久魔兽', '无限服'),
    (r'[Ff]orever\s*服', '无限服'),
    # 版 / 版本
    (r'经典永恒版本', '无限版本'),
    (r'(?:永恒|永恆)版本', '无限版本'),
    (r'永久版本', '无限版本'),
    (r'[Ff]orever\s*版本', '无限版本'),
    (r'(?:永恒|永恆)版', '无限版'),
    (r'永久版', '无限版'),
    # 裸 in 短语（限定「中/里」，避免误伤副词）
    (r'(?:永恒|永恆)里', '无限服里'),
    (r'(?:永恒|永恆)中', '无限服中'),
    (r'永久中', '无限服中'),
    (r'永久里', '无限服里'),
    # 裸「永恒/永恆」（负向保护「…之…」专名）
    (r'(?:永恒|永恆)(?!之)', '《无限》'),
    # 兜底：未翻译的 latin Forever
    (r'[Ff]orever', '《无限》'),
]

# ④ 空白规整：版本名前后不留半角空格（相邻非空格为 CJK 或 CJK 标点时）。
_TOKENS = r'(?:《魔兽世界：无限》|无限测试服|无限版本|无限服|无限版|《无限》)'
_CJK_L = r'[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]'
WS_LEFT = re.compile(r'(?<=' + _CJK_L + r')[ \t]+(?=' + _TOKENS + r')')
WS_RIGHT = re.compile(r'(' + _TOKENS + r')[ \t]+(?=' + _CJK_L + r')')


def apply_rules(text):
    """对单条文本串应用标题字面 + 整句纠正 + 通用正则 + 空白规整，返回 (新文本, 命中数)。"""
    n = 0
    for lit in TITLE_LITERALS:
        if lit in text:
            text = text.replace(lit, CANON_TITLE)
            n += 1
    for old, new in PHRASE_LITERALS:
        if old in text:
            text = text.replace(old, new)
            n += 1
    for rx, rep in REGEX_RULES:
        text, k = re.subn(rx, rep, text)
        n += k
    text, k = WS_LEFT.subn('', text)
    n += k
    text, k = WS_RIGHT.subn(r'\1', text)
    n += k
    return text, n


def main():
    grand = 0
    files = 0
    for f in sorted(os.listdir(D)):
        if not f.endswith('.json'):
            continue
        p = os.path.join(D, f)
        raw = io.open(p, encoding='utf-8').read()
        new, n = apply_rules(raw)
        if n:
            io.open(p, 'w', encoding='utf-8', newline='\n').write(new)
            files += 1
            grand += n
            print('  %-32s 替换 %2d 处' % (f, n))
    print('共 %d 文件、%d 处替换' % (files, grand))


if __name__ == '__main__':
    main()
