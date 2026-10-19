# -*- coding: utf-8 -*-
"""一次性字节补丁：购物清单「仅显示缺失」开关左侧补文字标签（2026-10-11 用户）。

用户原话：「只显示缺失的这个开关，左边写上文字“仅显示缺失”」

布局算式（沿面板右缘向左，负号 = 往左）：
  · 开关：右缘 -6，宽 36            ⇒ 左缘 -42
  · 标签：锚在开关左缘 -4（RIGHT 对齐） ⇒ 右缘 -46，左缘 -(46 + labW)
  · 表头：右缘 = -(SHOP_TOG_W + 10)   （SetPoint 里那个 +10 是表头↔标签的间隔）
  要表头不压标签：SHOP_TOG_W + 10 ≥ 46 + labW + 12
                ⇒ SHOP_TOG_W ≥ labW + 48  ⇒ 取 SHOP_TOG_W = labW + 48

labW 必须**实测**：英文 "Missing only"（12 半角 ≈ 92px）几乎是中文「仅显示缺失」
（5 全角 = 70px）的一倍半，写死 96 会让 enUS 的标签压到表头上。

两处编辑：
  1. `SHOP_TOG_W = 96` → 按 `ns.ProfModule.TextW` 实测标签宽现算（带 pcall + 兜底）。
  2. `missTog:SetPoint(...)` 之后新建 `f.shop.missLab`（14px、C_TEXT、右对齐）。
     ★ 标签必须挂 `f.shop`（父帧），不能挂开关本身 ——
       `ns.hui.ReskinToggle` 的 `PurgeNative` 会 Hide 掉开关上一切非自建子件。

用法：python _temp/patch_hud_misstog_label.py [--dry]
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Core', 'ProfFollow.lua')

EDIT1_OLD = '''    local SHOP_TOG_W = 96
'''

EDIT1_NEW = '''    -- 让位量 = 开关 36 + 间隔 4 + 标签宽 labW + 表头↔标签 8（下面 SetPoint 里另有 +10）。
    --   labW 必须实测：英文 "Missing only" 比中文「仅显示缺失」宽近一半，写死会让 enUS 压表头。
    local labW = 70
    do
        local PDw = ns.ProfModule
        if PDw and PDw.TextW then
            local okw, wv = pcall(PDw.TextW, L["仅显示缺失"], 14)
            if okw and type(wv) == "number" then labW = math.ceil(wv) end
        end
    end
    local SHOP_TOG_W = labW + 48
'''

EDIT2_OLD = '''    f.shop.missTog:SetPoint("TOPRIGHT", f.shop, "TOPRIGHT", -6, -4)
'''

EDIT2_NEW = '''    f.shop.missTog:SetPoint("TOPRIGHT", f.shop, "TOPRIGHT", -6, -4)
    -- 开关左侧的文字标签（2026-10-11 用户：「只显示缺失的这个开关，左边写上文字“仅显示缺失”」）。
    --   ★ 标签必须挂 f.shop（父帧），不能挂开关：ReskinToggle 的 PurgeNative 会把开关上
    --     一切「非自建子件」Hide 掉 —— 挂上去当场消失，实机看不到。
    f.shop.missLab = MakeFS(f.shop, 14, C_TEXT, "RIGHT")
    f.shop.missLab:SetWordWrap(false)
    f.shop.missLab:SetPoint("RIGHT", f.shop.missTog, "LEFT", -4, 0)
    f.shop.missLab:SetText(L["仅显示缺失"])
'''

DRY = '--dry' in sys.argv
b = io.open(SRC, 'rb').read()
assert b.count(b'\r') == 0, '源文件不是纯 LF，先查（本项目禁 CRLF）'
txt = b.decode('utf-8')

for name, old, new in [('表头让位量按标签实测宽现算', EDIT1_OLD, EDIT1_NEW),
                       ('开关左侧新增「仅显示缺失」标签', EDIT2_OLD, EDIT2_NEW)]:
    cnt = txt.count(old)
    assert cnt == 1, '锚点命中 %d 次（要求 1）：%s' % (cnt, name)
    txt = txt.replace(old, new, 1)
    print('[OK] %s' % name)

if DRY:
    print('（--dry：未写盘）')
    sys.exit(0)

io.open(SRC, 'wb').write(txt.encode('utf-8'))
b2 = io.open(SRC, 'rb').read()
assert b2.count(b'\r') == 0, '写回后出现 CR'
print('写入 %s：%d → %d 字节' % (SRC, len(b), len(b2)))
