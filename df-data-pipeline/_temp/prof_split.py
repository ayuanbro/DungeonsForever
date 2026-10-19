# -*- coding: utf-8 -*-
"""Data_ProfRecipes.lua 顶层专业分片化（惰性构建）+ 幂等。

把单个 eager 的 `ns.ProfRecipes = { ["a"]={..}, ["b"]={..} }` 字面量
改成「每专业一个闭包 + __index 惰性代理」：
  - PARTS[k] = function() return {..} end   （只在被取用时构建）
  - KEYS     = 全部专业键清单（权威顺序）
  - HAND     = 手工段宿主（poisons / comprehension 等生成器不产出的段）
  - ns.ProfRecipes = setmetatable({}, { __index = ... })
  - ns.EnsureProfRecipes(keys?)  —— 不带参=全量；带 keys=只构建指定分片

用途：Core/Data/Data_ProfRecipes.lua 与其 enUS / zhTW 覆盖层。
幂等：已分片则直接退出。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

TARGETS = [
    'Core/Data/Data_ProfRecipes.lua',
    'Core/Data/enUS/Data_ProfRecipes.lua',
    'Core/Data/zhTW/Data_ProfRecipes.lua',
]

MARK = 'local PARTS = {}'


def scan_braces(s, i):
    """从 s[i] 处的 '{' 开始，返回与之配对的 '}' 的下标（忽略字符串/注释内的括号）。"""
    depth = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == '-' and s[i:i + 2] == '--':
            if s[i:i + 4] == '--[[':
                j = s.find(']]', i + 4)
                i = n if j < 0 else j + 2
                continue
            j = s.find('\n', i)
            i = n if j < 0 else j
            continue
        if c == '"' or c == "'":
            q = c
            i += 1
            while i < n:
                if s[i] == '\\':
                    i += 2
                    continue
                if s[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == '[' and s[i:i + 2] == '[[':
            j = s.find(']]', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def split_text(src, nl):
    """返回分片后的文本；已分片则返回 None。"""
    if MARK in src:
        return None

    head_m = src.find('ns.EnsureProfRecipes = function()')
    if head_m < 0:
        raise SystemExit('未找到 ns.EnsureProfRecipes = function()')
    head = src[:head_m]

    tbl_m = src.find('ns.ProfRecipes = {', head_m)
    if tbl_m < 0:
        raise SystemExit('未找到 ns.ProfRecipes = {')
    open_i = src.index('{', tbl_m)
    close_i = scan_braces(src, open_i)
    if close_i < 0:
        raise SystemExit('ns.ProfRecipes 表括号不配平')

    body = src[open_i + 1:close_i]

    # 切顶层条目：4 空格缩进的  ["key"] = { ... },
    entries = []
    i = 0
    n = len(body)
    while i < n:
        j = body.find('\n    ["', i)
        if j < 0:
            break
        st = j + 1
        k_beg = st + 6
        k_end = body.index('"]', k_beg)
        key = body[k_beg:k_end]
        br = body.index('{', k_end)
        en = scan_braces(body, br)
        if en < 0:
            raise SystemExit('分片 %s 括号不配平' % key)
        inner = body[br + 1:en]
        entries.append((key, inner))
        i = en + 1

    if not entries:
        raise SystemExit('未切出任何专业分片')

    out = io.StringIO()
    out.write(head.rstrip('\n') + nl + nl)
    out.write('local PARTS = {}' + nl)
    out.write('local KEYS = {}' + nl)
    out.write('local HAND = {' + nl)
    out.write('}' + nl + nl)
    for key, inner in entries:
        out.write('KEYS[#KEYS + 1] = "%s"' % key + nl)
        out.write('PARTS["%s"] = function() return {' % key + nl)
        out.write(inner)
        out.write('} end' + nl + nl)
    out.write('for k, v in pairs(HAND) do' + nl)
    out.write('    KEYS[#KEYS + 1] = k' + nl)
    out.write('    PARTS[k] = function() return v end' + nl)
    out.write('end' + nl + nl)
    out.write('ns.ProfRecipeKeys = KEYS' + nl)
    out.write('ns.ProfRecipes = setmetatable({}, {' + nl)
    out.write('    __index = function(t, k)' + nl)
    out.write('        local f = PARTS[k]' + nl)
    out.write('        if not f then return nil end' + nl)
    out.write('        PARTS[k] = nil' + nl)
    out.write('        local v = f()' + nl)
    out.write('        rawset(t, k, v)' + nl)
    out.write('        return v' + nl)
    out.write('    end,' + nl)
    out.write('})' + nl)
    out.write('ns.EnsureProfRecipes = function(keys)' + nl)
    out.write('    local t = ns.ProfRecipes' + nl)
    out.write('    local list = keys or KEYS' + nl)
    out.write('    for i = 1, #list do local _ = t[list[i]] end' + nl)
    out.write('    return t' + nl)
    out.write('end' + nl)
    return out.getvalue()


def main():
    dry = '--dry' in sys.argv
    changed = 0
    for rel in TARGETS:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            print('  跳过（不存在） %s' % rel)
            continue
        raw = open(p, 'rb').read()
        src = raw.decode('utf-8')
        nl = '\r\n' if src.count('\r\n') > src.count('\n') - src.count('\r\n') else '\n'
        uni = src.replace('\r\n', '\n')
        new = split_text(uni, '\n')
        if new is None:
            print('  已是分片   %-42s %8.0f KB' % (rel, len(raw) / 1024.0))
            continue
        out = new.replace('\n', nl) if nl == '\r\n' else new
        print('  分片完成   %-42s %8.0f KB -> %.0f KB' % (rel, len(raw) / 1024.0, len(out.encode('utf-8')) / 1024.0))
        if not dry:
            open(p, 'wb').write(out.encode('utf-8'))
        changed += 1
    print('共处理 %d 个文件%s' % (changed, '（dry-run，未写盘）' if dry else ''))


if __name__ == '__main__':
    main()
