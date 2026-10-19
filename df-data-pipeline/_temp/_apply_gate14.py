# -*- coding: utf-8 -*-
"""第十刀（小改）：载入进度条挪到主窗口最上边框（用户选方案 A，2026-10-04）。

现状：条锚在内容面板（U.panel，960 宽）顶上 —— 面板首行内容紧贴面板顶，
3px 的条正好叠在内容上（用户反馈「进度条和内容有重叠」）。
改为：锚主窗体 host（1000 宽）最上沿，左右各缩进 8px 躲开 hui 窗皮圆角；
与任何内容零重叠。填充宽度按「窗宽 - 16」现算（桩环境 GetWidth 返回表值，
必须 type 守卫 + 常量兜底）。右下「正在载入… / 跳过」胶囊不动。
"""
import io

P1 = 'Core/DungeonUI.lua'
s = io.open(P1, encoding='utf-8', newline='').read()
ORIG1 = s

OLD1 = ('    local bar = CreateFrame("Frame", nil, panel)\r\n'
        '    bar:SetFrameLevel(panel:GetFrameLevel() + 20)\r\n'
        '    bar:SetPoint("TOPLEFT", panel, "TOPLEFT", 0, 0)\r\n'
        '    bar:SetPoint("TOPRIGHT", panel, "TOPRIGHT", 0, 0)\r\n'
        '    bar:SetHeight(3)\r\n')
NEW1 = ('    -- ★★ 贴主窗口最上边框（2026-10-04 用户选方案 A）：锚 host（窗体 1000 宽）而不是\r\n'
        '    --   内容面板 —— 面板首行内容紧贴面板顶，3px 条压内容；窗沿这条与内容零重叠。\r\n'
        '    --   左右各缩进 8px 躲开 hui 窗皮的圆角；填充宽度按「窗宽 - 16」现算\r\n'
        '    --   （桩环境测量 API 返回表值 ⇒ type 守卫 + 常量兜底，见 2026-10-03 探索页教训）。\r\n'
        '    local host = panel:GetParent() or panel\r\n'
        '    local bar = CreateFrame("Frame", nil, host)\r\n'
        '    bar:SetFrameLevel(host:GetFrameLevel() + 20)\r\n'
        '    bar:SetPoint("TOPLEFT", host, "TOPLEFT", 8, 0)\r\n'
        '    bar:SetPoint("TOPRIGHT", host, "TOPRIGHT", -8, 0)\r\n'
        '    bar:SetHeight(3)\r\n'
        '    do\r\n'
        '        local gw = 1000\r\n'
        '        local mw = host.GetWidth and host:GetWidth()\r\n'
        '        if type(mw) == "number" and mw > 0 then gw = mw end\r\n'
        '        DG.Gate.w = gw - 16\r\n'
        '    end\r\n')
assert s.count(OLD1) == 1, '锚点命中 %d 次' % s.count(OLD1)
s = s.replace(OLD1, NEW1, 1)
bare = s.replace('\r\n', '').count('\n')
assert bare == 0, 'DungeonUI 出现裸 LF %d' % bare
io.open(P1, 'w', encoding='utf-8', newline='').write(s)
print('[OK] DungeonUI.lua 进度条贴主窗口顶沿（%d -> %d 字节）'
      % (len(ORIG1.encode('utf-8')), len(s.encode('utf-8'))))
