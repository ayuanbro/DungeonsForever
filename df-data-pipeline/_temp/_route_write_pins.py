# -*- coding: utf-8 -*-
"""把 _route_qicon_override.json 的任务图标位置写回 Core/Data/Data_MapPins.lua 的 quest 项

override 结构 = {dungeonId: {qid: [x, y, floor]}}；某副本整表替换其 quest 行，其余 kind 不动。
"""
import io
import json
import os
import re

from _route_paths import ROOT, TEMP, checked

PINS = checked(ROOT + '/Core/Data/Data_MapPins.lua')
OVR = checked(TEMP + '/_route_qicon_override.json')


def num(v):
    s = ('%.1f' % float(v)).rstrip('0').rstrip('.')
    return s if s else '0'


def quest_line(items):
    parts = ', '.join('{ %s, %s, %d, %d }' % (num(x), num(y), int(qid), int(fl))
                      for qid, (x, y, fl) in sorted(items.items(),
                                                    key=lambda kv: int(kv[0])))
    return '        quest = { %s },' % parts


def main():
    try:
        ovr = json.load(io.open(OVR, encoding='utf-8'))
    except Exception:
        print('no override')
        return
    if not isinstance(ovr, dict) or not ovr:
        print('override empty')
        return

    s = io.open(PINS, encoding='utf-8').read()
    changed = []
    for did, items in ovr.items():
        if not items:
            continue
        line = quest_line(items)
        bm = re.search(r'(\["%s"\]\s*=\s*\{\n)(.*?)(\n\s*\},)' % re.escape(did), s, re.S)
        if bm:
            body = bm.group(2)
            if re.search(r'^\s*quest\s*=', body, re.M):
                body2 = re.sub(r'^\s*quest\s*=.*$', line, body, count=1, flags=re.M)
            else:
                body2 = body.rstrip() + '\n' + line
            s = s[:bm.start(2)] + body2 + s[bm.end(2):]
        else:
            block = '    ["%s"] = {\n%s\n    },\n' % (did, line)
            m = re.search(r'ns\.MapPins\s*=\s*\{\n', s)
            if not m:
                raise SystemExit('MapPins 表头未找到')
            s = s[:m.end()] + block + s[m.end():]
        changed.append('%s(%d)' % (did, len(items)))

    io.open(PINS, 'w', encoding='utf-8', newline='\n').write(s)
    print('written:', ', '.join(changed))


if __name__ == '__main__':
    main()
