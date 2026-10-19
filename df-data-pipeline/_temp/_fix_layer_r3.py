# -*- coding: utf-8 -*-
# 图钉图层断言第三轮：补 SetFrameLevel 显式压低（FontString 同层后画，仅先建不够）
import io

P = 'df_dungeon_check.py'
s = io.open(P, encoding='utf-8', newline='').read()

old = """ck('★★ ㊲b 图钉图层（第二轮）：全部钉文字挂先建的低层容器 pinText + dot 提 OVERLAY —— 图标压过全部文字（含跨钉）',
   'local pinText = CreateFrame("Frame", nil, pins)' in _mui3_src
   and 'bt.nm = MakeFS(pinText, 14, C_GOLD, "CENTER")' in _mui3_src
   and _mui3_src.find('local pinText = CreateFrame') < _mui3_src.find('for i = 1, M.MAX_PINS do')
   and 'bt.dot = bt:CreateTexture(nil, "OVERLAY")' in _mui3_src
   and 'nm:SetText("")' in _mui3_src)"""
new = """ck('★★ ㊲b 图钉图层（第三轮）：文字挂 pinText 低层容器 + 显式 SetFrameLevel 压到父层（同层 FontString 后画，仅先建不够）+ dot 提 OVERLAY',
   'local pinText = CreateFrame("Frame", nil, pins)' in _mui3_src
   and 'pinText:SetFrameLevel(math.max(pins:GetFrameLevel(), 0))' in _mui3_src
   and 'bt.nm = MakeFS(pinText, 14, C_GOLD, "CENTER")' in _mui3_src
   and 'bt.dot = bt:CreateTexture(nil, "OVERLAY")' in _mui3_src
   and 'nm:SetText("")' in _mui3_src)"""
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new, 1)
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('图层断言升级到第三轮口径')
