# -*- coding: utf-8 -*-
"""第五刀 · 第四段（校正）：pump 回到「一帧只跑一个块」。

第一段把 pump 改成「一帧内按预算连跑多个块」—— 这是**过度设计且有害**的：
块本身已经是「一帧的量」（预热一撮 / 一批行 / 一批卡 / 地图页的一段），
一帧连跑多块 = 把地图页那 6 段又合并回一帧（138 帧的尖峰回来了）。

正确分工：
  · pump      —— 一帧一个块（与第四刀完全一致，离线断言契约不变）
  · 块内部    —— 由 DG.Loader.budgetMs（真机 debugprofilestop）+ 数量兜底闸自适应

用法：python _apply_loadgate4.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
SRC = os.path.join(DF, 'Core', 'DungeonUI.lua')

raw = io.open(SRC, 'rb').read()
txt = raw.decode('utf-8')
style = '\r\n' if '\r\n' in txt else '\n'
flat = txt.replace('\r\n', '\n')


def rep(old, new, tag):
    global flat
    n = flat.count(old)
    if n != 1:
        print('!! [%s] 锚点命中 %d 次（应为 1）' % (tag, n))
        sys.exit(1)
    flat = flat.replace(old, new, 1)
    print('OK  [%s]' % tag)


rep('''    local function pump()
        -- ★★★ 第五刀：每帧预算（见 DG.Loader）—— 时间闸 + 数量闸，任一触发即停手。
        --   任务若返回真值 = 「本帧让出」（放回队首，下一帧接着来）。
        local t0 = DG.__nowMs()
        local n = 0
        while true do
            local fn = table.remove(DG.pendingSteps, 1)
            if not fn then
                DG.stepping = false
                DG.Gate.Finish()          -- ★ 队列抽干 = 这一批活干完了（进度条到此收工）
                return
            end
            local ok, res = pcall(fn)
            if not ok then
                print("|cffff5040[无限副本手册] 分帧构建出错（已跳过该块）：|r" .. tostring(res))
                res = nil
            end
            if res then
                table.insert(DG.pendingSteps, 1, fn)
                break
            end
            n = n + 1
            if n >= DG.Loader.budgetObj then break end
            local t1 = t0 and DG.__nowMs()
            if t1 and (t1 - t0) >= DG.Loader.budgetMs then break end
        end
        if #DG.pendingSteps > 0 then''',
    '''    local function pump()
        -- ★★★ 第五刀的分工：**pump 一帧只跑一个块** —— 块本身已经是「一帧的量」
        --   （预热一撮 / 一批行帧 / 一批 boss 卡 / 地图页的一段），一帧连跑多块就等于
        --   把已经拆开的尖峰又合并回去。
        --   块**内部**的密度才由 DG.Loader.budgetMs（真机 debugprofilestop 计时）+
        --   各块自己的数量兜底闸自适应 —— 好机器一帧多建几个、差机器少建几个。
        local fn = table.remove(DG.pendingSteps, 1)
        if not fn then
            DG.stepping = false
            return
        end
        local ok, err = pcall(fn)
        if not ok then
            print("|cffff5040[无限副本手册] 分帧构建出错（已跳过该块）：|r" .. tostring(err))
        end
        if #DG.pendingSteps > 0 then''',
    'pump 回到一帧一块')

rep('''        else
            DG.stepping = false
        end
    end
    -- ★★★ 2026-10-03「点副本就卡死」第四刀：**首块也不抢当前帧**。''',
    '''        else
            DG.stepping = false
            DG.Gate.Finish()      -- ★ 队列抽干 = 这一批活干完了（进度条到此收工）
        end
    end
    -- ★★★ 2026-10-03「点副本就卡死」第四刀：**首块也不抢当前帧**。''',
    'pump 收工收进度条')

rep('''DG.Loader = {
    budgetMs  = 4,      -- 每帧时间预算（ms）
    budgetObj = 96,     -- 每帧对象预算（兜底）
    preset    = "normal",
}''',
    '''DG.Loader = {
    budgetMs = 4,       -- 单块内的时间预算（ms）：块内循环据此停手，剩下的排到下一帧
    preset   = "normal",
}''',
    'Loader 去掉 budgetObj')

rep('DG.LOOT_ROW_FRAME_CAP = 24      -- 单帧最多建这么多行帧（数量兜底闸）\n',
    'DG.LOOT_ROW_FRAME_CAP = 16      -- 单块最多建这么多行帧（无计时口时的数量兜底闸）\n',
    '行帧兜底闸 24->16')

out = flat.replace('\n', style)
io.open(SRC, 'wb').write(out.encode('utf-8'))
crlf = out.count('\r\n')
print('字节 %d，CRLF %d，裸 LF %d' % (len(out.encode('utf-8')), crlf, out.count('\n') - crlf))
assert out.count('\n') - crlf == 0, '有裸 LF'
print('完成')
