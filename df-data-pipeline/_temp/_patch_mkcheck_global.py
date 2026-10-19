# -*- coding: utf-8 -*-
"""给 mk_df_check.py 加第 ⑦ 步：把「界面层不得定义裸全局函数」钉成静态断言。

为什么必须静态守：离线 harness 只加载本插件，**永远测不出**
「同名裸全局被后加载的同名插件覆盖」——本次 9 次本地回归全绿，实机点图标必崩。
本文件是一次性补丁，跑完即可删。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, 'mk_df_check.py')

raw = io.open(TARGET, 'rb').read()
src = raw.decode('utf-8')
orig = src

# 锚点 = ⑤ 步那条 replace 语句的完整尾部（含 `    1)`）。
# 必须锚完整的语句，否则会插进 Python 字符串拼接表达式中间。
ANCHOR = r'''    + "       and '地图标记仅无限客户端支持' in marcacode)\n",
    1)
'''

# 这一段是**生成器代码**（模块级）：它再去 harness 源码里插断言。
EXTRA = r'''
# ── ⑦ 补「跨插件命名空间」不变式（2026-09-23 实机事故）─────────────────────────
# 事故链：副本段从 upstream UI.lua 抄来了两个**裸全局函数**
#   BuildDungeons / BuildDungeonOverview；上游同名文件也定义这两个全局。
#   WoW 按文件夹名字母序加载 → DungeonsForever 先、TalentsForever 后 → 上游覆盖本插件。
#   于是本插件 U:SwitchSub 里的 `BuildDungeons()` 静默跑的是上游函数：
#   上游函数用的是**上游的文件级 local U**（U.dungeonPage 为 nil）→ MakeFS(nil)
#   → 报错落在 TalentsForever/Core/UI.lua:113（用户看到的正是这条）。
# 关键教训：离线 harness 只加载本插件，这种「被覆盖」永远测不出（9 次全绿 / 实机必崩），
#   只能用静态断言钉死：界面层不得有裸全局函数定义。
NS_ANCHOR = "       and '地图标记仅无限客户端支持' in marcacode)\n"
NS_EXTRA = r"""
    # ★★ 跨插件命名空间不变式（2026-09-23 实机事故）：界面层不得定义裸全局函数。
    #   上游 TalentsForever/Core/UI.lua 也定义 BuildDungeons / BuildDungeonOverview，
    #   WoW 按文件夹名字母序加载（DungeonsForever < TalentsForever）→ 上游覆盖本插件，
    #   U:SwitchSub 会静默调到上游函数（上游 U.dungeonPage 为 nil）→ MakeFS(nil)。
    #   离线 harness 只加载本插件，这种覆盖测不出，只能静态钉死。
    _bare = re.findall(r'(?m)^function\s+[A-Za-z_]\w*\s*\(', src)
    ck('★★ 界面层不定义裸全局函数（否则会被后加载的同名插件静默覆盖）',
       _bare == [], _bare)
    ck('★ BuildDungeons / BuildDungeonOverview 挂在 local 表 DG 上',
       'function DG.BuildDungeons()' in src
       and 'function DG.BuildDungeonOverview()' in src)
    _sw = src[src.index('function U:SwitchSub'):src.index('function U:UpdateActiveSub')]
    ck('★ U:SwitchSub 调的是 DG.BuildDungeons()（不是裸全局）',
       'DG.BuildDungeons()' in _sw)
"""
if NS_ANCHOR not in text:
    sys.exit('未找到⑦步的 harness 插入锚点，上游可能已改动')
text = text.replace(NS_ANCHOR, NS_ANCHOR + NS_EXTRA, 1)
'''

if ANCHOR not in src:
    sys.stderr.write('锚点未命中（本文件可能已打过补丁，或结构已变）\n')
    sys.exit(1)
src = src.replace(ANCHOR, ANCHOR + EXTRA, 1)

if src == orig:
    sys.stderr.write('没有任何改动\n')
    sys.exit(1)

io.open(TARGET, 'wb').write(src.encode('utf-8'))
print('已写回 %s（%d -> %d 字节）' % (TARGET, len(raw), len(src.encode('utf-8'))))
