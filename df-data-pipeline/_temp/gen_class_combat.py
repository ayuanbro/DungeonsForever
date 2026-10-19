# -*- coding: utf-8 -*-
"""生成职业指南「战斗数据」：Core/Data/Data_ClassCombat.lua + Core/Data/enUS/Data_ClassCombat.lua。

数据源（都在 _temp/，本脚本自包含，不依赖客户端）：
    cc_spells.py  法术登记表（等级 + 各等级段 ID，九职业）
    cc_rot.py     各专精有序输出循环（中英说明）
    cc_mac.py     各职业宏命令（中英用途与逐行讲解）

zhTW 副本由 _temp/gen_zhtw_data.py 自动产出；enUS 由本脚本直出（英文为人工对齐文本），
故 gen_enus_data.py 的 ENUS_EXCLUDE 已收录本文件名。

用法：python gen_class_combat.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from cc_spells import SPELLS  # noqa: E402
from cc_rot_wow import ROT  # noqa: E402
from cc_mac import MACROS  # noqa: E402

DF = os.path.dirname(HERE)
DST_CN = os.path.join(DF, 'Core', 'Data', 'Data_ClassCombat.lua')
DST_EN = os.path.join(DF, 'Core', 'Data', 'enUS', 'Data_ClassCombat.lua')

CLASS_ORDER = ['WARRIOR', 'PALADIN', 'HUNTER', 'ROGUE', 'PRIEST', 'SHAMAN', 'MAGE', 'WARLOCK', 'DRUID']

HEAD_CN = ''

HEAD_EN = ''


def lua_str(s):
    return '"%s"' % (s.replace('\\', '\\\\').replace('"', '\\"')
                     .replace('\n', '\\n').replace('\r', ''))


def indent(n):
    return '    ' * n


def spells_block():
    out = []
    for cls in CLASS_ORDER:
        out.append(indent(2) + '%s = {' % cls)
        for name in sorted(SPELLS[cls]):
            ids = SPELLS[cls][name]
            out.append(indent(3) + '{ %s, %s },'
                       % (lua_str(name), ', '.join(str(i) for i in ids)))
        out.append(indent(2) + '},')
    return '\n'.join(out)


def level_of(cls, name):
    e = SPELLS.get(cls, {}).get(name)
    return int(e[0]) if e else 0


ROT_EN_NOTE = {}


def rot_block(spec_key):
    out = []
    for cls in CLASS_ORDER:
        specs = ROT.get(cls) or {}
        out.append(indent(2) + '%s = {' % cls)
        for spec in sorted(specs):
            out.append(indent(3) + '%s = {' % spec)
            out.append(indent(4) + 'note = %s,' % lua_str(specs[spec].get('note') or ''))
            for col in ('st', 'aoe'):
                rows = specs[spec].get(col) or []
                out.append(indent(4) + '%s = {' % col)
                for row in rows:
                    note = row[2] if spec_key == 'cn' else row[1]
                    out.append(indent(5) + '{ spell = %s, note = %s },'
                               % (lua_str(row[0]), lua_str(note)))
                out.append(indent(4) + '},')
            out.append(indent(3) + '},')
        out.append(indent(2) + '},')
    return '\n'.join(out)


def mac_block(spec_key):
    out = []
    for cls in CLASS_ORDER:
        out.append(indent(2) + '%s = {' % cls)
        for m in MACROS[cls]:
            nk = 'name_cn' if spec_key == 'cn' else 'name_en'
            wk = 'what_cn' if spec_key == 'cn' else 'what_en'
            ek = 'explain_cn' if spec_key == 'cn' else 'explain_en'
            legacy = m['legacy']
            out.append(indent(3) + '{ level = %d, name = %s, legacy = %s,'
                       % (m['level'], lua_str(m[nk]),
                          lua_str(legacy) if legacy else 'nil'))
            out.append(indent(4) + 'body = %s,' % lua_str(m['body']))
            out.append(indent(4) + 'what = %s,' % lua_str(m[wk]))
            out.append(indent(4) + 'explain = {')
            for line in m[ek]:
                out.append(indent(5) + '%s,' % lua_str(line))
            out.append(indent(4) + '} },')
        out.append(indent(2) + '},')
    return '\n'.join(out)


def build(head, spec_key, guard=None):
    parts = [head, '', 'local _, ns = ...', '']
    if guard:
        parts += [guard, '']
    parts += [
        'ns.ClassCombat = {',
        indent(1) + 'meta = { patch = "1.60.1", level = 60, ranks = "game-client" },',
        '',
        indent(1) + 'spells = {',
        spells_block(),
        indent(1) + '},',
        '',
        indent(1) + 'rotation = {',
        rot_block(spec_key),
        indent(1) + '},',
        '',
        indent(1) + 'macros = {',
        mac_block(spec_key),
        indent(1) + '},',
        '}',
        '',
    ]
    return '\n'.join(parts)


EN_GUARD = 'if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end'


def main():
    cn = build(HEAD_CN, 'cn')
    en = build(HEAD_EN, 'en', EN_GUARD)
    open(DST_CN, 'w', encoding='utf-8', newline='\n').write(cn)
    open(DST_EN, 'w', encoding='utf-8', newline='\n').write(en)
    n_rot = sum(len(v) for c in ROT.values() for v in c.values())
    n_mac = sum(len(v) for v in MACROS.values())
    print('Data_ClassCombat.lua: %d 字节（%d 专精循环 %d 条 / %d 宏）'
          % (len(cn.encode('utf-8')), sum(len(v) for v in ROT.values()), n_rot, n_mac))
    print('enUS/Data_ClassCombat.lua: %d 字节' % len(en.encode('utf-8')))


if __name__ == '__main__':
    main()
