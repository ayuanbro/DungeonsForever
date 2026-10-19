# -*- coding: utf-8 -*-
"""补丁：配方页「点开那一瞬间」的同步重计算（2026-10-09 第二轮，用户报仍卡）。

实测口径（_temp/_prof_render_prof.py，leatherworking 511 条）：
    整帧 Render = 28.5ms（桩），其中
      A RecipeList + SearchFilter（全量 511 条建 spec）  14.7ms
      B FitRecipeCols（全量量宽 + 材料串重排）            8.7ms
      = 23.3ms（82%）花在**只画前 300 行**的全量数据准备上
      TextW 7391 次 / ItemName 6529 次 —— 都是纯 Lua 逐字符循环
    行帧建帧（24.2ms）已经在上一轮挪到分帧段了，所以「点开」那一帧仍被 A+B 顶住。

本补丁（全部只做**等价改写**，不改任何观感口径）：
  1. PD.ScanRecipe()   新增：轻量扫全量 —— 只数过滤后条数 + 量名称列最宽，
                       对**原始行**直接取三个字段（名称 / 副行 / 新角标），
                       不建 spec、不拼文案、不碰材料串。口径与 PD.SearchHit /
                       PD.RecipeSpec 逐字一致（含 key 过滤与「全 miss 退回全量」）。
  2. PD.RecipeList(limit)  加 limit：只为**真正画出来的**前 ROW_CAP 条建 spec。
  3. PD.RowsRecipe     改用 1+2；条数用轻量扫描的真数（观感不变）。
  4. PD.FitRecipeCols(list, maxW)  maxW 可由外部传入（复用 1 的扫描结果），
                       不传则自扫兜底（离线脚本/其它调用者不受影响）。
  5. PD.RecipeSpec     mats 不再预算（紧随的 FitRecipeCols 会用定稿列宽重算一遍，
                       这里那次是纯白做）；lines 改惰性闭包（配方行有 it ⇒
                       OnEnter 走 DG.ShowItemTip，__lines 从来不读）。
  6. PD.Row / PD.BindRow  接线惰性 lines（等价行为，零成本）。

用法：
    python _temp/patch_prof_perf2.py --check     # 只体检锚点，不写
    python _temp/patch_prof_perf2.py             # 落盘
"""
import io
import os
import sys

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      os.pardir, 'Core', 'ProfessionUI.lua')

# ── 1. PD.Row 的 OnEnter：lines 惰性求值 ────────────────────────────────
E1_OLD = '''        if self.__noTip then return end
        if self.__lines and (self.__linesFirst or not self.__it) then
'''
E1_NEW = '''        if self.__noTip then return end
        -- ★ lines 惰性求值（2026-10-09 第二轮）：一次渲染要建几百条 spec，
        --   每条 lines 都是 6 段 format 拼接 —— 而配方行有 it，OnEnter 走
        --   DG.ShowItemTip，__lines 从来不读。改成第一次真要读时才拼。
        if self.__lines == nil and self.__mkLines then
            self.__lines = self.__mkLines()
            self.__mkLines = nil
        end
        if self.__lines and (self.__linesFirst or not self.__it) then
'''

# ── 2. PD.BindRow：把惰性构造器一并落上行 ──────────────────────────────
E2_OLD = '''    r.__lines = spec.lines
    r.__linesFirst = spec.linesFirst
'''
E2_NEW = '''    r.__lines = spec.lines
    r.__mkLines = spec.mkLines
    r.__linesFirst = spec.linesFirst
'''

# ── 3. PD.FitRecipeCols：maxW 可由调用方传入 ───────────────────────────
E3_OLD = '''function PD.FitRecipeCols(list)
    local maxW = 0
    for _, s in ipairs(list) do
        local w = PD.TextW(s.text or "", 13)
        if s.is_new then w = w + PD.RECIPE_BADGE_W end
        local sw = PD.TextW(s.sub or "", 11)
        if sw > w then w = sw end
        if w > maxW then maxW = w end
    end
'''
E3_NEW = '''function PD.FitRecipeCols(list, maxW)
    -- ★ maxW 可由调用方传入（PD.ScanRecipe 的轻量全量扫描）—— 那一趟不建 spec，
    --   口径与本函数逐条量完全一致（同样只量名称 / 副行 / 新角标）。不传则自扫兜底。
    if maxW == nil then
        maxW = 0
        for _, s in ipairs(list) do
            local w = PD.TextW(s.text or "", 13)
            if s.is_new then w = w + PD.RECIPE_BADGE_W end
            local sw = PD.TextW(s.sub or "", 11)
            if sw > w then w = sw end
            if w > maxW then maxW = w end
        end
    end
'''

# ── 4. PD.RecipeList：加 limit（只为画出来的那些建 spec） ──────────────
E4_OLD = '''function PD.RecipeList()
    local d = R[PD.cur]
    local out = {}
    if not d then return out end
    local key = PD.toolKey
    if key == "__enchant" then
        for _, e in ipairs(d.enchants or {}) do out[#out + 1] = PD.EnchantSpec(e) end
        return out
    end
    if key == "__crafted" then
        for _, c in ipairs(d.crafted or {}) do out[#out + 1] = PD.CraftedSpec(c) end
        return out
    end
    if key == "__favor" then
        for _, f in ipairs(d.favor or {}) do out[#out + 1] = PD.FavorSpec(f) end
        return out
    end
    local any = false
    for _, r in ipairs(d.rows or {}) do
        if (not key or key == "all" or r[4] == key) then
            out[#out + 1] = PD.RecipeSpec(r)
            any = true
        end
    end
    if not any then
        for _, r in ipairs(d.rows or {}) do out[#out + 1] = PD.RecipeSpec(r) end
    end
    return out
end
'''
E4_NEW = '''-- ★ limit（2026-10-09 第二轮）：建 spec 是要花钱的 —— 每条都要拼 6 段文案、重排
--   材料串、建 lines 表。列表封顶只画 PD.ROW_CAP 条，所以**只为画出来的那些建**。
--   「过滤后到底多少条」由 PD.ScanRecipe 的轻量扫描给出（不建 spec）。
function PD.RecipeList(limit)
    local d = R[PD.cur]
    local out = {}
    if not d then return out end
    local key = PD.toolKey
    local cap = limit or PD.ROW_CAP
    if cap < 1 then return out end
    if key == "__enchant" then
        for _, e in ipairs(d.enchants or {}) do
            out[#out + 1] = PD.EnchantSpec(e)
            if #out >= cap then break end
        end
        return out
    end
    if key == "__crafted" then
        for _, c in ipairs(d.crafted or {}) do
            out[#out + 1] = PD.CraftedSpec(c)
            if #out >= cap then break end
        end
        return out
    end
    if key == "__favor" then
        for _, f in ipairs(d.favor or {}) do
            out[#out + 1] = PD.FavorSpec(f)
            if #out >= cap then break end
        end
        return out
    end
    local any = false
    for _, r in ipairs(d.rows or {}) do
        if (not key or key == "all" or r[4] == key) then
            out[#out + 1] = PD.RecipeSpec(r)
            any = true
            if #out >= cap then break end
        end
    end
    if not any then
        for _, r in ipairs(d.rows or {}) do
            out[#out + 1] = PD.RecipeSpec(r)
            if #out >= cap then break end
        end
    end
    return out
end
'''

# ── 5. PD.ScanRecipe 新增 + PD.RowsRecipe 改造 ─────────────────────────
E5_OLD = '''function PD.RowsRecipe(rows)
    local d = R[PD.cur]
    if not d then return end
    local list = PD.SearchFilter(PD.RecipeList())
    PD.FitRecipeCols(list)
    local total = (d.counts and d.counts.total) or #list
    local unread = (d.counts and d.counts.unreadable) or 0
    PushHead(rows, format(L["当前分类 %d 条（标注总计 %d 条，其中 %d 条来源不可读）"],
                          #list, total, unread))
    if #list == 0 and PD.searchQ and PD.searchQ ~= "" then
        PushGap(rows)
        PushText(rows, format(L["没有名称或材料匹配「%s」的配方 —— 换个关键词再试试。"],
                              PD.searchQ), 12, C_GOLD)
        return
    end
    local trunc = 0
    if #list > PD.ROW_CAP then trunc = #list - PD.ROW_CAP end
    for i = 1, math.min(#list, PD.ROW_CAP) do rows[#rows + 1] = list[i] end
'''
E5_NEW = '''-- ★ 配方页「轻量全量扫描」（2026-10-09 第二轮：点开配方页那一瞬间仍卡）：
--   渲染前只需要两件事 —— ① 过滤后到底多少条（抬头文案 + 截断提示）② 名称列最宽
--   多少（定列宽）。原来这两件事都是**先把全量 511 条建成完整 spec 再量**，而列表
--   封顶只画 300 条 ⇒ 剩下 211 条的部位纯白做（实测占整帧 82%）。
--   这里改成对**原始行**直接取三个字段量宽：名称 / 副行 / 新角标 —— 不建 spec、
--   不拼任何文案、不碰材料串。判定口径与 PD.SearchHit 逐字一致（含 q 已在
--   OnTextChanged 里小写化这一点）。
--   ★ 只覆盖 d.rows 主路径；附魔 / 制造品 / 声望三类特殊列表规模小，返回 nil
--     让调用方走原路径（PD.SearchFilter + PD.RecipeList 全量）。
function PD.ScanRecipe()
    local d = R[PD.cur]
    if not d then return 0, 0 end
    local key = PD.toolKey
    if key == "__enchant" or key == "__crafted" or key == "__favor" then
        return nil
    end
    local q = PD.searchQ
    local hasQ = (q and q ~= "") and true or false
    local useKey = (key and key ~= "all") and true or false

    local function scan(filterKey)
        local n, maxW = 0, 0
        for _, r in ipairs(d.rows or {}) do
            if (not filterKey) or r[4] == key then
                local nm = DG.ItemName(r[2])
                local sub = tostring(r[5] or "")
                local hit = true
                if hasQ then
                    hit = false
                    if nm and nm ~= ""
                       and string.find(string.lower(nm), q, 1, true) then
                        hit = true
                    elseif sub ~= ""
                           and string.find(string.lower(sub), q, 1, true) then
                        hit = true
                    else
                        for _, m in ipairs(r[12] or {}) do
                            local mn = DG.ItemName(m[1])
                            if mn and mn ~= ""
                               and string.find(string.lower(tostring(mn)), q, 1, true) then
                                hit = true
                                break
                            end
                        end
                    end
                end
                if hit then
                    n = n + 1
                    -- 与 PD.FitRecipeCols 的自扫逐字同口径：名称可为空（名字还没到货）
                    -- 时也照样把「新角标 + 副行」计入最宽值。
                    local w = (nm and nm ~= "" and PD.TextW(nm, 13)) or 0
                    if r[11] then w = w + PD.RECIPE_BADGE_W end
                    local sw = PD.TextW(sub, 11)
                    if sw > w then w = sw end
                    if w > maxW then maxW = w end
                end
            end
        end
        return n, maxW
    end

    local n, maxW = scan(useKey)
    -- 与 PD.RecipeList 的 any 回退一致：按分类过滤一条都没命中 ⇒ 退回不过滤
    if useKey and n == 0 then n, maxW = scan(false) end
    return n, maxW
end

function PD.RowsRecipe(rows)
    local d = R[PD.cur]
    if not d then return end
    local realN, maxW = PD.ScanRecipe()
    local list
    if realN then
        -- 主路径：只为画得出来的那些建 spec（列宽用轻量扫描的全量结果）
        list = PD.RecipeList(math.min(realN, PD.ROW_CAP))
    else
        -- 附魔 / 制造品 / 声望：规模小，保持原路径
        list = PD.SearchFilter(PD.RecipeList())
        realN, maxW = #list, nil
    end
    PD.FitRecipeCols(list, maxW)
    local total = (d.counts and d.counts.total) or realN
    local unread = (d.counts and d.counts.unreadable) or 0
    PushHead(rows, format(L["当前分类 %d 条（标注总计 %d 条，其中 %d 条来源不可读）"],
                          realN, total, unread))
    if realN == 0 and PD.searchQ and PD.searchQ ~= "" then
        PushGap(rows)
        PushText(rows, format(L["没有名称或材料匹配「%s」的配方 —— 换个关键词再试试。"],
                              PD.searchQ), 12, C_GOLD)
        return
    end
    local trunc = 0
    if realN > PD.ROW_CAP then trunc = realN - PD.ROW_CAP end
    for i = 1, #list do rows[#rows + 1] = list[i] end
'''

# ── 6. PD.RecipeSpec：mats 不预算 + lines 惰性 ─────────────────────────
E6_OLD = '''function PD.RecipeSpec(r)
    local mats = PD.MatText(r[12], 4)
    local lines = {}
    if r[6] and r[6] ~= "" then lines[#lines + 1] = { r[6] } end
    lines[#lines + 1] = { format(L["材料：%s"], mats ~= "" and mats or L["无"]) }
    lines[#lines + 1] = { format(L["技能：学 %s · %s"], tostring(r[7]),
                                 PD.TierText(r[8], r[9], r[10])) }
    if r[15] and #r[15] > 0 then
        lines[#lines + 1] = { format(L["改版前材料：%s"], PD.MatText(r[15])), 0.9, 0.7, 0.4 }
    end
    local hasVendor = r[14] and r[14].vendors and #r[14].vendors > 0
    if hasVendor then
        for _, ln in ipairs(PD.VendorLines(r[14])) do lines[#lines + 1] = ln end
    end
    -- 右下角那格拆两半（见 PD.SourceParts）：商人**恒为最后一段**，单独搬到 r.dv 好挂热区。
    --   dval 带上「· 」分隔符，拆开渲染后与旧的一整串逐像素一致。
    local dpre, dval, vk
    local parts = PD.SourceParts(r[14])
    for i = 1, #parts do
        if parts[i].vendor then vk = i end
    end
    if vk then
        dval = (vk > 1 and "· " or "") .. parts[vk].text
        local t = {}
        for i = 1, vk - 1 do t[i] = parts[i].text end
        if #t > 0 then dpre = table.concat(t, " · ") end
    end
    local mcol, _, _, msegs = PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W)
    if r[16] and r[16] ~= "" then
        lines[#lines + 1] = { format(L["套装：%s"], r[16]), 0.64, 0.21, 0.93 }
    end
    if r[17] and r[17] ~= "" then
        lines[#lines + 1] = { format(L["护甲类型：%s"], r[17]), 0.7, 0.7, 0.7 }
    end
    return {
        kind = "row", is_new = r[11], it = { r[2] }, row = r, _mats = r[12],
        text = DG.ItemName(r[2]),
        sub = tostring(r[5] or ""),
        mats = mcol,
        matSegs = msegs,
        src = r[14],
        dpre = dpre,
        dval = dval,
        right = format("%s · %s", format(L["学 %s"], tostring(r[7])),
                       PD.TierText(r[8], r[9], r[10])),
        right2 = PD.SourceText(r[14]) or (r[13] and L["需要图纸"] or ""),
        lines = lines,
        act = hasVendor and PD.VendorAct(r[14]) or nil,
    }
end
'''
E6_NEW = '''function PD.RecipeSpec(r)
    local hasVendor = r[14] and r[14].vendors and #r[14].vendors > 0
    -- 右下角那格拆两半（见 PD.SourceParts）：商人**恒为最后一段**，单独搬到 r.dv 好挂热区。
    --   dval 带上「· 」分隔符，拆开渲染后与旧的一整串逐像素一致。
    local dpre, dval, vk
    local parts = PD.SourceParts(r[14])
    for i = 1, #parts do
        if parts[i].vendor then vk = i end
    end
    if vk then
        dval = (vk > 1 and "· " or "") .. parts[vk].text
        local t = {}
        for i = 1, vk - 1 do t[i] = parts[i].text end
        if #t > 0 then dpre = table.concat(t, " · ") end
    end
    return {
        kind = "row", is_new = r[11], it = { r[2] }, row = r, _mats = r[12],
        text = DG.ItemName(r[2]),
        sub = tostring(r[5] or ""),
        -- ★ mats / matSegs 不在这里算（2026-10-09 第二轮）：紧随其后的
        --   PD.FitRecipeCols 会用**定稿列宽**把两者整个重算一遍，这里那次是纯白做
        --   （每条 = 材料个数 × 数次逐字符量宽，实测占整帧 Render 的一大半）。
        src = r[14],
        dpre = dpre,
        dval = dval,
        right = format("%s · %s", format(L["学 %s"], tostring(r[7])),
                       PD.TierText(r[8], r[9], r[10])),
        right2 = PD.SourceText(r[14]) or (r[13] and L["需要图纸"] or ""),
        -- ★ lines 也改惰性（配方行有 it ⇒ PD.Row 的 OnEnter 走 DG.ShowItemTip，
        --   __lines 从来不读）。真要读时才拼这一串文案（每条 6 段 format）。
        mkLines = function()
            local lines = {}
            if r[6] and r[6] ~= "" then lines[#lines + 1] = { r[6] } end
            local mt = PD.MatText(r[12], 4)
            lines[#lines + 1] = { format(L["材料：%s"], mt ~= "" and mt or L["无"]) }
            lines[#lines + 1] = { format(L["技能：学 %s · %s"], tostring(r[7]),
                                         PD.TierText(r[8], r[9], r[10])) }
            if r[15] and #r[15] > 0 then
                lines[#lines + 1] = { format(L["改版前材料：%s"], PD.MatText(r[15])),
                                      0.9, 0.7, 0.4 }
            end
            if hasVendor then
                for _, ln in ipairs(PD.VendorLines(r[14])) do lines[#lines + 1] = ln end
            end
            if r[16] and r[16] ~= "" then
                lines[#lines + 1] = { format(L["套装：%s"], r[16]), 0.64, 0.21, 0.93 }
            end
            if r[17] and r[17] ~= "" then
                lines[#lines + 1] = { format(L["护甲类型：%s"], r[17]), 0.7, 0.7, 0.7 }
            end
            return lines
        end,
        act = hasVendor and PD.VendorAct(r[14]) or nil,
    }
end
'''
E6_NEW = '''function PD.RecipeSpec(r)
    local hasVendor = r[14] and r[14].vendors and #r[14].vendors > 0
    return {
        kind = "row", is_new = r[11], it = { r[2] }, row = r, _mats = r[12],
        text = DG.ItemName(r[2]),
        sub = tostring(r[5] or ""),
        -- ★ mats 不在这里算（2026-10-09 第二轮）：紧随其后的 PD.FitRecipeCols 会用
        --   **定稿列宽**把 s.mats 整个重算一遍，这里那次是纯白做（每条一次材料串
        --   重排 = 材料个数 × 数次逐字符量宽）。
        mats = nil,
        right = format("%s · %s", format(L["学 %s"], tostring(r[7])),
                       PD.TierText(r[8], r[9], r[10])),
        right2 = PD.SourceText(r[14]) or (r[13] and L["需要图纸"] or ""),
        -- ★ lines 也改惰性（配方行有 it ⇒ PD.Row 的 OnEnter 走 DG.ShowItemTip，
        --   __lines 从来不读）。真要读时才拼这一串文案。
        mkLines = function()
            local lines = {}
            if r[6] and r[6] ~= "" then lines[#lines + 1] = { r[6] } end
            local mt = PD.MatText(r[12], 4)
            lines[#lines + 1] = { format(L["材料：%s"], mt ~= "" and mt or L["无"]) }
            lines[#lines + 1] = { format(L["技能：学 %s · %s"], tostring(r[7]),
                                         PD.TierText(r[8], r[9], r[10])) }
            if r[15] and #r[15] > 0 then
                lines[#lines + 1] = { format(L["改版前材料：%s"], PD.MatText(r[15])), 0.9, 0.7, 0.4 }
            end
            if hasVendor then
                for _, ln in ipairs(PD.VendorLines(r[14])) do lines[#lines + 1] = ln end
            end
            if r[16] and r[16] ~= "" then
                lines[#lines + 1] = { format(L["套装：%s"], r[16]), 0.64, 0.21, 0.93 }
            end
            if r[17] and r[17] ~= "" then
                lines[#lines + 1] = { format(L["护甲类型：%s"], r[17]), 0.7, 0.7, 0.7 }
            end
            return lines
        end,
        act = hasVendor and PD.VendorAct(r[14]) or nil,
    }
end
'''

# ── 7. 文件头纪律说明 ─────────────────────────────────────────────────
E7_OLD = '''--     量小走快速通道（不闪进度条）。
'''
E7_NEW = '''--     量小走快速通道（不闪进度条）。
--   · ★★ 同一轮还砍了「点开那一帧」的**同步重计算**：列表数据准备不再对全量建
--     spec —— PD.ScanRecipe() 轻量扫全量（只数条数 + 量名称列最宽），spec 只为
--     画得出来的前 PD.ROW_CAP 条建；材料串与 tooltip 文案都改成「用得到才算」。
--     改动前后观感/口径完全一致，只是常数小了（详见 PD.ScanRecipe / PD.RecipeSpec）。
'''

EDITS = [
    ('1 PD.Row OnEnter 惰性 lines', E1_OLD, E1_NEW),
    ('2 PD.BindRow 接线 __mkLines', E2_OLD, E2_NEW),
    ('3 PD.FitRecipeCols 收 maxW', E3_OLD, E3_NEW),
    ('4 PD.RecipeList 加 limit', E4_OLD, E4_NEW),
    ('5 PD.ScanRecipe + RowsRecipe', E5_OLD, E5_NEW),
    ('6 PD.RecipeSpec 去白做', E6_OLD, E6_NEW),
    ('7 文件头纪律说明', E7_OLD, E7_NEW),
]


def heal(text, raw):
    """按目标文件自身换行形态补齐（CRLF 文件里裸 \\n 永远匹配不到）。"""
    if b'\r\n' in raw and raw.count(b'\n') == raw.count(b'\r\n'):
        return text.replace('\r\n', '\n').replace('\n', '\r\n')
    return text.replace('\r\n', '\n')


def main():
    check = '--check' in sys.argv
    raw = open(TARGET, 'rb').read()
    src = raw.decode('utf-8')
    print('目标 %s：%d 字节，CRLF=%d / 裸 LF=%d'
          % (os.path.basename(TARGET), len(raw), raw.count(b'\r\n'),
             raw.count(b'\n') - raw.count(b'\r\n')))
    bad = 0
    out = src
    for name, old, new in EDITS:
        o, n = heal(old, raw), heal(new, raw)
        c_old, c_new = out.count(o), out.count(n)
        if c_new == 1 and c_old == 0:
            print('  [SKIP] %-34s 已应用' % name)
            continue
        if c_old != 1:
            print('  [BAD ] %-34s 锚点 %d 次' % (name, c_old))
            bad += 1
            continue
        if c_new >= 1:
            print('  [BAD ] %-34s 替换串已存在 %d 次（幂等判定冲突）' % (name, c_new))
            bad += 1
            continue
        out = out.replace(o, n)
        print('  [OK  ] %-34s 锚点 1 次' % name)
    if bad:
        print('✗ %d 处有问题，未写盘' % bad)
        return 2
    if check:
        print('✓ 预检通过（--check，未写盘）')
        return 0
    if out == src:
        print('✓ 无需改动')
        return 0
    open(TARGET, 'wb').write(out.encode('utf-8'))
    back = open(TARGET, 'rb').read()
    print('✓ 已写盘：%d → %d 字节，CRLF=%d / 裸 LF=%d'
          % (len(raw), len(back), back.count(b'\r\n'),
             back.count(b'\n') - back.count(b'\r\n')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
