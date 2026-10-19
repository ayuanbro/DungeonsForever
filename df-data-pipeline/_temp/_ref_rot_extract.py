# -*- coding: utf-8 -*-
"""把客户端参考插件 ForeverLevelingGuide 的 ROT / MAC / WowFHechizos 抽成 JSON，供全职业数据生成用。

用法：python _temp/_ref_rot_extract.py
产物：_temp/_ref_rot.json（rot / mac / spells）
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lupa import lua51  # noqa: E402

REF = r'D:\Game\World of Warcraft\_cn_beta_\Interface\AddOns\ForeverLevelingGuide'


def load(name, tweaks=(), cut=None):
    src = open(os.path.join(REF, name), 'rb').read().decode('utf-8')
    for a, b in tweaks:
        src = src.replace(a, b, 1)
    if cut and cut in src:
        src = src[:src.index(cut)]
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(src.encode('utf-8'))
    return lua


def plain(v):
    if isinstance(v, dict):
        return {k: plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    if hasattr(v, 'keys') and hasattr(v, '__getitem__'):
        try:
            return {k: plain(v[k]) for k in v.keys()}
        except Exception:
            pass
    return v


def main():
    lua = load('wowF_Hechizos.lua')
    spells = plain(lua.globals().WowFHechizos)

    lua2 = load("wowF_Rotacion.lua", [
        ('local ROT = {', 'ROT = {'),
        ('local MAC = {', 'MAC = {'),
    ], cut='local vigia = CreateFrame')
    g = lua2.globals()
    rot = plain(g.ROT)
    mac = plain(g.MAC)

    out = {'spells': spells, 'rot': rot, 'mac': mac}
    dst = os.path.join(HERE, '_ref_rot.json')
    open(dst, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
    print('spells classes:', len(spells or {}))
    print('rot classes:', len(rot or {}))
    for c in sorted(rot or {}):
        print('  ROT %-8s specs=%s' % (c, ','.join(sorted(rot[c].keys()))))
    for c in sorted(mac or {}):
        v = mac[c]
        if isinstance(v, list):
            print('  MAC %-8s n=%d' % (c, len(v)))
    print('->', dst)


if __name__ == '__main__':
    main()
