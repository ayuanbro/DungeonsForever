# -*- coding: utf-8 -*-
"""专业数据探针：把 Core/Data/Data_Prof*.lua 的真实**键集与元组长度**全量打出来。

为什么要有它：UI（Core/ProfessionUI.lua）是按位置取值的，而位置由 fc_gen.py 的
字段序元组决定。生成器一改字段序、或某个键漏写，UI 那边是**静默读 nil**（不报错、
只是那一列空着）。这个探针把「数据实际长什么样」变成可读的一页，改 UI 前先看一眼。

用法：python prof_probe.py [slug]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
DATA = os.path.join(DF, 'Core', 'Data')
TOOLS = r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'
sys.path.insert(0, TOOLS)

from lupa import lua51  # noqa: E402
import tf_dryrun as T  # noqa: E402


def load():
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(T.STUB)
    lua.execute('TF_NS = {}')
    root = DATA.replace('\\', '/')
    ev = lua.eval('function(rel) local c = loadfile("%s/" .. rel) '
                  'return c("DungeonsForever", TF_NS) end' % root)
    for f in ('Data_Professions.lua', 'Data_ProfRecipes.lua',
              'Data_ProfLeveling.lua', 'Data_ProfGathering.lua'):
        ev(f)
    return lua


def keys(t, src=''):
    """Lua table → 排序后的键列表（数组表给长度 + 首项采样）。"""
    if t is None:
        return None
    if not hasattr(t, 'items'):
        return {'scalar': repr(t)[:120]}
    n = 0
    ks = []
    s = []
    for k, v in t.items():
        if isinstance(k, (int, float)) and float(k).is_integer():
            n += 1
        else:
            ks.append(str(k))
        s.append((k, v))
    if ks:
        return {'dict_keys': sorted(ks), 'array_len': n}
    return {'array_len': n, 'first': repr(s[0][1])[:200] if s else None}


def tlen(t):
    """数组长度（非表给 0）。"""
    if t is None or not hasattr(t, 'items'):
        return 0
    n = 0
    for k in t.keys():
        if isinstance(k, (int, float)) and float(k).is_integer():
            n += 1
    return n


def shape(t, depth=0, maxd=2, label=''):
    pad = '  ' * depth
    if t is None:
        print('%s%s = nil' % (pad, label))
        return
    if not hasattr(t, 'items'):
        print('%s%s = %r' % (pad, label, t))
        return
    k = keys(t)
    print('%s%s -> %s' % (pad, label, k))
    if depth >= maxd:
        return
    # 只递归第一个数组项，够看清元组长度
    first = t[1] if t[1] is not None else None
    if first is not None and hasattr(first, 'items'):
        print('%s  [1] 元组长度 = %d' % (pad, tlen(first)))
        print('%s  [1] = %r' % (pad, repr(first)[:400]))
    dictkeys = k.get('dict_keys')
    if dictkeys:
        for dk in dictkeys[:3]:
            shape(t[dk], depth + 1, maxd, '.%s' % dk)


def main():
    lua = load()
    ds = lua.eval('TF_NS.ProfData')
    rc = lua.eval('TF_NS.ProfRecipes')
    lv = lua.eval('TF_NS.ProfLeveling')
    ga = lua.eval('TF_NS.ProfGathering')

    want = sys.argv[1:] or None

    print('=' * 72)
    print('ProfData 顶层：%s' % keys(ds))
    for slug in (ds.order.values() if ds.order is not None else []):
        if want and slug not in want:
            continue
        p = ds.pro[slug]
        print('-' * 72)
        print('pro[%s] 键：%s' % (slug, sorted(keys(p)['dict_keys'])))
        for dk in ('kind', 'section', 'word', 'status', 'recipes', 'sub'):
            print('    %-10s = %r' % (dk, p[dk]))
        for dk in ('camp', 'miles', 'perks', 'racials', 'bonuses', 'tips', 'verify',
                   'unknowns', 'steps', 'ranks', 'kinds'):
            v = p[dk]
            if v is None:
                continue
            info = keys(v)
            print('    %-10s %s' % (dk, info))
            if info.get('array_len'):
                print('        [1] = %r' % (repr(v[1])[:400],))
        if p.cert is not None:
            print('    cert       = %r' % (repr(p.cert)[:300],))
        if p.fishing is not None:
            print('    fishing    = %s' % keys(p.fishing))
            for gk in ('spells', 'lures', 'food', 'items', 'titles'):
                if p.fishing[gk] is not None:
                    print('        %-8s len=%d  [1]=%r'
                          % (gk, len(list(p.fishing[gk].values())),
                             repr(p.fishing[gk][1])[:260]))

    print('=' * 72)
    print('ProfRecipes 顶层：%s' % keys(rc))
    for slug in (rc.items() if False else []):
        pass
    for k, v in rc.items():
        if want and k not in want:
            continue
        print('-' * 72)
        print('R[%s] 键：%s' % (k, sorted(keys(v)['dict_keys'])))
        for dk in ('word', 'counts', 'groups', 'rows', 'enchants', 'crafted', 'favor'):
            val = v[dk]
            if val is None:
                continue
            print('    %-9s %s' % (dk, keys(val)))
            if (keys(val).get('array_len') or 0) > 0:
                print('        [1] = %r' % (repr(val[1])[:400],))
        if v.counts is not None:
            print('    counts dict = %r' % (repr(v.counts)[:200],))

    print('=' * 72)
    print('ProfLeveling 顶层：%s' % keys(lv))
    for k, v in lv.items():
        if want and k not in want:
            continue
        print('-' * 72)
        print('LV[%s] 键：%s' % (k, sorted(keys(v)['dict_keys'])))
        for dk in ('note', 'steps', 'shopping', 'sold', 'quest', 'parts', 'learn',
                   'rods', 'camps', 'vendor'):
            val = v[dk]
            if val is None:
                continue
            print('    %-9s %s' % (dk, keys(val)))
            if (keys(val).get('array_len') or 0) > 0:
                print('        [1] = %r' % (repr(val[1])[:300],))
        if v.camps is not None:
            print('    camps.a = %r   camps.h = %r' % (repr(v.camps.a)[:160],
                                                       repr(v.camps.h)[:160]))
        if v.vendor is not None:
            print('    vendor.a = %r   vendor.h = %r' % (repr(v.vendor.a)[:160],
                                                         repr(v.vendor.h)[:160]))

    print('=' * 72)
    print('ProfGathering 顶层：%s' % keys(ga))
    for k, v in ga.items():
        print('    %-10s %s' % (k, keys(v)))
        if (keys(v).get('array_len') or 0) > 0:
            print('        [1] = %r' % (repr(v[1])[:300],))


if __name__ == '__main__':
    main()
