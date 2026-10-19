# -*- coding: utf-8 -*-
"""一次性字节补丁：购物清单空清单也必须打开面板（2026-10-11 用户）。

用户反馈：「如果我把这个开关打开了之后，就永远点不开购物清单了。所以，当我所有的
东西都备齐了之后，还是能显示的，只是显示一条灰色字：所有物品已备齐」

根因：`PF.Paint` 的购物清单块里，行数 `n == 0` 时走 `else f.shop:Hide()`。
开关「只显示缺失」一开、材料又全备齐 ⇒ `#shown == 0` ⇒ `n == 0` ⇒ 面板被隐藏，
于是「永远点不开」。修法：n == 0 也一律 Show，给一行灰字说明为什么没有行。

两处编辑：
  1. 建 `f.shop.empty`（14 号灰字，一行）。
  2. `if n > 0 ... else f.shop:Hide() end` → else 也摆位 + Show + 设灰字。

用法：python _temp/patch_hud_shopempty.py [--dry]
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Core', 'ProfFollow.lua')

EDIT1_OLD = '''    TipOn(f.shop.missTog, L["只显示缺失"],
          L["开启：购物清单只列出还缺的材料，已备齐的自动隐藏。"])
'''
EDIT1_NEW = '''    TipOn(f.shop.missTog, L["只显示缺失"],
          L["开启：购物清单只列出还缺的材料，已备齐的自动隐藏。"])
    -- 空清单提示（一行灰字；n==0 时代替行区，见 Paint。2026-10-11 用户：
    --   开关一开且全备齐就「永远点不开购物清单」→ 面板必须照常显示）。
    f.shop.empty = MakeFS(f.shop, 14, C_GREY, "LEFT")
    f.shop.empty:SetPoint("TOPLEFT", f.shop, "TOPLEFT", 8, -30)
    f.shop.empty:Hide()
'''

EDIT2_OLD = '''        if n > 0 then
            local shopH = 30 + n * 20 + 10   -- 2026-10-08 晚：导入按钮挪到底部按钮排，页脚 26px 预留取消
            f.shop:ClearAllPoints()
            f.shop:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, y)
            f.shop:SetSize(W - 2 * PAD, shopH)
            f.shop:Show()
            y = y - shopH - 8
        else
            f.shop:Hide()
        end
'''
EDIT2_NEW = '''        if n > 0 then
            local shopH = 30 + n * 20 + 10   -- 2026-10-08 晚：导入按钮挪到底部按钮排，页脚 26px 预留取消
            f.shop.empty:Hide()
            f.shop:ClearAllPoints()
            f.shop:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, y)
            f.shop:SetSize(W - 2 * PAD, shopH)
            f.shop:Show()
            y = y - shopH - 8
        else
            -- ★ 空清单也必须把面板打开（2026-10-11 用户）。原先 n == 0 直接 Hide ⇒
            --   开关「只显示缺失」一开、材料又全备齐（#shown == 0）就「永远点不开清单」。
            --   改为一律 Show，用一行灰字说明为什么没有行：
            --     · 本来有材料、全被「只显示缺失」滤掉 ⇒ 所有物品已备齐
            --     · 本来就没有材料（当前段之后无配方材料） ⇒ 无材料（复用既有键）
            f.shop.empty:SetText(#list > 0 and L["所有物品已备齐"] or L["无材料"])
            f.shop.empty:Show()
            local shopH = 30 + 20 + 10
            f.shop:ClearAllPoints()
            f.shop:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, y)
            f.shop:SetSize(W - 2 * PAD, shopH)
            f.shop:Show()
            y = y - shopH - 8
        end
'''

DRY = '--dry' in sys.argv
b = io.open(SRC, 'rb').read()
assert b.count(b'\r') == 0, '源文件不是纯 LF，先查（本项目禁 CRLF）'
txt = b.decode('utf-8')

edits = [('建 f.shop.empty 灰字', EDIT1_OLD, EDIT1_NEW),
         ('n==0 也打开面板 + 设灰字', EDIT2_OLD, EDIT2_NEW)]
for name, old, new in edits:
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
