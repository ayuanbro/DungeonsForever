# -*- coding: utf-8 -*-
"""DungeonUI.lua 挂点补丁：接入 PvP 页（第 8 颗胶囊，仅 LoadForeverPages）。
CRLF 二进制读写；每条锚点断言恰好命中 1 次；--check 只预检不落盘。

挂点清单（8 处）：
  1 BuildSubTabs defs          胶囊定义
  2 EnsureBuilt                懒构建分支
  3 SchedulePrebuild order     空闲预热顺序
  4 SwitchSub elseif           键名合法化
  5 SwitchSub isXXX/SetShown   显隐互斥
  6 SwitchSub 调用分派         EnsureBuilt + Open
  7 UpdateActiveSub            刷新分派
  8 U:Build saved + pvpPage    存档还原 + 页帧创建
  9 DG.RefreshItemCards 尾部   物品到货重刷接线（ns.PvPModule.OnItemData）
"""
import sys, io, os

P = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                                  'Core', 'DungeonUI.lua'))
CHECK = '--check' in sys.argv

raw = open(P, 'rb').read().decode('utf-8')
assert raw.count('\r\n') > 0, 'DungeonUI.lua 应为 CRLF'
bare = raw.count('\n') - raw.count('\r\n')
assert bare == 0, '发现裸 LF: %d' % bare

def crlf(s):
    return s.replace('\n', '\r\n')

PATCHES = [
    # 1 胶囊 defs
    (crlf('        defs[#defs + 1] = { key = "Tier", text = L["职业指南"], width = DG.CAPSULE_W }\n    end'),
     crlf('        defs[#defs + 1] = { key = "Tier", text = L["职业指南"], width = DG.CAPSULE_W }\n'
          '        defs[#defs + 1] = { key = "PvP", text = L["PvP"], width = DG.CAPSULE_W }\n    end')),
    # 2 EnsureBuilt 分支
    (crlf('    elseif k == "Tier" and ns.TierModule and U.tierPage then\n'
          '        U.subBuilt[k] = true\n'
          '        ns.TierModule.Build(U.tierPage)\n    end'),
     crlf('    elseif k == "Tier" and ns.TierModule and U.tierPage then\n'
          '        U.subBuilt[k] = true\n'
          '        ns.TierModule.Build(U.tierPage)\n'
          '    elseif k == "PvP" and ns.PvPModule and U.pvpPage then\n'
          '        U.subBuilt[k] = true\n'
          '        ns.PvPModule.Build(U.pvpPage)\n    end')),
    # 3 SchedulePrebuild 顺序
    (crlf('        order[#order + 1] = "Tier"\n    end'),
     crlf('        order[#order + 1] = "Tier"\n'
          '        order[#order + 1] = "PvP"\n    end')),
    # 4 SwitchSub 键名合法化
    (crlf('    elseif key == "Tier" and ns.LoadForeverPages then\n'
          '        k = "Tier"\n    end'),
     crlf('    elseif key == "Tier" and ns.LoadForeverPages then\n'
          '        k = "Tier"\n'
          '    elseif key == "PvP" and ns.LoadForeverPages then\n'
          '        k = "PvP"\n    end')),
    # 5 SwitchSub 显隐互斥（locals + SetShown）
    (crlf('    local isDun, isRaid, isProf, isExpl, isColl, isBis, isTier = (k == "Dungeons"), (k == "Raids"), (k == "Professions"), (k == "Explore"), (k == "Collections"), (k == "Bis"), (k == "Tier")'),
     crlf('    local isDun, isRaid, isProf, isExpl, isColl, isBis, isTier = (k == "Dungeons"), (k == "Raids"), (k == "Professions"), (k == "Explore"), (k == "Collections"), (k == "Bis"), (k == "Tier")\n'
          '    local isPvP = (k == "PvP")')),
    (crlf('    if U.tierPage then U.tierPage:SetShown(isTier) end'),
     crlf('    if U.tierPage then U.tierPage:SetShown(isTier) end\n'
          '    if U.pvpPage then U.pvpPage:SetShown(isPvP) end')),
    # 6 SwitchSub 调用分派
    (crlf('    elseif isTier and ns.TierModule then\n'
          '        U:EnsureBuilt("Tier")\n'
          '        ns.TierModule.Refresh()\n    end'),
     crlf('    elseif isTier and ns.TierModule then\n'
          '        U:EnsureBuilt("Tier")\n'
          '        ns.TierModule.Refresh()\n'
          '    elseif isPvP and ns.PvPModule then\n'
          '        U:EnsureBuilt("PvP")\n'
          '        ns.PvPModule.Open()\n    end')),
    # 7 UpdateActiveSub 分派
    (crlf('    if self.curSub == "Tier" then\n'
          '        if ns.TierModule then ns.TierModule.Refresh() end\n'
          '        return\n    end'),
     crlf('    if self.curSub == "Tier" then\n'
          '        if ns.TierModule then ns.TierModule.Refresh() end\n'
          '        return\n    end\n'
          '    if self.curSub == "PvP" then\n'
          '        if ns.PvPModule then ns.PvPModule.Refresh() end\n'
          '        return\n    end')),
    # 8a U:Build 存档还原
    (crlf('    elseif saved == "Tier" and ns.LoadForeverPages then\n'
          '        U.curSub = "Tier"'),
     crlf('    elseif saved == "Tier" and ns.LoadForeverPages then\n'
          '        U.curSub = "Tier"\n'
          '    elseif saved == "PvP" and ns.LoadForeverPages then\n'
          '        U.curSub = "PvP"')),
    # 8b U:Build 页帧创建
    (crlf('        U.tierPage = CreateFrame("Frame", nil, panel)\n'
          '        U.tierPage:SetAllPoints(panel)\n'
          '        U.tierPage:Hide()'),
     crlf('        U.tierPage = CreateFrame("Frame", nil, panel)\n'
          '        U.tierPage:SetAllPoints(panel)\n'
          '        U.tierPage:Hide()\n'
          '        U.pvpPage = CreateFrame("Frame", nil, panel)\n'
          '        U.pvpPage:SetAllPoints(panel)\n'
          '        U.pvpPage:Hide()')),
    # 9 物品到货重刷接线
    (crlf('    local RU = ns.RU\n'
          '    if RU and RU.OnItemData then RU.OnItemData(itemID) end'),
     crlf('    local RU = ns.RU\n'
          '    if RU and RU.OnItemData then RU.OnItemData(itemID) end\n'
          '    local PVM = ns.PvPModule\n'
          '    if PVM and PVM.OnItemData then PVM.OnItemData(itemID) end')),
]

for i, (old, new) in enumerate(PATCHES, 1):
    n = raw.count(old)
    if n != 1:
        print('FAIL patch %d: anchor hit %d times' % (i, n))
        print('--- anchor head ---')
        print(old[:120].replace('\r\n', '\\r\\n'))
        sys.exit(1)

if CHECK:
    print('check OK: %d anchors hit exactly once' % len(PATCHES))
    sys.exit(0)

for old, new in PATCHES:
    raw = raw.replace(old, new, 1)

assert raw.count('\n') - raw.count('\r\n') == 0, '写入前裸 LF 检查失败'
open(P, 'wb').write(raw.encode('utf-8'))
print('patched DungeonUI.lua: %d hooks' % len(PATCHES))
