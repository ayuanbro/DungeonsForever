# -*- coding: utf-8 -*-
"""扫描插件 Lua 文件里的**裸全局定义**（跨插件命名空间污染源）。

背景（2026-09-23 实机事故）：
  副本页剥离时把上游 UI.lua 里的两个裸全局函数 `BuildDungeons` / `BuildDungeonOverview`
  一起抄了过来。上游同名文件也定义这两个全局 → 两个插件同时加载时，**后加载者覆盖前者**。
  WoW 按文件夹名字母序加载：DungeonsForever < TalentsForever → 上游覆盖本插件
  → 本插件 `U:SwitchSub` 调到的其实是上游的函数（用上游的文件级 local U/MakeFS）
  → 上游 U.dungeonPage 为 nil → `MakeFS(nil)` → 报错在 TalentsForever/Core/UI.lua:113。

本脚本列出每个文件里「在 chunk 顶层制造全局」的行：
  ① `function NAME(`        —— 裸全局函数
  ② `NAME = ...`            —— 裸全局赋值（排除已知白名单，如 SLASH_*、SlashCmdList、UISpecialFrames）
  ③ `NAME.FIELD = ...`      —— 对**非本插件**全局表的字段写入（可疑，需人工判断）
用法：python _temp/scan_globals.py <插件根目录> [<上游根目录>]
"""
import os
import re
import sys

SAFE_ASSIGN = re.compile(r'^(?:SLASH_[A-Z0-9_]+|SlashCmdList|UISpecialFrames|BINDING_HEADER_[A-Z0-9_]+)\b')
SAFE_FIELD = {
    'SAVED_VARIABLES', 'UISpecialFrames', 'SlashCmdList', 'hooksecurefunc',
}
# 上游/客户端的公共表：往里写字段通常是有意为之（如 hook 表），不算本类缺陷
FIELD_OK = {'C_', 'InterfaceOptions_', 'GameTooltip', 'WorldMapFrame'}

FN_RE = re.compile(r'^function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(')
ASG_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)')
FLD_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\.[A-Za-z_][A-Za-z0-9_.]*\s*=(?!=)')


def scan(path):
    out = {'fn': [], 'asg': [], 'fld': []}
    for i, ln in enumerate(open(path, encoding='utf-8', errors='replace'), 1):
        s = ln.rstrip('\r\n')
        if not s or s.lstrip().startswith('--') or s[0] in ' \t':
            continue                                    # 空行 / 注释 / 缩进（非顶层）
        m = FN_RE.match(s)
        if m:
            out['fn'].append((i, m.group(1), s.strip()))
            continue
        m = FLD_RE.match(s)
        if m and m.group(1) not in FIELD_OK:
            out['fld'].append((i, m.group(1), s.strip()[:90]))
            continue
        m = ASG_RE.match(s)
        if m:
            name = m.group(1)
            if name in ('local', 'return', 'end', 'else', 'elseif', 'if', 'for', 'while'):
                continue
            if SAFE_ASSIGN.match(s):
                continue
            out['asg'].append((i, name, s.strip()[:90]))
    return out


def report(root, label):
    total = 0
    for dirpath, _dirs, files in os.walk(root):
        for fn in sorted(files):
            if not fn.endswith('.lua'):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root).replace('\\', '/')
            r = scan(p)
            if not (r['fn'] or r['asg'] or r['fld']):
                continue
            total += len(r['fn']) + len(r['asg'])
            print('  %s' % rel)
            for i, n, s in r['fn']:
                print('    L%-5d 裸全局函数  %s' % (i, n))
            for i, n, s in r['asg']:
                print('    L%-5d 裸全局赋值  %s' % (i, s))
            for i, n, s in r['fld']:
                print('    L%-5d 全局表字段  %s' % (i, s))
    print('  —— %s：顶层全局定义合计 %d 处' % (label, total))
    return total


roots = sys.argv[1:]
for r in roots:
    print('=========== %s ===========' % r)
    report(r, os.path.basename(r.rstrip('/\\')))
    print()
