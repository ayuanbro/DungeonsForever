# -*- coding: utf-8 -*-
"""升级 HUD 购物清单：新增「只显示缺失」开关 + 表头文案改短（2026-10-11 用户）。

用户原话：
  「在HUD需要增加一个按钮 购物清单内仅显示缺失的， 已备齐的不显示
    添加在 购物(从当前段累计到300，含银行)·共1种 这句话的右边
    这句话改为 购物清单·共1种」

改动（全部落在 Core/ProfFollow.lua，LF 保持）：
  ① onlyMissView()：读装置级偏好 DungeonsForeverDB.prof.shopOnlyMiss
  ② 建 f.shop.missTog（CheckButton，复用专业页同款胶囊开关皮）+ 表头让位限宽
  ③ 表头文案换键：L["购物清单"] .. " · " .. format(L["共%d种"], #shown)
  ④ Paint：按开关过滤出 shown（在算列宽之前，免得被滤掉的名字撑宽名字列）
  ⑤ 只改渲染，**不动** shopList / DoImport 口径 —— 一键导入始终导全量。

用法：python _temp/patch_hud_shoponlymissing.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
P = os.path.join(DF, 'Core', 'ProfFollow.lua')

b = open(P, 'rb').read()
if b.count(b'\r\n'):
    sys.exit('文件不是纯 LF（CRLF %d），先停下' % b.count(b'\r\n'))
orig = len(b)
_edits = []


def rep(old, new, cnt=1):
    global b
    o = old.encode('utf-8')
    w = new.encode('utf-8')
    got = b.count(o)
    if got != cnt:
        sys.exit('锚点命中 %d 次（期望 %d）：%r' % (got, cnt, old[:110]))
    b = b.replace(o, w, 1)
    _edits.append(old.strip().split('\n')[0][:60])


# ── ① 视图开关读取（放在 dbProf 之后、st() 之前）─────────────────────────
rep(
    '''-- 当前角色的跟随状态（收窗只标记 hidden，进度保留）
local function st()''',
    '''-- 购物清单「只显示缺失」视图开关（2026-10-11 用户：已备齐的不显示）。
-- 属装置级偏好而非角色进度 ⇒ 存 prof.shopOnlyMiss，不跟角色走。
-- 只作用在渲染（滤掉已备齐行）；shopList / DoImport 口径不变，一键导入仍导全量。
local function onlyMissView()
    return dbProf().shopOnlyMiss and true or false
end

-- 当前角色的跟随状态（收窗只标记 hidden，进度保留）
local function st()''')

# ── ② 建开关 + 表头让位 ────────────────────────────────────────────────
rep(
    '''    f.shop.head = MakeFS(f.shop, 14, C_HEAD, "LEFT")
    f.shop.head:SetPoint("TOPLEFT", f.shop, "TOPLEFT", 8, -8)
''',
    '''    f.shop.head = MakeFS(f.shop, 14, C_HEAD, "LEFT")
    f.shop.head:SetPoint("TOPLEFT", f.shop, "TOPLEFT", 8, -8)
    -- 表头右侧「只显示缺失」开关（2026-10-11 用户）。购物面板会随两栏加宽，宽度不定，
    -- 故表头右侧锚到开关左侧让位（超长走 MaxWidth 省略号，不压到开关上）。
    local SHOP_TOG_W = 96
    f.shop.head:SetPoint("RIGHT", f.shop, "RIGHT", -(SHOP_TOG_W + 10), 0)
    f.shop.head:SetWordWrap(false)
    f.shop.missTog = CreateFrame("CheckButton", nil, f.shop)
    f.shop.missTog:SetSize(36, 20)
    f.shop.missTog:EnableMouse(true)
    -- 复用专业页设置页同款胶囊开关皮（桩/实机都不自建纹理分支）
    if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(f.shop.missTog) end
    f.shop.missTog:SetPoint("TOPRIGHT", f.shop, "TOPRIGHT", -6, -4)
    f.shop.missTog:SetScript("OnClick", function(self)
        dbProf().shopOnlyMiss = not onlyMissView()
        self:SetChecked(onlyMissView())
        PF.Paint()          -- 滚动位置由 Paint 内的 maxScroll 夹紧，这里不重复算
        ns.PlaySound(1)
    end)
    f.shop.missTog:SetChecked(onlyMissView())
    TipOn(f.shop.missTog, L["只显示缺失"],
          L["开启：购物清单只列出还缺的材料，已备齐的自动隐藏。"])
''')

# ── ③ 表头文案 + 过滤（必须在算列宽之前）────────────────────────────────
rep(
    '''        local list = shopList(s)
        f.shop.head:SetText(L["购物（从当前段累计到 300，含银行）"] .. format(" · 共%d种", #list))''',
    '''        local list = shopList(s)
        -- ★ 过滤要排在算各列宽之前：否则被滤掉的长名字仍会把名字列撑宽（右留一片白）。
        --   shopList 内已把 e.have 填好（= Have(id)），这里只补 missing，不重复取背包。
        local shown = {}
        for _, e in ipairs(list) do
            e.missing = e.need - e.have
            if (not onlyMissView()) or e.missing > 0 then shown[#shown + 1] = e end
        end
        f.shop.head:SetText(L["购物清单"] .. format(L[" · 共%d种"], #shown))
        f.shop.missTog:SetChecked(onlyMissView())''')

# ── ④ 行表改扫过滤后的 shown ───────────────────────────────────────────
rep(
    '''        for _, e in ipairs(list) do
            local nm, got = DG.ItemName(e.id)
            if not got then DG.RequestItem(e.id) pending = true end''',
    '''        for _, e in ipairs(shown) do
            local nm, got = DG.ItemName(e.id)
            if not got then DG.RequestItem(e.id) pending = true end''')

open(P, 'wb').write(b)
print('patched OK：%d 处，len %d -> %d' % (len(_edits), orig, len(b)))
for i, e in enumerate(_edits, 1):
    print('  %2d) %s' % (i, e))
print('CRLF %d / bareLF %d' % (b.count(b'\r\n'), b.count(b'\n') - b.count(b'\r\n')))
