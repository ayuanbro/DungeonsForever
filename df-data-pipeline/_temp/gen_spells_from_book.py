# -*- coding: utf-8 -*-
"""从天赋插件的技能书数据重建我方法术登记表（cc_spells.py）。

来源：TalentsForever/Core/Data/Data_SpellBook.lua（ns.SpellBookData）
      该文件自述数据来源 foreverchanges.pro / Forever Beta 1.60.1.70425，覆盖 1~60 级。
字段：name / nameEn / id / learnLv / ranks[{rank, learn, id}]
我方格式：'EnglishName': (learnLv, id1, id2, ...)  —— 与运行期 BaseId/KnownId 口径一致

用法：python gen_spells_from_book.py [--apply]
"""
import os
import re
import sys

from lupa import LuaRuntime

BOOK = r'D:/Game/World of Warcraft/_cn_beta_/Interface/AddOns/TalentsForever/Core/Data/Data_SpellBook.lua'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cc_spells.py')
CLASSES = ['WARRIOR', 'PALADIN', 'HUNTER', 'ROGUE', 'PRIEST', 'SHAMAN', 'MAGE', 'WARLOCK', 'DRUID']


def load_book():
    src = open(BOOK, encoding='utf-8').read()
    L = LuaRuntime(unpack_returned_tuples=True)
    f = L.eval('function(ns, src) local fn = load(src); fn("TalentsForever", ns); return ns end')
    ns = L.table()
    ns.IsTitan = True
    return f(ns, src).SpellBookData


def collect(book):
    out = {}
    for cls in CLASSES:
        c = book.classes[cls]
        if c is None:
            continue
        tb = {}
        for _, tab in c.tabs.items():
            spells = tab.spells
            if spells is None:
                continue
            for _, sp in spells.items():
                en = sp.nameEn
                if not en or en == '':
                    continue
                lv = int(sp.learnLv or 0)
                ids = []
                ranks = sp.ranks
                if ranks is not None and len(ranks) > 0:
                    rows = []
                    for _, r in ranks.items():
                        rows.append((int(r.rank or 0), int(r.id or 0)))
                    rows.sort()
                    ids = [i for _rk, i in rows if i > 0]
                else:
                    ids = [int(sp.id or 0)]
                ids = [i for i in ids if i > 0]
                if not ids:
                    continue
                old = tb.get(en)
                if old:
                    base = old[1]
                    lv = min(lv, base) if base else lv
                    merged = sorted(set(list(old[2:]) + ids))
                    tb[en] = tuple([lv] + merged)
                else:
                    tb[en] = tuple([lv] + ids)
        out[cls] = tb
    return out


def lua_str(s):
    return '"%s"' % s.replace('\\', '\\\\').replace('"', '\\"')


def emit(table):
    lines = ['# -*- coding: utf-8 -*-',
             '"""法术登记表：英文名 → (学习等级, 逐级法术 ID)。',
             '',
             '数据来源：天赋插件技能书（foreverchanges.pro / Forever Beta 1.60.1.70425，覆盖 1~60 级）。',
             '由 _temp/gen_spells_from_book.py 生成，勿手改。',
             '"""',
             '',
             'SPELLS = {']
    for cls in CLASSES:
        tb = table.get(cls) or {}
        lines.append('    %r: {' % cls)
        for name in sorted(tb):
            ids = tb[name]
            lines.append('        %s: (%s),' % (lua_str(name), ', '.join(str(i) for i in ids)))
        lines.append('    },')
    lines.append('}')
    lines.append('')
    return '\n'.join(lines)


def placeholders():
    keys = set()
    base = os.path.dirname(os.path.abspath(__file__))
    for fn in ('cc_mac.py', 'cc_mac2.py', 'cc_rot_wow.py', 'cc_rot.py'):
        p = os.path.join(base, fn)
        if not os.path.exists(p):
            continue
        src = open(p, encoding='utf-8').read()
        for m in re.finditer(r"\{([A-Za-z][A-Za-z0-9:' \-]*)\}", src):
            for part in m.group(1).split('|'):
                keys.add(part.strip())
    return keys


CARRY = {}


def carry_over(new):
    src = open(OUT, encoding='utf-8').read()
    for cls in CLASSES:
        tb = new.setdefault(cls, {})
        for name in list(placeholders()):
            if name in tb or name in CARRY:
                continue
            m = re.search(r"'%s': \(([\d,\s]+)\)" % re.escape(name), src)
            if m:
                CARRY[name] = tuple(int(x) for x in m.group(1).replace(' ', '').split(',') if x)
                tb[name] = CARRY[name]
    return new


def main(apply):
    book = load_book()
    new = collect(book)
    src = open(OUT, encoding='utf-8').read()
    m = re.search(r'SPELLS = \{.*?\n\}', src, re.S)
    old = {}
    for cls in CLASSES:
        mm = re.search(r"%r: \{(.*?)\n    \}," % cls, src, re.S)
        if not mm:
            continue
        tb = {}
        for name, ids in re.findall(r'"([^"]+)": \(([\d,\s]+)\),', mm.group(1)):
            tb[name] = tuple(int(x) for x in ids.replace(' ', '').split(',') if x)
        old[cls] = tb

    print('=== 新旧对比 ===')
    tot_new = tot_old = 0
    for cls in CLASSES:
        n = len(new.get(cls) or {})
        o = len(old.get(cls) or {})
        tot_new += n
        tot_old += o
        only_new = sorted(set((new.get(cls) or {})) - set((old.get(cls) or {})))
        print('  %-8s 旧 %3d → 新 %3d  新增 %d 条%s' % (cls, o, n, len(only_new),
              (' 例：' + ', '.join(only_new[:5])) if only_new else ''))
    print('合计 旧 %d → 新 %d' % (tot_old, tot_new))

    new = carry_over(new)
    ph = placeholders()
    allkeys = set()
    for cls in CLASSES:
        allkeys |= set(new.get(cls) or {})
    miss = sorted(k for k in ph if k not in allkeys)
    print()
    print('宏/循环里引用的占位符 %d 个，新表覆盖不了 %d 个：%s' % (len(ph), len(miss), ', '.join(miss[:20])))

    if apply:
        open(OUT, 'w', encoding='utf-8', newline='\n').write(emit(new))
        print('已写入 %s' % OUT)
    else:
        print('（dry-run，未落盘；加 --apply 写盘）')


if __name__ == '__main__':
    main('--apply' in sys.argv)
