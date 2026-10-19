# -*- coding: utf-8 -*-
"""修复：上一步把 Lua 语法塞进了 Python 段。把误插的块换成 Python 版。"""
GOOD = '''    # \u2500\u2500 \u56e2\u672c\u9875\uff08Core/RaidUI.lua\uff0c2026-09-29 \u65b0\u589e\uff1a\u65f6\u95f4\u7ebf / \u5217\u8868 \u4e24\u4e2a\u4e8c\u7ea7\u5b50\u9875\uff09\u2500\u2500
    _ra = open(os.path.join(ADDON, 'Core', 'RaidUI.lua'), encoding='utf-8',
               errors='replace').read().replace('\\r\\n', '\\n')
    _toc2 = open(TOC, encoding='utf-8', errors='replace').read().replace('\\r\\n', '\\n')
    _raf = re.findall(r'MakeFS\\([^,]+,\\s*(\\d+),', _ra)
    ck('\u2605 RaidUI \u6309 toc \u987a\u5e8f\u6302\u5728 DungeonUI \u4e4b\u540e',
       'Core\\\\DungeonUI.lua\\nCore\\\\RaidUI.lua\\n' in _toc2)
    ck('\u2605\u2605 RaidUI \u5168\u7aef\u53ef\u89c1\uff08\u4e0d\u6302 LoadForeverPages \u95f8\uff09',
       'ns.LoadForeverPages' not in _ra)
    ck('\u2605\u2605 RaidUI \u5b57\u53f7\u53ea\u8bb8 11/14/16\uff08\u5168\u63d2\u4ef6\u5b57\u53f7\u6807\u51c6\u540c\u6b3e\uff09',
       _raf and all(v in ('11', '14', '16') for v in _raf), sorted(set(_raf)))
    ck('\u2605\u2605 RaidUI \u4e8c\u7ea7\u9875\u7b7e = \u65f6\u95f4\u7ebf / \u5217\u8868',
       '{ key = "timeline", text = L["\u65f6\u95f4\u7ebf"] }' in _ra
       and '{ key = "list", text = L["\u5217\u8868"] }' in _ra)
    ck('\u2605\u2605 RaidUI \u4e0d\u505a\u79d2\u7ea7\u5012\u8ba1\u65f6\uff08\u65e0 OnUpdate / \u65e0 unlockAt\uff0c\u53ea\u5199\u65e5\u671f\uff09',
       'OnUpdate' not in _ra and 'unlockAt' not in _ra)
    ck('\u2605\u2605 RaidUI \u754c\u9762\u5c42\u4e0d\u5b9a\u4e49\u88f8\u5168\u5c40\u51fd\u6570\uff08\u51fd\u6570\u4e00\u5f8b\u6302 local \u8868 RU\uff09',
       not re.search(r'^function\\s+[A-Za-z_][A-Za-z0-9_]*\\s*\\(', _ra, re.M))
'''

MARK = '    # \u2500\u2500 \u56e2\u672c\u9875\uff08Core/RaidUI.lua\uff0c'


def fix(path):
    raw = open(path, 'rb').read().decode('utf-8')
    i = raw.find(MARK)
    if i < 0:
        print('[SKIP] %s 找不到误插块' % path)
        return
    j = raw.find('\n    end\n', i)
    if j < 0:
        print('[SKIP] %s 找不到块尾' % path)
        return
    raw = raw[:i] + GOOD + raw[j + len('\n    end\n'):]
    open(path, 'wb').write(raw.encode('utf-8'))
    print('[OK] %s 已换成 Python 版' % path)


for p in ('df_dungeon_check.py', 'mk_df_check.py'):
    fix(p)
