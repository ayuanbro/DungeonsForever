# -*- coding: utf-8 -*-
"""手写件 L 化转换器：把代码里的 CJK 双引号字符串包成 L["…"]。

规则（2026-09-25 本地化第 1 步）：
- 跳过纯注释行（^\s*--）；行内代码段的 -- 注释部分不动。
- "中文"   -> L["中文"]   （前面已是 L 的不重复包）
- ["中文"] -> [L["中文"]] （表键同步包，保证繁体下键值对查两侧一致）
- 已含 L 键跳过；引号内跨行的串不动（逐行处理，发现不配对引号报错退出）。

用法：python wrap_locale.py Core/BisUI.lua [Core/ExploreUI.lua ...]
"""
import re
import sys

CJK = re.compile(r'[\u4e00-\u9fff]')


def split_comment(line):
    """返回 (代码段, 注释段)。-- 在字符串外才算注释起点。"""
    in_str = False
    i = 0
    while i < len(line):
        c = line[i]
        if c == '"' :
            in_str = not in_str
        elif c == '\\' and in_str:
            i += 1
        elif not in_str and c == '-' and line[i:i + 2] == '--':
            return line[:i], line[i:]
        i += 1
    if in_str:
        sys.exit('引号不配对（跨行串？需手工处理）：%s' % line.rstrip())
    return line, ''


S_QUOTED = re.compile(r'"([^"]*)"')


def wrap_code(code):
    out = []
    pos = 0
    for m in S_QUOTED.finditer(code):
        s = m.group(1)
        start, end = m.start(), m.end()
        # 段内先处理 bracket 键：本串是否处于 [ "…" ] 形态
        pre = code[max(0, start - 1):start]
        post = code[end:end + 1]
        if not CJK.search(s):
            continue
        if pre == 'L' and code[max(0, start - 2):start] == '.L':
            pass
        out.append((start, end, s, pre, post))
    if not out:
        return code, 0
    buf = []
    last = 0
    n = 0
    for start, end, s, pre, post in out:
        # 已是 L["…"] 形态则跳过（引号前两位是 L[）
        already = code[max(0, start - 2):start] == 'L['
        buf.append(code[last:start])
        if already:
            buf.append(code[start:end])
        else:
            # 键形态 ["中文"] 的方括号本来就留在原代码里，这里只替换引号串本体
            buf.append('L["%s"]' % s)
            n += 1
        last = end
    buf.append(code[last:])
    return ''.join(buf), n


def process(path):
    src = open(path, 'rb').read().decode('utf-8')
    nl = '\r\n' if '\r\n' in src else '\n'
    lines = src.split(nl)
    total = 0
    for idx, line in enumerate(lines):
        if line.lstrip().startswith('--'):
            continue
        code, comment = split_comment(line)
        if CJK.search(code) and '"' in code:
            new, n = wrap_code(code)
            if new != code:
                lines[idx] = new + comment
                total += n
    open(path, 'wb').write(nl.join(lines).encode('utf-8'))
    print('%s: 包了 %d 处' % (path, total))


for p in sys.argv[1:]:
    process(p)
