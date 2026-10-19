# -*- coding: utf-8 -*-
"""按「实际用到的键」从上游 zhCN.lua 筛出覆盖条目，生成 DungeonsForever/Locales/zhCN.lua。

本插件词条以中文键名直接承载文案（查表未命中时 __index 回退返回键名本身），
故只有「键名 ≠ 文案」的条目需要登记。筛选是必须的：
上游 zhCN.lua 里约 60% 是天赋/法术书/传承页专用文案，抄进来只会变成死条目。

用法：python gen_locales.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
UI = os.path.join(DF, 'Core', 'DungeonUI.lua')
SRC_LOCALE = os.path.join(os.path.dirname(DF), 'TalentsForever', 'Locales', 'zhCN.lua')
DST = os.path.join(DF, 'Locales', 'zhCN.lua')

ui = open(UI, 'rb').read().decode('utf-8')
used = set(re.findall(r'L\["([^"]+)"\]', ui))

src = open(SRC_LOCALE, 'rb').read().decode('utf-8')
lines = src.split('\n')

# 逐行识别 `L["key"] = ...`，值可能跨行（多个字符串字面量串接），
# 判定方式：从 `=` 之后找第一个位于行尾的闭合引号。
ENTRY = re.compile(r'^L\["([^"]+)"\]\s*=')
entries = []          # [(key, [行...])]  按上游出现顺序
i = 0
while i < len(lines):
    m = ENTRY.match(lines[i])
    if not m:
        i += 1
        continue
    key = m.group(1)
    block = [lines[i]]
    # 单行闭合：去掉行尾空白后以 " 结尾
    while not block[-1].rstrip().endswith('"'):
        i += 1
        if i >= len(lines):
            sys.exit('条目未闭合：%s' % key)
        block.append(lines[i])
    entries.append((key, block))
    i += 1

hit = [(k, b) for k, b in entries if k in used]
missing = sorted(k for k in used if k not in dict(entries))

HEAD = '''local _, ns = ...
local L = setmetatable({}, {
    __index = function(_, key)
        return tostring(key)
    end,
})
ns.L = L
ns.DL = function(s)
    local lc = (type(GetLocale) == 'function') and GetLocale() or nil
    if lc == 'zhTW' or lc == 'enUS' then
        return L[s]
    end
    return s
end
local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'
if gl == 'zhTW' or gl == 'enUS' then return end'''

body = '\n'.join('\n'.join(b) for _, b in hit)
out = HEAD + '\n' + body + '\n'
open(DST, 'w', encoding='utf-8', newline='\n').write(out)

print('界面用到的键 %d 个；上游显式覆盖命中 %d 条；未登记（走回退返回键名）%d 个'
      % (len(used), len(hit), len(missing)))
print('  未登记键：%s' % ('、'.join(missing) if missing else '（无）'))


def _strip_comments_after_gen():
    """注释精简：**只清理本生成器写出的文件**（Locales/zhCN.lua，即 DST）。

    ★ 2026-09-29 收口（第七轮）：纠正旧实现的路径错位 —— 本生成器把产物写到
      DungeonsForever/Locales/zhCN.lua，收尾却去扫整个 Core/，既白扫又剥掉
      并行会话手改文件（LootFilterUI / MainFrame / Core / LootFilter）与其它
      生成器产物（enUS / zhTW 副本）的注释。现限定为 [DST] 单一产物，杜绝外溢。
      注释口径本身不变：每个 Lua 只留文件头注释块（逻辑仍在 _temp/strip_comments.py）。
    """
    import os as _os
    import sys as _sys
    _here = _os.path.dirname(_os.path.abspath(__file__))
    if _here not in _sys.path:
        _sys.path.insert(0, _here)
    import strip_comments as _S
    n = 0
    for _p in _S.walk([DST]):
        _raw = open(_p, 'rb').read()
        _txt = _raw.decode('utf-8')
        _new, _c, _t = _S.strip_all_text(_txt)
        if _new != _txt:
            open(_p, 'wb').write(_new.encode('utf-8'))
            n += 1
    if n:
        print('注释精简：收尾清理 %d 个文件' % n)

_strip_comments_after_gen()
