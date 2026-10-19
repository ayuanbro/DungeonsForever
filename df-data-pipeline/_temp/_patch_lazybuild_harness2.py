# -*- coding: utf-8 -*-
"""harness 断言二次校准（2026-10-03）：修 `_lazy` 误用 + 恢复专业页原断言"""
import io, sys

P = r'D:\workspace\DungeonsForever\_temp\df_dungeon_check.py'
NL = '\r\n'
s = io.open(P, 'r', encoding='utf-8', newline='').read()


def rep(old, new, label):
    global s
    old = old.replace('\n', NL)
    new = new.replace('\n', NL)
    c = s.count(old)
    if c != 1:
        print('!! [%s] 命中 %d 次（期望 1）' % (label, c))
        sys.exit(1)
    s = s.replace(old, new, 1)
    print('OK  %s' % label)


# ① `U:EnsureBuilt("Raids")` 的字面量只出现在 SwitchSub，不在 EnsureBuilt 段 → 改用 _sw
rep("""       and 'U:EnsureBuilt("Raids")' in _lazy
       and 'ns.RaidModule.Build(U.raidPage)' in _lazy)""",
    """       and 'U:EnsureBuilt("Raids")' in _sw
       and 'ns.RaidModule.Build(U.raidPage)' in _lazy)""", 'R1 _lazy -> _sw (Raids)')

rep("""       and 'U:EnsureBuilt("Explore")' in _lazy
       and 'ns.ExploreModule.Build(U.explorePage)' in _lazy)""",
    """       and 'U:EnsureBuilt("Explore")' in _sw
       and 'ns.ExploreModule.Build(U.explorePage)' in _lazy)""", 'R2 _lazy -> _sw (Explore)')

rep("""       and 'U:EnsureBuilt("Professions")' in _lazy
       and 'ns.ProfModule.Build(U.profPage)' in _lazy)""",
    """       and 'U:EnsureBuilt("Professions")' in _sw
       and 'ns.ProfModule.Build(U.profPage)' in _lazy)""", 'R3 _lazy -> _sw (Professions)')

# ② 专业页断言：本段之前（探索段末）已 SwitchSub("Professions") ⇒ 内容已建，恢复原口径
rep("""          -- ★ 懒构建（2026-10-03）：专业页内容要切到该页才建 —— 先断「未切 = 未建」，再切。
          ck("★★ 懒构建：未切过专业页时内容尚未建（PD.built 仍为 false）", PD.built ~= true)
""",
    """          ck("★ 页面骨架由 ProfModule.Build 建好（PD.built）", PD.built == true)
          ck("★ 行池 / 滚动容器就位（详情条 2026-09-23 晚已退役）",
             PD.child ~= nil and PD.scroll ~= nil and PD.detail == nil)
""", 'R11 恢复原断言')

rep("""          ck("★ 首次切到专业页会一次性建页（懒构建成本）", FRAMES - _f0 > 0, FRAMES - _f0)
          ck("★★ 切到专业页后内容已就位（PD.built + 行池/滚动容器）",
             PD.built == true and PD.child ~= nil and PD.scroll ~= nil and PD.detail == nil)
""",
    """          ck("★ 首次进专业页只长行池、不重复建骨架（新建帧 < 64）", FRAMES - _f0 < 64, FRAMES - _f0)
          ck("★★ 懒构建后专业页内容仍完整就位（PD.built + 行池/滚动容器）",
             PD.built == true and PD.child ~= nil and PD.scroll ~= nil and PD.detail == nil)
""", 'R11b 恢复原断言 + 新增就位断言')

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('--- 写回完成')
