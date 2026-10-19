# -*- coding: utf-8 -*-
"""补丁：harness 的搜索断言（2026-10-09 第二轮收尾）。

为什么必须补：
  上一轮的性能改写一度把配方页**主路径的搜索过滤**整个绕过（主路径不再套
  PD.SearchFilter），而共享 harness 的动态断言**只比条数**
      _n1 < _n0           （n0 = 300 行 → n1 = 31 行，全绿）
  —— 因为那一版里「条数按命中数截断、行却是分类前 N 条」，纯条数断言照样过。
  实测（_temp/_prof_search_audit.py）：显示 31 行里 **31 行全不含搜索词**。
  ⇒ 断言必须落到**行内容**上。

本补丁（三个文件位置，df_dungeon_check.py 与 mk_df_check.py 同步改）：
  A. 静态：`PD.RecipeList(math.min(realN, PD.ROW_CAP))` → 带 q 的新签名
           （不改这一处，性能改写后这条断言会静默恒假）。
  B. 静态：新增「搜索过滤发生在建 spec 之前」（PD.RawHit 两处共用 + EffKeyFilter）。
  C. 静态：量宽记忆化那条补 `if w ~= nil then return w end`（让「摘掉记忆化」能变红）。
  D. 动态：搜索断言补一条**内容**校验（每一行都真的命中才算过）。

用法：
    python _temp/patch_prof_search_harness.py --check
    python _temp/patch_prof_search_harness.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = [
    os.path.join(HERE, 'df_dungeon_check.py'),
    os.path.join(HERE, 'mk_df_check.py'),
]

# ── A. 静态断言：RecipeList 的新签名 ────────────────────────────────────
A_OLD = """       and 'PD.RecipeList(math.min(realN, PD.ROW_CAP))' in profui
"""
A_NEW = """       and 'PD.RecipeList(math.min(realN, PD.ROW_CAP), PD.searchQ)' in profui
"""

# ── B + C. 静态断言：新增搜索过滤位置 + 量宽记忆化补哨兵 ─────────────────
BC_OLD = """    ck('★ 量宽记忆化 + 物品请求按 id 去重（同一材料在几百条配方里重复量宽 / 重复请求）',
       'local _twMemo, _twN = {}, 0' in profui
       and 'if not id or seen[id] then return end' in profui)
"""
BC_NEW = """    ck('★ 量宽记忆化 + 物品请求按 id 去重（同一材料在几百条配方里重复量宽 / 重复请求）',
       'local _twMemo, _twN = {}, 0' in profui
       and 'if w ~= nil then return w end' in profui
       and 'if not id or seen[id] then return end' in profui)
    # ★★ 2026-10-09 第二轮收尾：上一轮的性能改写一度把**主路径的搜索过滤**整个绕过
    #   （主路径不再套 PD.SearchFilter），实机表现就是「搜索框形同虚设」。修法是
    #   把过滤挪进 PD.RecipeList 且**发生在建 spec 之前**（PD.RawHit 与 ScanRecipe
    #   共用同一口径，不许两边各写一套 —— 口径一漂，条数与行就对不上）。
    ck('★★ 搜索过滤在建 spec 之前（PD.RawHit 扫描/建表两处共用，不许绕过）',
       'function PD.RawHit' in profui
       and profui.count('PD.RawHit(r, q)') >= 2
       and profui.count('PD.EffKeyFilter(d)') >= 2)
"""

# ── D. 动态断言：补内容校验 ────────────────────────────────────────────
D_OLD = """              local _n0 = #(PD.specs or {})
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
"""
D_NEW = """              -- ★ 判据必须落到**行内容**上（2026-10-09 第二轮实锤）：只比条数不够 ——
              --   上一轮的性能改写让主路径「条数按命中数截断、行却是分类前 N 条」，
              --   纯条数断言照样全绿（实测 300 -> 31 全绿），搜索框其实形同虚设。
              --   PD.specs 里还混着抬头/间距/截断提示 ⇒ 只认真正的配方行（有 it）。
              local function _isRecipe(s)
                return s ~= nil and s.it ~= nil
                   and (s.kind == "row" or s.kind == nil)
              end
              local function _nRecipes(list)
                local n = 0
                for _, s in ipairs(list or {}) do
                  if _isRecipe(s) then n = n + 1 end
                end
                return n
              end
              local function _hitAndMiss(list, q)
                local n, bad = 0, 0
                for _, s in ipairs(list or {}) do
                  if _isRecipe(s) then
                    local cands = { tostring(_DG.ItemName(s.it[1]) or ""), s.sub or "" }
                    for _, m in ipairs(s._mats or {}) do
                      cands[#cands + 1] = tostring(_DG.ItemName(m[1]) or "")
                    end
                    local hit = false
                    for _, t in ipairs(cands) do
                      if t ~= "" and string.find(string.lower(t), q, 1, true) then
                        hit = true
                        break
                      end
                    end
                    if hit then n = n + 1 else bad = bad + 1 end
                  end
                end
                return n, bad
              end
              local _n0 = _nRecipes(PD.specs)
              PD.searchQ = "轻皮"
              PD.Render()
              local _n1, _bad = _hitAndMiss(PD.specs, "轻皮")
              _DG.ItemName = _oIN
              PD.searchQ = nil
              PD.Render()
              local _n2 = _nRecipes(PD.specs)
              ck("★★ 搜索词过滤列表（命中子集）且清空后全量还原",
                 _n0 > 0 and _n1 > 0 and _n1 < _n0 and _n2 == _n0,
                 tostring(_n0) .. " -> " .. tostring(_n1) .. " -> " .. tostring(_n2))
              ck("★★ 搜索后留下的每一行都真的命中（条数对不算数，行内容也得对）",
                 _n1 > 0 and _bad == 0,
                 tostring(_n1) .. " 行命中 / " .. tostring(_bad) .. " 行未命中")
"""

EDITS = [
    ('A 静态：RecipeList 新签名', A_OLD, A_NEW, None),
    ('B/C 静态：搜索过滤位置 + 量宽哨兵', BC_OLD, BC_NEW, None),
    ('D 动态：搜索内容校验', D_OLD, D_NEW, None),
]


def main():
    check = '--check' in sys.argv
    bad_total = 0
    for tgt in TARGETS:
        raw = open(tgt, 'rb').read()
        src = raw.decode('utf-8')
        print('目标 %s（%d 字节）' % (os.path.basename(tgt), len(raw)))
        bad = 0
        out = src
        for name, old, new, marker in EDITS:
            c_old, c_new = out.count(old), out.count(new)
            if marker and marker in out:
                print('  [SKIP] %-30s 已应用' % name)
                continue
            if not marker and c_new == 1 and c_old == 0:
                print('  [SKIP] %-30s 已应用' % name)
                continue
            if c_old != 1:
                print('  [BAD ] %-30s 锚点 %d 次' % (name, c_old))
                bad += 1
                continue
            if not marker and c_new >= 1:
                print('  [BAD ] %-30s 替换串已存在 %d 次' % (name, c_new))
                bad += 1
                continue
            out = out.replace(old, new)
            print('  [OK  ] %-30s 锚点 1 次' % name)
        if bad:
            bad_total += bad
            continue
        if out == src:
            print('  ✓ 无需改动')
            continue
        if check:
            print('  ✓ 预检通过（未写盘）')
            continue
        open(tgt, 'wb').write(out.encode('utf-8'))
        print('  ✓ 已写盘：%d → %d 字节' % (len(raw), len(out.encode('utf-8'))))
    if bad_total:
        print('✗ %d 处有问题' % bad_total)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
