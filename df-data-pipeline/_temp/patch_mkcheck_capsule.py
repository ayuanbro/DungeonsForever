# -*- coding: utf-8 -*-
"""给 mk_df_check.py 加第 ⑧ 步：顶栏胶囊「5人本 / 团本」+ 整体上移 15 的断言。

用户 2026-09-23 要求：「副本」→「5人本」，右侧新增「团本」；胶囊行整体往上移 15。
本插件侧由 port_dungeonsforever.py 的 CAPSULE_PATCHES 落地；这里补守住它的断言。

★ 关键：mk_df_check.py **不含 harness 正文**（它在运行时把上游 tf_dungeon_check.py 读进
  `text` 再改写），所以：
    · 静态断言那一段是「往 NS_EXTRA 字符串里加行」——NS_EXTRA 本身就是要插进 harness 的
      源码文本，故直接追加即可（第 ⑦ 步也是这么干的）；
    · 动态断言那一段必须写成**生成器代码**（拼一个 DYN_EXTRA 再 text.replace），
      不能直接写字面量（写了只是 mk_df_check.py 里多一段没人执行的文本）。

★ 为什么上移量只能静态钉：桩的 SetPoint 只校验首参是 string、**不记偏移**
  （见 _temp/tf_dryrun.py 的 CHECKED.SetPoint），离线拿不到几何值。

用法：python patch_mkcheck_capsule.py --check   # 只验锚点
      python patch_mkcheck_capsule.py           # 落盘
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, 'mk_df_check.py')

src = io.open(TARGET, 'rb').read().decode('utf-8')
orig = src

# ────────────────────────────────────────────────────────────────────────────
# ① 静态断言：追加到第 ⑦ 步 NS_EXTRA 的尾部（该字符串内容会被插进 harness 的 static_guard）
# ────────────────────────────────────────────────────────────────────────────
STATIC_ANCHOR = (
    "    ck('★ U:SwitchSub 调的是 DG.BuildDungeons()（不是裸全局）',\n"
    "       'DG.BuildDungeons()' in _sw)\n"
)

STATIC_BLOCK = r'''
    # ── 顶栏胶囊：两颗（5人本 / 团本）+ 整体上移 15（2026-09-23 用户指定）──
    # 「上移量」是纯几何量：桩的 SetPoint 只校验首参类型、不记偏移（CHECKED.SetPoint）
    # → 离线拿不到几何值，只能静态钉。
    # 静态断言一律**收窄到目标函数体**：同名串在别处会被「替命中」（白测）。
    ck('★★ 胶囊行上移量 DG.CAPSULE_LIFT = 15',
       re.search(r'DG\.CAPSULE_LIFT\s*=\s*15\b', src) is not None)
    ck('★ 胶囊 host 的 y 偏移 = DG.CAPSULE_LIFT - ROW_SUB（上移没被改回 -ROW_SUB）',
       'host:SetPoint("TOP", U.panel, "TOP", 0, DG.CAPSULE_LIFT - ROW_SUB)' in src)
    ck('★ 两颗胶囊等宽（分段控件滑块宽度按按钮宽取，不等宽会跳形）',
       'DG.CAPSULE_W = 82' in src and src.count('width = DG.CAPSULE_W') == 2)
    ck('★ 两颗胶囊 = 5人本(Dungeons) / 团本(Raids)',
       '{ key = "Dungeons", text = L["5人本"], width = DG.CAPSULE_W }' in src
       and '{ key = "Raids",    text = L["团本"],  width = DG.CAPSULE_W }' in src)
    ck('★ 旧的单页签「副本」文案已下线', 'L["副本"]' not in src)
    ck('★★ SwitchSub 按 key 分流（不是把参数丢掉、永远只显示副本页）',
       'local k = (key == "Raids") and "Raids" or "Dungeons"' in _sw
       and 'U.dungeonPage:SetShown(not isRaid)' in _sw
       and 'if U.raidPage then U.raidPage:SetShown(isRaid) end' in _sw
       and 'if not isRaid then' in _sw)
    _bld = src[src.index('function U:Build()'):src.index('function U:Refresh()')]
    ck('★ 团本页在 Build 里一次建好（不在切页时懒建 → 保住「渲染路径零新建帧」不变量）',
       'U.raidPage = CreateFrame("Frame", nil, panel)' in _bld
       and 'U.raidNote:SetText(L["团本数据待补"])' in _bld)
    _uas = src[src.index('function U:UpdateActiveSub'):src.index('function U:Build()')]
    ck('★ UpdateActiveSub 在团本态跳过刷新（空态没有可刷新的内容）',
       'if self.curSub ~= "Raids" then self:UpdateDungeons() end' in _uas)
'''

# ────────────────────────────────────────────────────────────────────────────
# ② 生成器代码：往 text（harness 正文）里插动态断言 + 改一条旧断言名
#    锚 = 第 ⑦ 步生成器代码的最后两行（那一段是**可执行代码**，插在它后面才是代码区）
# ────────────────────────────────────────────────────────────────────────────
GEN_ANCHOR = (
    "if NS_ANCHOR not in text:\n"
    "    sys.exit('未找到⑦步的 harness 插入锚点，上游可能已改动')\n"
    "text = text.replace(NS_ANCHOR, NS_ANCHOR + NS_EXTRA, 1)\n"
)

GEN_BLOCK = r'''
# ── ⑧ 顶栏胶囊：两颗（5人本 / 团本）+ 整体上移 15（2026-09-23 用户指定）────────
# 本插件侧由 port_dungeonsforever.py 的 CAPSULE_PATCHES 落地；这里往 harness 里插动态断言。
# 上移量只能静态钉（桩的 SetPoint 不记偏移，见上面 static_guard 里的断言）。
# 动态这半边要证明的是：**两颗真的能互斥切换**，且切到空态团本页时不去碰副本页的构建/刷新。
DYN_ANCHOR = (
    '    U:SwitchSub("Dungeons")\n'
    '    if U.dungeonPage == nil then ck("dungeonPage 页面帧未创建", false) return end\n'
    '    ck("★ SwitchSub 后副本页显示（漏 SetShown → 整页空白）", U.dungeonPage.__shown == true)\n'
    '    ck("副本页已构建", U.dungeonBuilt == true)\n'
)
DYN_EXTRA = r"""
    -- ---------- 顶栏胶囊：5人本 / 团本（2026-09-23 用户指定）----------
    -- 整块包 do...end：Lua 5.1 单函数 local 上限 200，本脚本很长，
    -- 块内临时变量出块即释放，不计入峰值。
    do
      ck("★ 胶囊行恰好两颗", #(U.subTabs or {}) == 2, #(U.subTabs or {}))
      local _t1, _t2 = (U.subTabs or {})[1], (U.subTabs or {})[2]
      ck("★ 两颗胶囊 key = Dungeons / Raids",
         _t1 ~= nil and _t1.key == "Dungeons" and _t2 ~= nil and _t2.key == "Raids",
         tostring(_t1 and _t1.key) .. " / " .. tostring(_t2 and _t2.key))
      ck("★ 两颗胶囊文案 = 5人本 / 团本（用户 2026-09-23 改名）",
         _t1 ~= nil and _t1.text == "5人本" and _t2 ~= nil and _t2.text == "团本",
         tostring(_t1 and _t1.text) .. " / " .. tostring(_t2 and _t2.text))
      ck("★ 团本页是常驻帧（空态骨架）", U.raidPage ~= nil and U.raidNote ~= nil)
      ck("★ 团本页占位文案 = 团本数据待补",
         U.raidNote ~= nil and U.raidNote.__text == "团本数据待补",
         U.raidNote and U.raidNote.__text)

      -- 切到团本：副本页隐、团本页显
      local _f0 = FRAMES
      U:SwitchSub("Raids")
      ck("★ 切团本 → 团本页显示", U.raidPage.__shown == true)
      ck("★ 切团本 → 副本页隐藏（两页互斥）", U.dungeonPage.__shown == false)
      ck("★ 切团本 → curSub = Raids", U.curSub == "Raids", tostring(U.curSub))
      ck("★ 切团本零新建帧（空态骨架不做构建）", FRAMES == _f0, FRAMES - _f0)
      ck("★ 选中态写进存档 subTab（开窗沿用上次那一颗）",
         DungeonsForeverDB ~= nil and DungeonsForeverDB.dungeon ~= nil
         and DungeonsForeverDB.dungeon.subTab == "Raids",
         DungeonsForeverDB and DungeonsForeverDB.dungeon
         and tostring(DungeonsForeverDB.dungeon.subTab))
      -- 开窗刷新路径：团本态下不得去刷按钮都没显示的副本页
      local _okU = pcall(U.UpdateActiveSub, U)
      ck("★ 团本态下 UpdateActiveSub 不报错", _okU == true)
      ck("★ 团本态下 UpdateActiveSub 不会把副本页刷出来", U.dungeonPage.__shown == false)

      -- 切回 5人本：副本页复原、内容仍在
      U:SwitchSub("Dungeons")
      ck("★ 切回 5人本 → 副本页显示", U.dungeonPage.__shown == true)
      ck("★ 切回 5人本 → 团本页隐藏", U.raidPage.__shown == false)
      ck("★ 切回 5人本 → curSub = Dungeons", U.curSub == "Dungeons", tostring(U.curSub))
      ck("★ 切回后副本页仍处于已构建态", U.dungeonBuilt == true)
    end
"""
if DYN_ANCHOR not in text:
    sys.exit('未找到⑧步动态插入锚点（上游 harness 可能已改动）')
text = text.replace(DYN_ANCHOR, DYN_ANCHOR + DYN_EXTRA, 1)
print('  %-28s → %d 处' % ('⑧动态断言块', 1))

# 旧断言名里的「副本」随胶囊改名 → 「5人本」（只改文案，判定逻辑不变）
_LBL_OLD = '    ck("标签行里有「副本」入口", found)\n'
_LBL_NEW = '    ck("标签行里有「5人本」入口（key = Dungeons；文案随用户要求已改名）", found)\n'
if _LBL_OLD not in text:
    sys.exit('未找到⑧步标签断言名锚点（上游 harness 可能已改动）')
text = text.replace(_LBL_OLD, _LBL_NEW, 1)
print('  %-28s → %d 处' % ('⑧标签断言改名', 1))
'''

check_only = '--check' in sys.argv


def apply(label, old, new):
    global src
    n = src.count(old)
    if n != 1:
        sys.exit('✗ %s 锚点命中 %d 次（应为 1）' % (label, n))
    src = src.replace(old, new, 1)
    print('  ✔ %-34s 1 处' % label)


apply('①静态断言块', STATIC_ANCHOR, STATIC_ANCHOR + STATIC_BLOCK)
apply('②生成器代码（动态）', GEN_ANCHOR, GEN_ANCHOR + GEN_BLOCK)

if src == orig:
    sys.exit('✗ 没有任何改动')
if check_only:
    print('两条锚点各命中 1 次 —— 可以正式跑。')
    sys.exit(0)

io.open(TARGET, 'wb').write(src.encode('utf-8'))
print('已写回 %s（%d -> %d 字节）' % (TARGET, len(orig.encode('utf-8')), len(src.encode('utf-8'))))
