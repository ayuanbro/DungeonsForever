# -*- coding: utf-8 -*-
"""预热调优（2026-10-03）：间隔 0.05 -> 0.2（给主线程留喘息）+ 已建齐短路"""
import io, sys

# ① 源侧插件（CRLF）
P = r'D:\workspace\DungeonsForever\Core\DungeonUI.lua'
s = io.open(P, 'r', encoding='utf-8', newline='').read()
NL = '\r\n'


def rep(old, new, label, nl=NL):
    global s
    old = old.replace('\n', nl)
    new = new.replace('\n', nl)
    c = s.count(old)
    if c != 1:
        print('!! [%s] 命中 %d 次' % (label, c))
        sys.exit(1)
    s = s.replace(old, new, 1)
    print('OK  %s' % label)


rep("""    local order = { "Raids" }
    if ns.LoadForeverPages then
        order[#order + 1] = "Professions"
        order[#order + 1] = "Explore"
        order[#order + 1] = "Bis"
        order[#order + 1] = "Tier"
    end
    local i = 0
""",
    """    local order = { "Raids" }
    if ns.LoadForeverPages then
        order[#order + 1] = "Professions"
        order[#order + 1] = "Explore"
        order[#order + 1] = "Bis"
        order[#order + 1] = "Tier"
    end
    local left = 0
    for _, k2 in ipairs(order) do
        if not (U.subBuilt and U.subBuilt[k2]) then left = left + 1 end
    end
    if left == 0 then return end     -- 全部建齐：不再排程（每次开窗都排会白跑一轮）
    local i = 0
""", 'SchedulePrebuild 已建齐短路')

rep('            C_Timer.After(0.05, step)\n',
    '            C_Timer.After(0.2, step)     -- 0.2s：给主线程留喘息，切页前基本已建好\n',
    '预热间隔 0.2s')
io.open(P, 'w', encoding='utf-8', newline='').write(s)
b = open(P, 'rb').read()
print('--- DungeonUI.lua CRLF %d / 字节 %d' % (b.count(b'\r\n'), len(b)))

# ② harness 静态断言同步（CRLF）
P2 = r'D:\workspace\DungeonsForever\_temp\df_dungeon_check.py'
s = io.open(P2, 'r', encoding='utf-8', newline='').read()
rep("""       and 'C_Timer.After(0.05, step)' in _lazy)""",
    """       and 'C_Timer.After(0.2, step)' in _lazy)""", 'harness 静态断言同步')
io.open(P2, 'w', encoding='utf-8', newline='').write(s)
print('--- 完成')
