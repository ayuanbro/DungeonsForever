# -*- coding: utf-8 -*-
"""一次性脚本：把 Core/Data/Data_LootFilter.lua 的 D.Presets 由「排除式」翻成「需求式」。

口径：useX = D.ClassUsable[该 preset 所属职业][x] 减去 这一套的 notUseX。
       —— 用 ClassUsable 当全集，天然不会把「其他武器 / 杂项武器 / 钓鱼竿」这类
          垃圾项混进「我需要」，避免 UI 上出现"需要钓鱼竿"这种荒谬勾选。

只就地替换每套的 notUseWeapon/notUseArmor 两行，其余（icon / name / useShuXing /
Tank / MainAttribute / 注释 / 排版）原样保留，最小化 diff。

用法：python lf_gen_presets.py            # 只打印 before/after，不改文件
      python lf_gen_presets.py --apply    # 实际写回
"""
import re
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), 'Core', 'Data', 'Data_LootFilter.lua')

CLASSES = ["WARRIOR", "PALADIN", "DEATHKNIGHT", "SHAMAN", "HUNTER",
           "ROGUE", "DRUID", "MONK", "MAGE", "WARLOCK", "PRIEST"]


def parse_names(seg):
    """从 `{ "a", "b", ... }` 里取出名称列表（保序）。"""
    return re.findall(r'"([^"]*)"', seg)


def parse_class_usable(text):
    """解析 D.ClassUsable：class → { 'weapon': [...], 'armor': [...] }。"""
    m = re.search(r'D\.ClassUsable = \{(.*?)\n\}\n', text, re.S)
    if not m:
        raise SystemExit('找不到 D.ClassUsable 块')
    body = m.group(1)
    out = {}
    for cm in re.finditer(
            r'([A-Z]+) = \{\s*weapon = \{([^}]*)\},\s*armor = \{([^}]*)\},\s*\}', body, re.S):
        out[cm.group(1)] = {'weapon': parse_names(cm.group(2)),
                            'armor': parse_names(cm.group(3))}
    return out


def find_preset_block(text):
    start = text.index('D.Presets = {')
    tail = '\n}\n\n-- 界面铺勾选框用'
    end = text.index(tail, start)
    return start, end + len('\n}')


PRESET_RE = re.compile(
    r'\{ icon = (ICON\.[A-Za-z_]+), name = "([^"]*)",\s*\n'
    r'\s*notUseWeapon = \{([^}]*)\},\s*\n'
    r'\s*notUseArmor = \{([^}]*)\},\s*\n'
    r'\s*useShuXing = (\{[^}]*\}), Tank = (\{[^}]*\}), MainAttribute = (\{[^}]*\}) \},'
)


def wrap_array(prefix_indent, field, names, width=104):
    """把名称列表排版成 `field = { "a", "b", ... },`，过长则换行（续行对齐 `{ `）。"""
    head = '%s%s = { ' % (prefix_indent, field)
    if not names:
        return head + '},'
    one = head + ', '.join('"%s"' % n for n in names) + ' },'
    if len(one) <= width:
        return one
    cont = ' ' * len(head)
    lines, cur = [], head
    for i, n in enumerate(names):
        piece = '"%s"' % n
        sep = ', ' if i < len(names) - 1 else ''
        if len(cur) + len(piece) + len(sep) > width and cur.strip() != field + ' = {':
            lines.append(cur.rstrip())
            cur = cont + piece + sep
        else:
            cur += piece + sep
    lines.append(cur + ' }')
    return '\n'.join(lines) + ','


def main():
    text = open(SRC, encoding='utf-8').read()
    usable = parse_class_usable(text)
    missing = [c for c in CLASSES if c not in usable]
    if missing:
        raise SystemExit('ClassUsable 缺职业: %s' % missing)

    start, end = find_preset_block(text)
    block = text[start:end]

    # 记录每个职业头的位置，用于判定某 preset 归属哪个职业
    heads = [(m.start(), m.group(1))
             for m in re.finditer(r'^    ([A-Z]+) = \{$', block, re.M)]

    def owner(pos):
        cur = None
        for p, c in heads:
            if p < pos:
                cur = c
            else:
                break
        return cur

    count = 0
    per_class = {}
    report = []

    def repl(m):
        nonlocal count
        icon, name, nw, na, shu, tank, main = m.groups()
        cls = owner(m.start())
        if cls is None:
            raise SystemExit('无法判定职业: %s' % name)
        use_all_w = usable[cls]['weapon']
        use_all_a = usable[cls]['armor']
        notuse_w = set(parse_names(nw))
        notuse_a = set(parse_names(na))
        uw = [n for n in use_all_w if n not in notuse_w]
        ua = [n for n in use_all_a if n not in notuse_a]
        if not uw:
            raise SystemExit('useWeapon 为空: %s' % name)
        if not ua:
            raise SystemExit('useArmor 为空: %s' % name)
        count += 1
        per_class[cls] = per_class.get(cls, 0) + 1
        report.append((cls, name, parse_names(nw), uw, parse_names(na), ua))

        indent = '          '
        out = ('{ icon = %s, name = "%s",\n' % (icon, name)
               + wrap_array(indent, 'useWeapon', uw) + '\n'
               + wrap_array(indent, 'useArmor', ua) + '\n'
               + '%suseShuXing = %s, Tank = %s, MainAttribute = %s },' % (indent, shu, tank, main))
        return out

    new_block = PRESET_RE.sub(repl, block)

    print('=== before(notUseX) → after(useX) 逐套核对 ===')
    for cls, name, nw, uw, na, ua in report:
        print('%-12s %-14s' % (cls, name))
        print('    Weapon  -%2d %s' % (len(nw), '/'.join(nw) or '∅'))
        print('        =>   +%2d %s' % (len(uw), '/'.join(uw)))
        print('    Armor   -%2d %s' % (len(na), '/'.join(na) or '∅'))
        print('        =>   +%2d %s' % (len(ua), '/'.join(ua)))
    print()
    print('共转出 %d 套；各职业: %s' % (
        count, ' '.join('%s=%d' % (c, per_class.get(c, 0)) for c in CLASSES)))
    if count != 33:
        raise SystemExit('期望 33 套，实际 %d 套' % count)
    if any(v == 0 for v in per_class.values()):
        raise SystemExit('有职业套数为 0')

    new_text = text[:start] + new_block + text[end:]

    if '--apply' in sys.argv:
        with open(SRC, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new_text)
        print('\n[已写回] %s' % SRC)
    else:
        print('\n[dry-run] 未写文件；加 --apply 落盘')


if __name__ == '__main__':
    main()
