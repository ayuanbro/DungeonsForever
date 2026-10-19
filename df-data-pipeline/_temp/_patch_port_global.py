# -*- coding: utf-8 -*-
"""给 port_dungeonsforever.py 打「去全局化」补丁（跨插件撞名修复的生成器侧改动）。

为什么要脚本补丁：本项目铁律——同一消息里对同一文件做多处文本替换会互相覆盖，
故一律「读全文 → 逐锚点确认恰好命中 1 次 → 二进制写回」。
本文件是一次性补丁，跑完即可删。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, 'port_dungeonsforever.py')

raw = io.open(TARGET, 'rb').read()
src = raw.decode('utf-8')
orig = src

PATCHES = []

# ① 需要 re 做裸全局函数扫描
PATCHES.append((
    'import os\nimport sys\n',
    'import os\nimport re\nimport sys\n',
))

# ② 边界自检补上 BuildDungeonOverview（上游第 5308 行，lines 下标 5307）
PATCHES.append((
    "    (lines[4983], 'function BuildDungeons()', 'BuildDungeons 定义应在段内'),\n",
    "    (lines[4983], 'function BuildDungeons()', 'BuildDungeons 定义应在段内'),\n"
    "    (lines[5307], 'function BuildDungeonOverview()', 'BuildDungeonOverview 定义应在段内'),\n",
))

# ③ REPLACES 末尾追加去全局化两条
PATCHES.append((
    "    ('TalentsForever_SourceURL', 'DungeonsForever_SourceURL'),\n]\n",
    "    ('TalentsForever_SourceURL', 'DungeonsForever_SourceURL'),\n"
    "    # \u2605\u2605 \u53bb\u5168\u5c40\u5316\uff082026-09-23 \u5b9e\u673a\u4e8b\u6545\uff0c\u89c1 AGENTS.md\u300c\u8de8\u63d2\u4ef6\u5168\u5c40\u649e\u540d\u300d\uff09\uff1a\n"
    "    #    \u4e0a\u6e38\u8fd9\u4e24\u4e2a\u662f**\u88f8\u5168\u5c40\u51fd\u6570**\uff0cTalentsForever \u4e5f\u5b9a\u4e49\u540c\u540d\u5168\u5c40\uff1bWoW \u6309\u6587\u4ef6\u5939\u540d\u5b57\u6bcd\u5e8f\u52a0\u8f7d\n"
    "    #    \uff08DungeonsForever < TalentsForever\uff09\u2192 \u4e0a\u6e38\u8986\u76d6\u672c\u63d2\u4ef6 \u2192 \u672c\u63d2\u4ef6\u7684 U:SwitchSub \u8c03\u5230\u4e0a\u6e38\u51fd\u6570\n"
    "    #    \uff08\u7528\u4e0a\u6e38\u7684\u6587\u4ef6\u7ea7 local U\uff0cU.dungeonPage \u4e3a nil\uff09\u2192 MakeFS(nil)\uff0c\n"
    "    #    \u62a5\u9519\u843d\u5728 TalentsForever/Core/UI.lua:113\u3002\u6302\u5230\u672c\u6587\u4ef6\u5df2\u6709\u7684 local \u8868 DG \u4e0a\uff0c\n"
    "    #    \u65e2\u6d88\u6389\u5168\u5c40\u53c8\u4e0d\u65b0\u589e main chunk local\uff08\u4e0a\u6e38\u90a3\u4e2a chunk \u5df2\u903c\u8fd1 200 \u4e0a\u9650\uff09\u3002\n"
    "    #    \u6ce8\u610f BuildDungeonOverview \u5728\u6bb5\u5185**\u5148\u8c03\u7528\uff08\u4e0a\u6e38 5278 \u884c\uff09\u540e\u5b9a\u4e49\uff085308 \u884c\uff09**\uff0c\n"
    "    #    \u6240\u4ee5\u53ea\u80fd\u7528\u8868\u5b57\u6bb5\u3001\u4e0d\u80fd\u7528 local function\u3002\n"
    "    ('BuildDungeons()', 'DG.BuildDungeons()'),\n"
    "    ('BuildDungeonOverview()', 'DG.BuildDungeonOverview()'),\n]\n",
))

# ④ 替换循环之后加硬闸
PATCHES.append((
    "    module = module.replace(old, new)\n\nif 'TalentsForever' in module:\n",
    "    module = module.replace(old, new)\n\n"
    "# \u2605 \u786c\u95f8\uff1a\u6bb5\u5185\u4e0d\u5f97\u518d\u51fa\u73b0\u88f8\u5168\u5c40\u51fd\u6570\u5b9a\u4e49\uff08\u8de8\u63d2\u4ef6\u649e\u540d\u7684\u552f\u4e00\u6765\u6e90\uff09\u3002\n"
    "#   \u5b9e\u6d4b\u53e3\u5f84\uff1a\u88f8\u5168\u5c40\u51fd\u6570\u88ab\u540e\u52a0\u8f7d\u7684\u540c\u540d\u63d2\u4ef6\u8986\u76d6\u540e\uff0c\u8c03\u7528\u70b9\u4f1a\u9ed8\u9ed8\u8dd1\u522b\u4eba\u7684\u4ee3\u7801\uff0c\n"
    "#   \u800c\u79bb\u7ebf harness\uff08\u53ea\u52a0\u8f7d\u672c\u63d2\u4ef6\uff09**\u6c38\u8fdc\u6d4b\u4e0d\u51fa**\u3002\u6545\u5fc5\u987b\u5728\u751f\u6210\u671f\u5c31\u62e6\u4f4f\u3002\n"
    "_bare = re.findall(r'(?m)^function\\s+[A-Za-z_]\\w*\\s*\\(', module)\n"
    "if _bare:\n"
    "    die('\u6bb5\u5185\u4ecd\u6709\u88f8\u5168\u5c40\u51fd\u6570\u5b9a\u4e49\uff08\u4f1a\u4e0e\u4e0a\u6e38\u649e\u540d\uff0c\u5fc5\u987b\u6302\u5230 DG. \u4e0a\uff09\uff1a%s' % _bare)\n\n"
    "if 'TalentsForever' in module:\n",
))

# ⑤ 手写段 U:SwitchSub 的调用点同步改名
PATCHES.append((
    "    if U.dungeonPage then U.dungeonPage:SetShown(true) end\n    BuildDungeons()\n",
    "    if U.dungeonPage then U.dungeonPage:SetShown(true) end\n    DG.BuildDungeons()\n",
))

# ⑥ 文件头注释补一句
PATCHES.append((
    '纯机械抽取：按行号区间从源文件逐字取（保留 CRLF），只做点名替换 + 手写文件头/生命周期。\n',
    '纯机械抽取：按行号区间从源文件逐字取（保留 CRLF），只做点名替换 + 手写文件头/生命周期。\n'
    '★ 点名替换里含「去全局化」：上游的 BuildDungeons / BuildDungeonOverview 是裸全局，\n'
    '  必须挂到本文件 local 表 DG 上，否则会被后加载的同名插件覆盖（2026-09-23 实机事故）。\n',
))

for i, (old, new) in enumerate(PATCHES, 1):
    n = src.count(old)
    if n != 1:
        sys.stderr.write('补丁 %d 锚点命中 %d 次（期望 1）：%r\n' % (i, n, old[:70]))
        sys.exit(1)
    src = src.replace(old, new)
    print('  补丁 %d 命中 1 次 OK' % i)

if src == orig:
    sys.stderr.write('没有任何改动\n')
    sys.exit(1)

io.open(TARGET, 'wb').write(src.encode('utf-8'))
print('已写回 %s（%d -> %d 字节）' % (TARGET, len(raw), len(src.encode('utf-8'))))
