# -*- coding: utf-8 -*-
# 2026-10-09 给 df_dungeon_check.py 补「配方搜索 + 名称列现算」断言（静态 Python 段 + 运行时 Lua 段）
# 幂等：已插入则 SKIP。锚点不唯一/不存在即中止。原子读改写。
import sys

P = r'D:\workspace\DungeonsForever\_temp\df_dungeon_check.py'
s = open(P, 'rb').read().decode('utf-8')

if '配方搜索 + 名称列现算' in s:
    print('SKIP: 已插入过'); sys.exit(0)

def rep(old, new, tag):
    global s
    n = s.count(old)
    if n != 1:
        print('FATAL[%s]: 锚点命中 %d 次' % (tag, n)); sys.exit(1)
    s = s.replace(old, new, 1)
    print('OK %s' % tag)

# ---------- 静态段（Python 代码） ----------
rep("""       and 'PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * LV_SPLIT)' in profui)
""",
"""       and 'PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * LV_SPLIT)' in profui)
    # ⑩ 配方搜索 + 名称列现算（2026-10-09：第一列名称太宽 / 材料列截断太多 + 工具行右端加搜索框）
    ck('★★ 配方搜索框 Build 一次建好（帧数纪律）',
       'PD.searchBox = sb' in profui
       and 'CreateFrame("EditBox", nil, sb, "BackdropTemplate")' in profui)
    _otc = None
    if 'seb:SetScript("OnTextChanged"' in profui and 'seb:SetScript("OnEscapePressed"' in profui:
        _otc = profui[profui.index('seb:SetScript("OnTextChanged"'):
                                 profui.index('seb:SetScript("OnEscapePressed"')]
    ck('★★ 搜索框输入即滤：OnTextChanged 里更新搜索词并重渲染（不等回车）',
       _otc is not None and 'PD.searchQ = t' in _otc and 'PD.Render()' in _otc)
    ck('★★ 搜索按纯文本匹配（用户输入当字面量，不吃 Lua 模式字符；名称/副行/材料三路都查）',
       'function PD.SearchHit' in profui and 'function PD.SearchFilter' in profui
       and profui.count(', q, 1, true)') >= 3)
    ck('★★ 工具行给搜索框让位（首行右端留白，分类芯片不压搜索框）',
       'function PD.SearchReserve' in profui
       and 'PD.RIGHT_W - ((row == 0) and PD.SearchReserve() or 0)' in profui)
    ck('★★ 名称列按本页现算（量本页最宽名称/副行，剩余全给材料列；固定分割只在加载期兜底）',
       'function PD.FitRecipeCols' in profui
       and 'PD.MAT_X = nameW + PD.RECIPE_NAME_PAD' in profui
       and 's.mats = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)' in profui
       and 'PD.SearchFilter(PD.RecipeList())' in profui)
    ck('★ 搜不到给中文空态提示（不许白屏）',
       'L["没有名称或材料匹配「%s」的配方 —— 换个关键词再试试。"]' in profui)
""", 'static-block')

# ---------- 运行时段（Lua 字符串内） ----------
rep("""            ck("★ 材料列预算不足时不劈字（截到放得下 + …）", type(_t0) == "string")
          end

          -- ---------- 专业页的行同样支持 Shift+点击发链接 ----------
""",
"""            ck("★ 材料列预算不足时不劈字（截到放得下 + …）", type(_t0) == "string")
          end

          -- ---------- 配方搜索 + 名称列现算（2026-10-09）----------
          do
            ck("★★ 名称列按本页现算（在 [MIN,MAX] 内、材料列 = 行宽-右保留-起点-8）",
               PD.RECIPE_NAME_W ~= nil
               and PD.RECIPE_NAME_W >= PD.RECIPE_NAME_MIN
               and PD.RECIPE_NAME_W <= PD.RECIPE_NAME_MAX
               and PD.MAT_X == PD.RECIPE_NAME_W + PD.RECIPE_NAME_PAD
               and PD.MAT_W == PD.MAT_ROW_W - PD.MAT_RIGHT_RESERVE - PD.MAT_X - 8)
            ck("★★ 现算的名称列比旧的固定分割窄（省下的全给了材料列）",
               PD.MAT_X < math.floor(PD.MAT_ROW_W * 0.40),
               tostring(PD.MAT_X))
            ck("★★ 搜索框只在配方页显示（当前就在配方页）",
               PD.searchBox ~= nil and PD.searchBox.__shown == true)
            PD.SetTab("overview")
            ck("★ 切离配方页搜索框隐藏", PD.searchBox.__shown == false)
            PD.SetTab("recipe")
            do
              local _DG = TF_NS.ProfHost.DG
              local _oIN = _DG.ItemName
              _DG.ItemName = function(id)
                if (tonumber(id) or 0) % 2 == 0 then return "轻皮甲片", true end
                return "铁扣环", true
              end
              local _n0 = #(PD.specs or {})
              PD.searchQ = "轻皮"
              PD.Render()
              local _n1 = #(PD.specs or {})
              _DG.ItemName = _oIN
              PD.searchQ = nil
              PD.Render()
              local _n2 = #(PD.specs or {})
              ck("★★ 搜索词过滤列表（命中子集）且清空后全量还原",
                 _n0 > 0 and _n1 > 0 and _n1 < _n0 and _n2 == _n0,
                 tostring(_n0) .. " -> " .. tostring(_n1) .. " -> " .. tostring(_n2))
            end
          end

          -- ---------- 专业页的行同样支持 Shift+点击发链接 ----------
""", 'runtime-block')

open(P, 'wb').write(s.encode('utf-8'))
print('写入完成')
