# -*- coding: utf-8 -*-
"""生成 Core/Data/Data_PvPHonor.lua —— 荣誉冲刺 CP 结算模型（生成物，禁手改）。

来源：_classic_era_/Interface/AddOns/Ranker/Ranker.lua 的 lookupData
（contributionPointsFloor/Ceiling、rankChangeFactor、honorToContributionPointsRatio、
honorIncrements 与各军衔荣誉里程碑），2026-10-08 移植。全部纯数字、语言中立。
黄金案例（R4·60%）：22500→R5·0% / 45000→R5·80% / 77500→R6·50% / 110000→R7·20%。
"""
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'Core', 'Data', 'Data_PvPHonor.lua')

RANK_CHANGE = [1, 1, 1, 0.8, 0.8, 0.8, 0.7, 0.7, 0.6, 0.5, 0.5, 0.4, 0.4, 0.34, 0.34]
CP_FLOOR = [0, 2000, 5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 45000, 50000, 55000, 60000]
CP_CEIL = [2000, 5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 45000, 50000, 55000, 60000, 65000]
RATIO = [2.25] * 6 + [6.5] * 4 + [16.25] * 4
INC = [0, 4500, 11250, 22500, 33750, 45000, 77500, 110000, 142500, 175000, 256250, 337500, 418750, 500000]

# 军衔 r 的里程碑 = INC 取 1 基下标 {r, r+2, r+3, r+4}（与 Ranker 帮助文案逐条一致）
MILES = {}
for r in range(2, 15):
    MILES[r] = [INC[k - 1] for k in (r, r + 2, r + 3, r + 4) if k <= 14]

def fmt(xs):
    return ', '.join(('%g' % x) if isinstance(x, float) else str(x) for x in xs)

lines = []
A = lines.append
A('')
A('')
A('')
A('')
A('')
A('')
A('')
A('local _, ns = ...')
A('')
A('ns.PvPHonorData = {')
A('    updated = "2026-10-08",')
A('    rankChangeFactor = {%s},' % fmt(RANK_CHANGE))
A('    cpFloor = {%s},' % fmt(CP_FLOOR))
A('    cpCeiling = {%s},' % fmt(CP_CEIL))
A('    honorRatio = {%s},' % fmt(RATIO))
A('    honorIncrements = {%s},' % fmt(INC))
A('    milestones = {')
for r in range(2, 15):
    A('        [%d] = {%s},' % (r, ', '.join(str(m) for m in MILES[r])))
A('    },')
A('}')
A('')

# 自检：黄金案例的里程碑锚点必须落在数据里
assert MILES[4] == [22500, 45000, 77500, 110000], MILES[4]
assert MILES[2] == [4500, 22500, 33750, 45000], MILES[2]
assert MILES[13] == [418750] and MILES[14] == [500000], (MILES[13], MILES[14])
assert RATIO[1] == 2.25 and RATIO[7] == 6.5 and RATIO[11] == 16.25

with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(lines))
print('written', OUT, len(lines), 'lines')
