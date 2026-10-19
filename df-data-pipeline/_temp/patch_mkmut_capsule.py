# -*- coding: utf-8 -*-
"""给 mk_df_mut.py 加第 ⑥ 步：5 条「顶栏胶囊」变异。

用户 2026-09-23 要求：「副本」→「5人本」，右侧新增「团本」；胶囊行整体往上移 15。
本插件侧由 port_dungeonsforever.py 的 CAPSULE_PATCHES 落地，harness 断言由
patch_mkcheck_capsule.py 落地；这里补变异，证明那些断言**不是恒真白测**。

★ 坑（本脚本第一次写就踩了）：mk_df_mut.py 里的 `"MUTATIONS = [\n"` 是**源码里的转义串**，
  文件字节上是「反斜杠 + n」，不是真换行。所以拿它当锚点时，锚点也必须写成转义串形式；
  而 `# 残留自检` 这类普通文本才是真换行。故本脚本改在 `# 残留自检` 前插一段
  **生成器代码**（含定义 + 两处 text 改写），绕开转义层级。

★ 变异是 bytes，注释只能英文（中文字面量会被当成字节、破坏锚点匹配）。
★ 变异 spec 只能 2 元组 (old, new)。

用法：python patch_mkmut_capsule.py --check
      python patch_mkmut_capsule.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, 'mk_df_mut.py')

src = io.open(TARGET, 'rb').read().decode('utf-8')
orig = src

ANCHOR = '# 残留自检\n'

# 这段是**生成器代码**（原样落进 mk_df_mut.py）。
# 它是 raw 字符串，故下面写的 \n / \\r\\n / \" 都会原样成为 mk_df_mut.py 的源码，
# 再由 mk_df_mut.py 的 Python 解析器还原成「插进 harness 的文本」。
BLOCK = r'''# ── ⑥ 5 条「顶栏胶囊」变异（2026-09-23 用户要求：副本→5人本、右加团本、整体上移15）──
# 变异是 bytes，注释只能英文（中文字面量会被当成字节、破坏锚点匹配）。
# 每条都配了一条静态/动态断言；已逐条隔离跑过，确认不是脏抓。
_CAP_MUT_DEFS = (
    "MUT_CAPSULE_NO_LIFT = (\n"
    "    b'    host:SetPoint(\"TOP\", U.panel, \"TOP\", 0, DG.CAPSULE_LIFT - ROW_SUB)\\r\\n',\n"
    "    b'    host:SetPoint(\"TOP\", U.panel, \"TOP\", 0, -ROW_SUB) -- MUT: capsule lift gone\\r\\n')\n"
    "\n"
    "MUT_RAID_TAB_GONE = (\n"
    "    b'        { key = \"Raids\",    text = L[\"\\xe5\\x9b\\xa2\\xe6\\x9c\\xac\"],  width = DG.CAPSULE_W },\\r\\n',\n"
    "    b'        -- MUT: raid tab removed\\r\\n')\n"
    "\n"
    "MUT_SWITCH_IGNORES_KEY = (\n"
    "    b'    local k = (key == \"Raids\") and \"Raids\" or \"Dungeons\"\\r\\n',\n"
    "    b'    local k = \"Dungeons\" -- MUT: key ignored\\r\\n')\n"
    "\n"
    "MUT_RAID_SHOW_BOTH = (\n"
    "    b'    if U.dungeonPage then U.dungeonPage:SetShown(not isRaid) end\\r\\n',\n"
    "    b'    if U.dungeonPage then U.dungeonPage:SetShown(true) end -- MUT: both pages shown\\r\\n')\n"
    "\n"
    "MUT_UAS_NO_SKIP = (\n"
    "    b'    if self.curSub ~= \"Raids\" then self:UpdateDungeons() end\\r\\n',\n"
    "    b'    self:UpdateDungeons() -- MUT: no raid skip\\r\\n')\n"
    "\n"
)
_CAP_DEF_ANCHOR = "MUTATIONS = [\n"
if _CAP_DEF_ANCHOR not in text:
    sys.exit('未找到 MUTATIONS 定义处，上游可能已改动')
text = text.replace(_CAP_DEF_ANCHOR, _CAP_MUT_DEFS + _CAP_DEF_ANCHOR, 1)
print('  %-40s → %d 处' % ('胶囊变异定义 5 条', 1))

_CAP_REG_ANCHOR = (
    "    ('命名空间：页面构建函数退回裸全局（会被后加载的同名插件覆盖）', MUT_BARE_GLOBAL),\n"
    "]\n"
)
if _CAP_REG_ANCHOR not in text:
    sys.exit('未找到 MUTATIONS 尾部锚点，上游或第⑤步可能已改动')
text = text.replace(
    _CAP_REG_ANCHOR,
    "    ('命名空间：页面构建函数退回裸全局（会被后加载的同名插件覆盖）', MUT_BARE_GLOBAL),\n"
    "\n"
    "    # ⑪ 顶栏胶囊：5人本 / 团本 + 上移 15（用户 2026-09-23）\n"
    "    ('胶囊：上移量被改回 -ROW_SUB（没上移）', MUT_CAPSULE_NO_LIFT),\n"
    "    ('胶囊：团本那颗入口消失（退回单页签）', MUT_RAID_TAB_GONE),\n"
    "    ('胶囊：SwitchSub 又把 key 丢掉（永远只显示 5人本）', MUT_SWITCH_IGNORES_KEY),\n"
    "    ('胶囊：切团本时副本页不隐藏（两页同时显示）', MUT_RAID_SHOW_BOTH),\n"
    "    ('胶囊：UpdateActiveSub 在团本态也刷新（空态页误刷副本页）', MUT_UAS_NO_SKIP),\n"
    "]\n",
    1)
print('  %-40s → %d 处' % ('胶囊变异登记 5 条', 1))

'''

check_only = '--check' in sys.argv

n = src.count(ANCHOR)
if n != 1:
    sys.exit('✗ 锚点「# 残留自检」命中 %d 次（应为 1）' % n)
src = src.replace(ANCHOR, BLOCK + ANCHOR, 1)
print('  ✔ %-30s 1 处' % '⑥胶囊变异块')

if src == orig:
    sys.exit('✗ 没有任何改动')
if check_only:
    print('锚点命中 1 次 —— 可以正式跑。')
    sys.exit(0)

io.open(TARGET, 'wb').write(src.encode('utf-8'))
print('已写回 %s（%d -> %d 字节）' % (TARGET, len(orig.encode('utf-8')), len(src.encode('utf-8'))))
