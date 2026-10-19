# -*- coding: utf-8 -*-
"""补丁：修回被上一轮性能改动**绕过**的配方页搜索（2026-10-09 第二轮，收尾）。

背景（我自己引入的回归，本轮实锤）：
  上一轮为了让「点开配方页那一瞬间」不再卡，把 PD.RowsRecipe 的主路径改成了
      list = PD.RecipeList(math.min(realN, PD.ROW_CAP))
  —— 而 PD.RecipeList 内部**只按分类 key 过滤，不认搜索词**。旧写法是在它外面
  套一层 PD.SearchFilter(PD.RecipeList())。于是主路径的搜索过滤被整个跳过：
      实测（_temp/_prof_search_audit.py，leatherworking 511 条，Q = "轻皮"）
      显示 300 条里 11 条**不含该子串**；搜索前后条数一模一样（303 -> 303）。
  共享 harness 的动态搜索断言此刻被并行会话的团本页在途改动提前崩掉、跑不到，
  所以这条回归一直没人守。

本补丁（口径与观感完全不变，只把过滤挪到**建 spec 之前**）：
  1. 新增 PD.RawHit(r, q)      —— 原始行是否命中搜索词（不建 spec 的轻量判定），
                                 口径与 PD.SearchHit 逐字一致（名称→副行→材料名）。
  2. 新增 PD.EffKeyFilter(d)   —— 本页「有效分类过滤」（按 key 一条都没命中就退回
                                 不过滤）；与旧的 any 回退同口径，两处共用。
  3. PD.ScanRecipe 改用 1+2    —— 顺手把「key 命中 0 条 ⇒ 退回不过滤」的判据从
                                 「key+搜索都 miss」修正回与 RecipeList 一致的
                                 「key miss」（否则搜索无结果时抬头条数会虚高）。
  4. PD.RecipeList(limit, q)   —— 主路径先按 1 过滤再建 spec。
  5. PD.RowsRecipe             —— 主路径把 PD.searchQ 传进去。

  注意：过滤依然发生在建 spec 之前 ⇒ 上一轮的性能收益（整帧 28.5ms → 4.7ms）不受
  影响；命中子集的建 spec 次数只会**更少**。

用法：
    python _temp/patch_prof_perf4.py --check     # 只体检锚点，不写
    python _temp/patch_prof_perf4.py             # 落盘
"""
import os
import sys

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      os.pardir, 'Core', 'ProfessionUI.lua')

# ── 1. 新增 PD.RawHit / PD.EffKeyFilter（插在 ScanRecipe 的说明块之前） ──
E1_OLD = '''-- ★ 配方页「轻量全量扫描」（2026-10-09 第二轮：点开配方页那一瞬间仍卡）：
'''
E1_NEW = '''-- ★ 原始行命中搜索词吗（2026-10-09 第二轮）：**不建 spec** 的轻量判定。
--   配方页主列表必须按搜索词过滤，但过滤得发生在**建 spec 之前** —— 否则
--   「点开那一瞬间」又要为全量 511 条建一遍 spec（已量过 = 整帧 82% 的耗时）。
--   口径与 PD.SearchHit 逐字一致（名称 → 副行 → 材料名；q 已小写化）。
function PD.RawHit(r, q)
    if not q or q == "" then return true end
    local nm = DG.ItemName(r[2])
    if nm and nm ~= "" and string.find(string.lower(tostring(nm)), q, 1, true) then
        return true
    end
    local sub = tostring(r[5] or "")
    if sub ~= "" and string.find(string.lower(sub), q, 1, true) then return true end
    for _, m in ipairs(r[12] or {}) do
        local mn = DG.ItemName(m[1])
        if mn and mn ~= "" and string.find(string.lower(tostring(mn)), q, 1, true) then
            return true
        end
    end
    return false
end

-- ★ 本页的「有效分类过滤」（2026-10-09 第二轮）：按 PD.toolKey 过滤**一条都没命中**
--   时退回不过滤 —— 与旧 PD.RecipeList 的 any 回退同口径。返回值即要用的 key
--   （nil = 不过滤）。PD.ScanRecipe 与 PD.RecipeList 共用，两边口径不许各写一套。
function PD.EffKeyFilter(d)
    local key = PD.toolKey
    if not key or key == "all" then return nil end
    for _, r in ipairs(d.rows or {}) do
        if r[4] == key then return key end
    end
    return nil
end

-- ★ 配方页「轻量全量扫描」（2026-10-09 第二轮：点开配方页那一瞬间仍卡）：
'''

# ── 2. PD.ScanRecipe：改用 RawHit + EffKeyFilter ───────────────────────
E2_OLD = '''    local q = PD.searchQ
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
'''
E2_NEW = '''    local q = (PD.searchQ and PD.searchQ ~= "") and PD.searchQ or nil
    local fk = PD.EffKeyFilter(d)

    local n, maxW = 0, 0
    for _, r in ipairs(d.rows or {}) do
        if (not fk) or r[4] == fk then
            if PD.RawHit(r, q) then
                n = n + 1
                -- 与 PD.FitRecipeCols 的自扫逐字同口径：名称可为空（名字还没到货）
                -- 时也照样把「新角标 + 副行」计入最宽值。
                local nm = DG.ItemName(r[2])
                local w = (nm and nm ~= "" and PD.TextW(nm, 13)) or 0
                if r[11] then w = w + PD.RECIPE_BADGE_W end
                local sw = PD.TextW(tostring(r[5] or ""), 11)
                if sw > w then w = sw end
                if w > maxW then maxW = w end
            end
        end
    end
    return n, maxW
'''

# ── 3. PD.RecipeList：签名加 q ─────────────────────────────────────────
E3_OLD = '''function PD.RecipeList(limit)
    local d = R[PD.cur]
'''
E3_NEW = '''function PD.RecipeList(limit, q)
    local d = R[PD.cur]
'''

# ── 4. PD.RecipeList：主路径先过滤再建 spec ────────────────────────────
E4_OLD = '''    local any = false
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
E4_NEW = '''    -- ★ 搜索必须在**建 spec 之前**生效（2026-10-09 第二轮修正）：先按 PD.RawHit 过
    --   原始行，命中的才建 spec —— 不然「点开那一瞬间」还是要为全量 511 条建一遍。
    --   口径与 PD.ScanRecipe 完全共用（PD.EffKeyFilter + PD.RawHit），不许各写一套。
    --   ★ 旧的 `any` 回退（key 一条都没命中 ⇒ 不过滤）已折进 PD.EffKeyFilter。
    local fk = PD.EffKeyFilter(d)
    for _, r in ipairs(d.rows or {}) do
        if (not fk) or r[4] == fk then
            if PD.RawHit(r, q) then
                out[#out + 1] = PD.RecipeSpec(r)
                if #out >= cap then break end
            end
        end
    end
    return out
end
'''

# ── 5. PD.RowsRecipe：把搜索词传进去 ───────────────────────────────────
E5_OLD = '''        list = PD.RecipeList(math.min(realN, PD.ROW_CAP))
'''
E5_NEW = '''        list = PD.RecipeList(math.min(realN, PD.ROW_CAP), PD.searchQ)
'''

# ── 6. 文件头纪律说明补一句 ────────────────────────────────────────────
E6_OLD = '''--     改动前后观感/口径完全一致，只是常数小了（详见 PD.ScanRecipe / PD.RecipeSpec）。
'''
E6_NEW = '''--     改动前后观感/口径完全一致，只是常数小了（详见 PD.ScanRecipe / PD.RecipeSpec）。
--   · ★★ 同轮修正：那次改写一度把**搜索过滤**绕过了（主路径不再套 PD.SearchFilter），
--     现已改成 PD.RecipeList(limit, q) + PD.RawHit：过滤仍在**建 spec 之前**，
--     命中子集才建 —— 性能收益不变，搜索口径与 PD.SearchHit 逐字一致。
'''

EDITS = [
    # (名字, 锚点, 替换, 哨兵：出现即说明已应用)
    # ★ 1/6 是「在锚点前插入」，替换串里**含**锚点原文 ⇒ 单靠 c_old/c_new 判不出来，
    #   必须给一个只在替换串里出现的哨兵。
    ('1 新增 PD.RawHit / PD.EffKeyFilter', E1_OLD, E1_NEW,
     'function PD.RawHit(r, q)'),
    ('2 PD.ScanRecipe 改用 RawHit', E2_OLD, E2_NEW, None),
    ('3 PD.RecipeList 签名加 q', E3_OLD, E3_NEW, None),
    ('4 PD.RecipeList 主路径先过滤', E4_OLD, E4_NEW, None),
    ('5 PD.RowsRecipe 传搜索词', E5_OLD, E5_NEW, None),
    ('6 文件头纪律说明', E6_OLD, E6_NEW,
     '那次改写一度把**搜索过滤**绕过'),
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
    for name, old, new, marker in EDITS:
        o, n = heal(old, raw), heal(new, raw)
        c_old, c_new = out.count(o), out.count(n)
        if marker:
            if heal(marker, raw) in out:
                print('  [SKIP] %-34s 已应用' % name)
                continue
        elif c_new == 1 and c_old == 0:
            print('  [SKIP] %-34s 已应用' % name)
            continue
        if c_old != 1:
            print('  [BAD ] %-34s 锚点 %d 次' % (name, c_old))
            bad += 1
            continue
        if not marker and c_new >= 1:
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
