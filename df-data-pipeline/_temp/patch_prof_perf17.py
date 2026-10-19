# -*- coding: utf-8 -*-
"""第十一刀（rev17）：物品名/图标记忆表「正负分离 + 正向跨渲染持久」+ 空闲预热。

14:40 实机（第十刀生效后）—— 第十刀的账**结清了**：
  · `数据 20.8 → 12.4ms`（`列宽材料 9.8 → 1.2`、`材料串 300次/9.1 → 29次/0.8`）
  · 整页 `点页签 recipe 32.0 → 24.2ms`；分帧段相应变大（那 8ms 摊进几十帧）。
  · 剩下的 12.4 被**一元分解**得很干净：
        数据 12.4 = 扫描 7.3（ScanRecipe） + 建spec 3.7（RecipeList） + 列宽材料 1.2
    而 `取名 1055次/5.7ms · 取名(引擎) 428次/4.7ms` ⇒ **扫描那一半几乎就是「向引擎
    要 300 个物品名」**（数据文件只存 ID，名字只能问客户端；见 Data_ProfRecipes.lua 头注）。
  · 关键佐证：这一页 `发包 0 次`（计数为 0 不打印）⇒ **名字本来就已经在客户端缓存里**，
    428 次 GetItemInfo 全是**白问**。

机制（真凶：`PD.ResetItemNameMemo` 每次 Render 整表清空）：
  · `PD.ItemName` 是「事务内记忆化」——`Render` 开头 `PD.ResetItemNameMemo()` 把
    名字表 + 图标表**整个清掉**。一局里这一页的名字至少被重问 5 遍：
    到货重扫 `PD.SweepNames`（0.5/1.5/4/9s 各一次重渲）+ 每次切走再切回来。
  · 但**物品名一旦到货就不会再变**（原名表注释自己写着「同一个 id 的名字不可能变」）
    ⇒ 正向结果完全该跨渲染留着；只有「还没到货」那半边才需要下次渲染重问。

本补丁：
  P0a/P0b      Core/ProfessionUI.lua —— 两处注释跟着新语义改（原注释写的是「整表清空」）。
  P1           `_nmMemo/_icMemo` 两表拆成**正 / 负**四表；`PD.ResetItemNameMemo(hard)`
               只清负向（`hard` 走全清，给测试造态用）。
  P2/P3        `PD.ItemName` 改成「正向命中直接返回 / 负向命中直接占位 / 都没命中才问引擎」。
  P4           `PD.ItemIcon` 同构（`FALLBACK_ICON` 算「还没到货」⇒ 进负向表）。
  P5           **空闲预热** `PD.WarmNames` / `PD.WarmId`：在分帧器空闲帧把当前专业的
               物品名先喂进持久记忆表 —— 用户点开配方页时那些名字已经是命中。
  P6           `PD.Render` 收尾调一次 `PD.WarmNames()`。
  C1/C2        双 harness 各加 2 条断言。
  D1/D2/D3     变异 `MUT_PROF_NM_MEMO_RESET_ALL` / `MUT_PROF_WARM_GONE` + 登记 + DEFAULT_WANT。
  E1a/E1b/E2   探针离线冒烟：① 造态前把**正向**表也硬清（不然造态被持久表吃掉、断言假绿）；
               ② 行为自检：正向跨 Render 存活（清表后引擎调用 = 0）、负向每次重问、
               空闲预热真的喂进表并发装载请求。

★ 插入型改动 ⇒ 幂等靠**哨兵串**判，不靠 count(old)。
★ 变异锚点必须**纯 ASCII**（Python 3 的 b'...' 不许含非 ASCII 字面量）。
"""

import sys

PROF = 'Core/ProfessionUI.lua'
CHECK = '_temp/df_dungeon_check.py'
MK = '_temp/mk_df_check.py'
MUT = '_temp/df_mut_check.py'
WANT = '_temp/df_check_new_muts.py'
SMOKE = '_temp/_prof_perf_print_check.py'

# ────────────────────────── Core/ProfessionUI.lua ──────────────────────────

# P0a：物品名注释块（原话说的是「Render 开头清空」）
OLD_C0 = ("--   一次 Render 是同步执行、中间没有任何异步插入 ⇒ 同一个 id 的名字不可能变，\n"
          "--   按 id 记忆化绝对安全。Render 开头清空（PD.ResetItemNameMemo）；物品到货后的\n"
          "--   重扫（PD.SweepNames → PD.Render）自然拿到新名字。\n")

NEW_C0 = ("--   一次 Render 是同步执行、中间没有任何异步插入 ⇒ 同一个 id 的名字不可能变，\n"
          "--   按 id 记忆化绝对安全。\n"
          "--   ★★ 第十一刀（rev17）：记忆表再改成**正 / 负分离 + 正向跨渲染持久** ——\n"
          "--   实机量到「一页 取名 1055 次 / 取名(引擎) 428 次 / 4.7ms」，而这一页的\n"
          "--   名字在一局里至少被重问 5 遍（到货重扫 0.5/1.5/4/9s 各重渲一次 + 每次\n"
          "--   切走再切回来），且那一页 `发包 0 次` ⇒ **名字本来就在客户端缓存里**，\n"
          "--   428 次 GetItemInfo 全是白问。名字一旦到货就不会再变 ⇒ 正向结果完全该\n"
          "--   跨渲染留着；只有「还没到货」那半边才需要下次渲染重问。\n"
          "--   到货后的重扫（PD.SweepNames → PD.Render）靠清**负向**表自然拿到新名字。\n")

# P0b：图标注释块（原话说的是「两表一起清」）
OLD_C1 = ("--   同一个 id 在一次渲染里图标不可能变 ⇒ 与 PD.ItemName 共用同一次清空时机\n"
          "--   （PD.ResetItemNameMemo 两表一起清），到货重扫自然拿到新图标。\n")

NEW_C1 = ("--   同一个 id 在一次渲染里图标不可能变 ⇒ 与 PD.ItemName 一样**正 / 负分离**：\n"
          "--   真图标（正向表）跨渲染持久；FALLBACK_ICON 算「还没到货」进负向表，\n"
          "--   每次 Render 开头清（PD.ResetItemNameMemo(hard) 可连正向一起清），\n"
          "--   到货重扫自然拿到新图标。\n")

# P1：两表拆四表 + ResetItemNameMemo 只清负向
OLD_P1 = ("local _nmMemo, _nmN = {}, 0\n"
          "local _icMemo, _icN = {}, 0\n"
          "function PD.ResetItemNameMemo()\n"
          "    _nmMemo, _nmN = {}, 0\n"
          "    _icMemo, _icN = {}, 0\n"
          "end\n")

NEW_P1 = ("-- ★★ 第十一刀（rev17）：正 / 负**分离** + 正向**跨渲染持久**。\n"
          "--   · _nmPos / _icPos（正向：名字 / 图标**已到货**）—— **不随 Render 清**，\n"
          "--     只在满 PD_MEMO_POS_CAP 时整表清（代价只是重问一遍）。\n"
          "--   · _nmNeg / _icNeg（负向：**还没到货**）—— 每次 Render 开头清\n"
          "--     （PD.ResetItemNameMemo），保证「到货重扫」永远能把占位刷成真名。\n"
          "--   ★ hard = true 连正向一起清（只给离线冒烟的「造态」用：桩的假名会先落进\n"
          "--     正向表，不硬清就看不出「未到货」那条路，断言会假绿）。\n"
          "local PD_MEMO_POS_CAP = 32768\n"
          "local _nmPos, _nmPosN = {}, 0\n"
          "local _nmNeg, _nmN = {}, 0\n"
          "local _icPos, _icPosN = {}, 0\n"
          "local _icNeg, _icN = {}, 0\n"
          "function PD.ResetItemNameMemo(hard)\n"
          "    _nmNeg, _nmN = {}, 0\n"
          "    _icNeg, _icN = {}, 0\n"
          "    if hard then _nmPos, _nmPosN, _icPos, _icPosN = {}, 0, {}, 0 end\n"
          "end\n")

# P2：ItemName 头部（正向命中 / 负向命中）
OLD_P2 = ("function PD.ItemName(id)\n"
          "    if id == nil then return L[\"暂时没有客户端数据\"], false end\n"
          "    local c = _nmMemo[id]\n"
          "    if c then return c[1], c[2] end\n")

NEW_P2 = ("function PD.ItemName(id)\n"
          "    if id == nil then return L[\"暂时没有客户端数据\"], false end\n"
          "    local hit = _nmPos[id]\n"
          "    if hit ~= nil then return hit, true end\n"
          "    if _nmNeg[id] then return L[\"暂时没有客户端数据\"], false end\n")

# P3：ItemName 尾部（到货进正向 / 没到货进负向）
OLD_P3 = ("    local nm, got = DG.ItemName(id)\n"
          "    if _nmN >= 8192 then _nmMemo, _nmN = {}, 0 end\n"
          "    _nmMemo[id] = { nm, got }\n"
          "    _nmN = _nmN + 1\n"
          "    return nm, got\n"
          "end\n")

NEW_P3 = ("    local nm, got = DG.ItemName(id)\n"
          "    if got then\n"
          "        if _nmPosN >= PD_MEMO_POS_CAP then _nmPos, _nmPosN = {}, 0 end\n"
          "        _nmPos[id], _nmPosN = nm, _nmPosN + 1\n"
          "        return nm, true\n"
          "    end\n"
          "    if _nmN >= 8192 then _nmNeg, _nmN = {}, 0 end\n"
          "    _nmNeg[id], _nmN = true, _nmN + 1\n"
          "    return nm, false\n"
          "end\n")

# P4：ItemIcon 同构
OLD_P4 = ("function PD.ItemIcon(id)\n"
          "    if id == nil then return FALLBACK_ICON end\n"
          "    local c = _icMemo[id]\n"
          "    if c ~= nil then return c end\n"
          "    local tex = DG.ItemIcon(id)\n"
          "    if _icN >= 8192 then _icMemo, _icN = {}, 0 end\n"
          "    _icMemo[id] = tex\n"
          "    _icN = _icN + 1\n"
          "    return tex\n"
          "end\n")

NEW_P4 = ("function PD.ItemIcon(id)\n"
          "    if id == nil then return FALLBACK_ICON end\n"
          "    local hit = _icPos[id]\n"
          "    if hit ~= nil then return hit end\n"
          "    if _icNeg[id] then return FALLBACK_ICON end\n"
          "    local tex = DG.ItemIcon(id)\n"
          "    -- ★ FALLBACK_ICON = 「还没到货」⇒ 进负向表（下次 Render 再问）；\n"
          "    --   真图标进正向表（跨渲染持久）。\n"
          "    if tex ~= FALLBACK_ICON then\n"
          "        if _icPosN >= PD_MEMO_POS_CAP then _icPos, _icPosN = {}, 0 end\n"
          "        _icPos[id], _icPosN = tex, _icPosN + 1\n"
          "        return tex\n"
          "    end\n"
          "    if _icN >= 8192 then _icNeg, _icN = {}, 0 end\n"
          "    _icNeg[id], _icN = true, _icN + 1\n"
          "    return tex\n"
          "end\n")

# P5：空闲预热（插在 PD.RequestRows 定义之前）
OLD_P5 = "function PD.RequestRows(rows)\n"

NEW_P5 = (
    "-- ★★ 第十一刀（rev17）：**空闲预热** —— 把「点开配方页那一帧本该付的取名钱」\n"
    "--   提前到空闲帧付掉。\n"
    "--   一页 300 条配方，PD.ScanRecipe 必须为**列宽**取全部 300 个物品名（数据文件\n"
    "--   只存 ID，名字只能问客户端），实机 428 次 GetItemInfo / 4.7ms 全压在「点开\n"
    "--   那一瞬间」；而名字一旦到货就不会再变（记忆表已改成跨渲染持久）⇒ 完全可以\n"
    "--   在空闲帧先喂一遍：用户点开配方页时 PD.ItemName 全是命中，那一帧的引擎调用归零。\n"
    "--   ★ 只在分帧器空闲（not DG.stepping）时才喂 —— 建行永远优先；每帧只一小口。\n"
    "--   ★ 跟当前专业走（PD.cur 变了就换目标）；覆盖范围与 PD.RequestRows 一致\n"
    "--     （min(#d.rows, ROW_CAP) 行）⇒ 只是把本该付的钱挪到前面，不产生额外请求。\n"
    "--   ★ pcall 包住 —— 预热永不许影响正事；出错就静静停下。\n"
    "local _warmTok = 0\n"
    "local PD_WARM_PER_FRAME = 96\n"
    "function PD.WarmId(id)\n"
    "    if not id then return end\n"
    "    local _, got = PD.ItemName(id)\n"
    "    if got then return end\n"
    "    if C_Item and C_Item.RequestLoadItemDataByID then\n"
    "        pcall(C_Item.RequestLoadItemDataByID, id)\n"
    "    end\n"
    "    local gi = GetItemInfo or (C_Item and C_Item.GetItemInfo)\n"
    "    if type(gi) == \"function\" then pcall(gi, id) end\n"
    "end\n"
    "function PD.WarmNames()\n"
    "    local d = R[PD.cur]\n"
    "    local all = d and d.rows\n"
    "    if type(all) ~= \"table\" or #all == 0 then return end\n"
    "    if not (C_Timer and C_Timer.After) then return end\n"
    "    _warmTok = _warmTok + 1\n"
    "    local tok = _warmTok\n"
    "    local i, n = 0, math.min(#all, PD.ROW_CAP)\n"
    "    local function feed()\n"
    "        if tok ~= _warmTok then return end\n"
    "        if DG.stepping then C_Timer.After(0, feed) return end\n"
    "        local ok = pcall(function()\n"
    "            local budget = PD_WARM_PER_FRAME\n"
    "            while i < n and budget > 0 do\n"
    "                i = i + 1\n"
    "                local r = all[i]\n"
    "                if r then\n"
    "                    PD.WarmId(r[2])\n"
    "                    local ms = r[12]\n"
    "                    if ms then\n"
    "                        for k = 1, #ms do PD.WarmId(ms[k] and ms[k][1]) end\n"
    "                    end\n"
    "                end\n"
    "                budget = budget - 1\n"
    "            end\n"
    "        end)\n"
    "        if not ok then return end\n"
    "        if i < n then C_Timer.After(0, feed) end\n"
    "    end\n"
    "    C_Timer.After(0, feed)\n"
    "end\n"
    "\n"
    "function PD.RequestRows(rows)\n")

# P6：Render 收尾调一次预热
OLD_P6 = "    PD.RequestRows(rows)\nend\n"
NEW_P6 = ("    PD.RequestRows(rows)\n"
          "    PD.WarmNames()\n"
          "    -- ★★ 第十一刀（rev17）：收尾挂一次**空闲预热** —— 在当前专业上把物品名\n"
          "    --   先喂进持久记忆表。用户切到 overview / leveling 的那几百毫秒里，\n"
          "    --   配方页那 300 个名字就已经备好了 ⇒ 点开配方页那一帧不再向引擎要名字。\n"
          "end\n")

# ────────────────────────────── 双 harness 断言 ──────────────────────────────

ANCHOR_CK = ("    ck('★★ 配方页材料串按需算（首屏现算 / 其余挂标，绑前用同一个 PD.MAT_W 补算）',\n"
             "       'function PD.FinishSpecMats(s)' in profui\n"
             "       and 'local keep = PD.SyncRows()' in profui\n"
             "       and 's._matsPending = true' in profui\n"
             "       and 'if spec._matsPending then PD.FinishSpecMats(spec) end' in profui)\n")

NEW_CK = (ANCHOR_CK +
          "    # ★★ 第十一刀（rev17）：物品名 / 图标记忆表**正负分离 + 正向跨渲染持久**。\n"
          "    #   原来每次 Render 开头把两表整个清空 ⇒ 到货重扫（0.5/1.5/4/9s）与任何一次\n"
          "    #   重渲都要**重新向引擎要一遍全部物品名**（实机一页 428 次 GetItemInfo / 4.7ms，\n"
          "    #   而那一页 `发包 0 次` ⇒ 名字本来就在客户端缓存里，全是白问）。名字一旦到货\n"
          "    #   就不会再变 ⇒ 正向（_nmPos/_icPos）必须跨渲染留着，Render 只清负向。\n"
          "    ck('★★ 物品名/图标记忆表正负分离：正向跨渲染持久，Render 只清「未到货」那半边',\n"
          "       'local _nmPos, _nmPosN = {}, 0' in profui\n"
          "       and 'local _nmNeg, _nmN = {}, 0' in profui\n"
          "       and 'local _icPos, _icPosN = {}, 0' in profui\n"
          "       and '_nmPos[id], _nmPosN = nm, _nmPosN + 1' in profui\n"
          "       and '_nmNeg[id], _nmN = true, _nmN + 1' in profui\n"
          "       and ('function PD.ResetItemNameMemo(hard)\\n'\n"
          "            '    _nmNeg, _nmN = {}, 0\\n'\n"
          "            '    _icNeg, _icN = {}, 0\\n' in profui))\n"
          "    # ★★ 第十一刀（rev17）：空闲预热 —— Render 收尾必须在空闲帧把当前专业的\n"
          "    #   物品名先喂进持久记忆表（用户切到其它页签的那几百毫秒就是预热窗口）。\n"
          "    ck('★★ 空闲预热：Render 收尾在空闲帧把当前专业的物品名喂进持久记忆表',\n"
          "       'function PD.WarmNames()' in profui\n"
          "       and 'function PD.WarmId(id)' in profui\n"
          "       and '    PD.RequestRows(rows)\\n    PD.WarmNames()' in profui\n"
          "       and 'if DG.stepping then C_Timer.After(0, feed) return end' in profui)\n")

# ────────────────────────────── 变异 ──────────────────────────────

MUT_DEF_ANCHOR = "# ★★ 物品名记忆表（2026-10-09 第五轮）：Render 开头不清"

MUT_DEF = (
    "# ★★ 第十一刀（rev17）：记忆表「正负分离」被破坏 —— 清表时把**正向**那半边\n"
    "#   也一起清了 ⇒ 每一帧渲染又要向引擎重问全部物品名（实机一页 428 次）。\n"
    "MUT_PROF_NM_MEMO_RESET_ALL = ('Core/ProfessionUI.lua', (\n"
    "    b'    _nmNeg, _nmN = {}, 0\\n'\n"
    "    b'    _icNeg, _icN = {}, 0\\n',\n"
    "    b'    _nmNeg, _nmPos, _nmN, _nmPosN = {}, {}, 0, 0  -- MUT: positive memo cleared too\\n'))\n"
    "\n"
    "# ★★ 第十一刀（rev17）：空闲预热被摘 ⇒ 「点开配方页」那一帧又得现向引擎要名字。\n"
    "MUT_PROF_WARM_GONE = ('Core/ProfessionUI.lua', (\n"
    "    b'    PD.RequestRows(rows)\\n    PD.WarmNames()\\n',\n"
    "    b'    PD.RequestRows(rows)\\n    -- MUT: idle prewarm gone\\n'))\n"
    "\n")

MUT_REG_ANCHOR = ("    ('专业页：材料串退回「全部行现算」（点开那一帧又背 ~8ms）',"
                  " MUT_PROF_MATS_DEFER_GONE),\n")
MUT_REG_NEW = (MUT_REG_ANCHOR +
               "    ('专业页：物品名记忆表连「已到货」也清（每帧渲染又重问一遍全部名字）',"
               " MUT_PROF_NM_MEMO_RESET_ALL),\n"
               "    ('专业页：空闲预热被摘（点开配方页那一帧又得现向引擎要 300 个名字）',"
               " MUT_PROF_WARM_GONE),\n")

WANT_ANCHOR = "    '专业页：材料串退回「全部行现算」（点开那一帧又背 ~8ms）',\n"
WANT_NEW = (WANT_ANCHOR +
            "    '专业页：物品名记忆表连「已到货」也清（每帧渲染又重问一遍全部名字）',\n"
            "    '专业页：空闲预热被摘（点开配方页那一帧又得现向引擎要 300 个名字）',\n")

# ────────────────────── 既有断言：跟着新机制更新 ──────────────────────
# ★ 这两条断言是第五 / 第六轮给**旧的两表实现**写的（钉住 `_nmMemo`/`_icMemo`
#   「每次渲染整表清」）。机制改成正负分离后它们的**意图**仍然成立、只是字面过时：
#     · 名字：不清就会把「还没到货」的占位钉死一整局 ⇒ 现在钉**负向表**每次清；
#     · 图标：记忆表必须跟着一起清 ⇒ 现在钉 `_icNeg`。
#   ★ 断言**名字保持不变**（变异登记 `MUT_PROF_NO_NM_RESET` / `MUT_PROF_NO_ICON_MEMO`
#     的守护点就是这两条，改名会让登记对不上）。

F1_OLD = ("    ck('★★ 物品名记忆表每次渲染清空（不清就会把「名字还没到货」的占位钉死一整局）',\n"
          "       'local _nmMemo, _nmN = {}, 0' in profui\n"
          "       and 'function PD.ResetItemNameMemo()' in profui\n"
          "       and 'function PD.ItemName(id)' in profui\n"
          "       and 'PD.ResetItemNameMemo()' in _prender)\n")

F1_NEW = ("    # ★ 第十一刀（rev17）：机制改成「正负分离」—— 这条断言跟着换字面（守护点不变：\n"
          "    #   「还没到货」那半边必须每次渲染清，否则到货重扫永远刷不回来）。\n"
          "    ck('★★ 物品名记忆表每次渲染清空（不清就会把「名字还没到货」的占位钉死一整局）',\n"
          "       'local _nmNeg, _nmN = {}, 0' in profui\n"
          "       and ('function PD.ResetItemNameMemo(hard)\\n'\n"
          "            '    _nmNeg, _nmN = {}, 0\\n'\n"
          "            '    _icNeg, _icN = {}, 0\\n' in profui)\n"
          "       and 'function PD.ItemName(id)' in profui\n"
          "       and 'PD.ResetItemNameMemo()' in _prender)\n")

F2_OLD = ("    ck('★★ 材料图标查询走记忆化（一页上千次同源引擎调用；MatIconTex 不许绕过记忆表）',\n"
          "       'function PD.ItemIcon(id)' in profui\n"
          "       and 'local _icMemo, _icN = {}, 0' in profui\n"
          "       and '    _icMemo, _icN = {}, 0' in profui\n"
          "       and 'local ic = PD.ItemIcon(id)' in profui\n"
          "       and 'local ic = DG.ItemIcon(id)' not in profui)\n")

F2_NEW = ("    ck('★★ 材料图标查询走记忆化（一页上千次同源引擎调用；MatIconTex 不许绕过记忆表）',\n"
          "       'function PD.ItemIcon(id)' in profui\n"
          "       and 'local _icNeg, _icN = {}, 0' in profui\n"
          "       and '    _icNeg, _icN = {}, 0' in profui\n"
          "       and 'local ic = PD.ItemIcon(id)' in profui\n"
          "       and 'local ic = DG.ItemIcon(id)' not in profui)\n")

# ────────────────────── 探针离线冒烟（Lua 段 + 断言） ──────────────────────

# E1a：造态必须连**正向**表一起硬清（否则前面几帧用桩的假名已进正向表，
#      持久化之后造态看到的仍是「已到货」，那条路永远测不到、断言假绿）。
OLD_SMOKE_ZAOTAI = ("  PD.searchQ = nil\n"
                    "  guard()\n"
                    "  PD.Render()\n")

NEW_SMOKE_ZAOTAI = ("  -- ★★ 第十一刀（rev17）：记忆表已「正向跨渲染持久」⇒ 造态还必须把**正向**\n"
                    "  --   那半边也硬清一次。否则前面几帧用桩的假名已经落进正向表，这里永远\n"
                    "  --   看不到「未到货」那条路（rlN / notReady 断言会假绿）。\n"
                    "  PD.ResetItemNameMemo(true)\n"
                    "  PD.searchQ = nil\n"
                    "  guard()\n"
                    "  PD.Render()\n")

# E1b：行为自检段（插在收尾 `print = realPrint` 之前）
OLD_SMOKE_TAIL = ("  print = realPrint\n"
                  "  local nr = (PD.notReady and #PD.notReady) or 0\n")

NEW_SMOKE_TAIL = ("  -- ★★ 第十一刀（rev17）：记忆表「正负分离 + 正向跨渲染持久」的行为自检。\n"
                  "  --   ① 正向：取一次真名 → PD.ResetItemNameMemo()（= 一次新 Render 的开头）\n"
                  "  --      → 再取，引擎调用必须是 **0**（原来整表清 ⇒ 又调一次）。\n"
                  "  --   ② 负向：「名字还没到货」必须**不**跨 Render —— 每次都要再问一次，\n"
                  "  --      否则到货重扫永远刷不出名字（那是原来那张表唯一的存在理由）。\n"
                  "  --   ③ 空闲预热：PD.WarmNames() 要真的把当前专业的物品名喂进表\n"
                  "  --      （造态里名字一律未到货 ⇒ 必然发出装载请求）。\n"
                  "  do\n"
                  "    local prevGI = GetItemInfo\n"
                  "    local engN = 0\n"
                  "    GetItemInfo = function(id)\n"
                  "      engN = engN + 1\n"
                  "      return \"测试物品\" .. tostring(id), \"item:\" .. tostring(id)\n"
                  "    end\n"
                  "    local e0 = engN\n"
                  "    PD.ItemName(1900001)\n"
                  "    local e1 = engN - e0\n"
                  "    PD.ResetItemNameMemo()\n"
                  "    PD.ItemName(1900001)\n"
                  "    local e2 = engN - e0 - e1\n"
                  "    logs[#logs + 1] = \"@@MEMO\\t\" .. e1 .. \"\\t\" .. e2\n"
                  "\n"
                  "    local negN = 0\n"
                  "    GetItemInfo = function() negN = negN + 1 return nil end\n"
                  "    PD.ResetItemNameMemo()\n"
                  "    PD.ItemName(1900002)\n"
                  "    local n1 = negN\n"
                  "    PD.ResetItemNameMemo()\n"
                  "    PD.ItemName(1900002)\n"
                  "    local n2 = negN - n1\n"
                  "    logs[#logs + 1] = \"@@MEMO2\\t\" .. n1 .. \"\\t\" .. n2\n"
                  "\n"
                  "    WG_REQ = 0\n"
                  "    local prevRL = C_Item.RequestLoadItemDataByID\n"
                  "    C_Item.RequestLoadItemDataByID = function(...)\n"
                  "      WG_REQ = WG_REQ + 1\n"
                  "      if prevRL then return prevRL(...) end\n"
                  "    end\n"
                  "    PD.sweeping = true\n"
                  "    guard()\n"
                  "    local w0 = WG_REQ\n"
                  "    PD.WarmNames()\n"
                  "    local wp = 0\n"
                  "    while #PUMPS > 0 and wp < 40000 do\n"
                  "      local fn = table.remove(PUMPS, 1)\n"
                  "      wp = wp + 1\n"
                  "      pcall(fn)\n"
                  "    end\n"
                  "    C_Item.RequestLoadItemDataByID = prevRL\n"
                  "    GetItemInfo = prevGI\n"
                  "    logs[#logs + 1] = \"@@WARM\\t\" .. (WG_REQ - w0) .. \"\\t\" .. wp\n"
                  "\n"
                  "    -- 还原造态：最后一帧仍要「名字未到货」⇒ PD.notReady 非空（既有断言要用）。\n"
                  "    PD.ResetItemNameMemo(true)\n"
                  "    guard()\n"
                  "    PD.Render()\n"
                  "  end\n"
                  "\n"
                  "  print = realPrint\n"
                  "  local nr = (PD.notReady and #PD.notReady) or 0\n")

OLD_SMOKE_CK = "    # ★★ /dfprofperf rep：连渲同一页 3 次（冷 / 热对照）\n"

NEW_SMOKE_CK = ("    # ★★ 第十一刀（rev17）：记忆表正负分离 —— 正向跨 Render 存活（第 2 次取\n"
                "    #   同名 = 0 次引擎调用）；负向每次重问（否则到货重扫刷不出名字）；\n"
                "    #   空闲预热真的把当前专业的物品名喂进表并发装载请求。\n"
                "    p_memo = [int(x) for x in (next((l for l in lines\n"
                "                                     if l.startswith('@@MEMO\\t')), '@@MEMO\\t-1\\t-1')\n"
                "                               .split('\\t')[1:])]\n"
                "    p_neg = [int(x) for x in (next((l for l in lines\n"
                "                                     if l.startswith('@@MEMO2\\t')), '@@MEMO2\\t-1\\t-1')\n"
                "                               .split('\\t')[1:])]\n"
                "    p_warm = [int(x) for x in (next((l for l in lines\n"
                "                                      if l.startswith('@@WARM\\t')), '@@WARM\\t-1\\t-1')\n"
                "                                .split('\\t')[1:])]\n"
                "    ck('★★ 物品名正向记忆跨 Render 存活（清负向表后不再问引擎）',\n"
                "       p_memo == [1, 0], '首次 %s 次 · 清表后 %s 次' % tuple(p_memo))\n"
                "    ck('★★ 「未到货」不跨 Render（每次都要重问，否则到货重扫永远刷不出名字）',\n"
                "       p_neg == [1, 1], '首次 %s 次 · 清表后 %s 次' % tuple(p_neg))\n"
                "    ck('★★ 空闲预热把当前专业的物品名喂进持久记忆表（并发装载请求）',\n"
                "       p_warm[0] > 0 if p_warm else False,\n"
                "       '装载请求 %s 次 · 分帧块 %s' % tuple(p_warm))\n"
                "    # ★★ /dfprofperf rep：连渲同一页 3 次（冷 / 热对照）\n")

# (文件, 名字, 旧, 新, 哨兵) —— 哨兵只在「已应用」后出现。
JOBS = [
    (PROF, 'P0a 注释(名)', OLD_C0, NEW_C0, '第十一刀（rev17）：记忆表再改成'),
    (PROF, 'P0b 注释(图)', OLD_C1, NEW_C1, '与 PD.ItemName 一样**正 / 负分离**'),
    (PROF, 'P1 四表+Reset', OLD_P1, NEW_P1, 'local _nmPos, _nmPosN = {}, 0'),
    (PROF, 'P2 ItemName 头', OLD_P2, NEW_P2, '    local hit = _nmPos[id]\n'),
    (PROF, 'P3 ItemName 尾', OLD_P3, NEW_P3, '_nmPos[id], _nmPosN = nm, _nmPosN + 1'),
    (PROF, 'P4 ItemIcon', OLD_P4, NEW_P4, '_icPos[id], _icPosN = tex, _icPosN + 1'),
    (PROF, 'P5 空闲预热', OLD_P5, NEW_P5, 'function PD.WarmNames()'),
    (PROF, 'P6 Render 收尾', OLD_P6, NEW_P6,
     '    PD.RequestRows(rows)\n    PD.WarmNames()\n'),
    (CHECK, 'C1 harness 加断言', ANCHOR_CK, NEW_CK, '物品名/图标记忆表正负分离'),
    (MK, 'C2 生成器加断言', ANCHOR_CK, NEW_CK, '物品名/图标记忆表正负分离'),
    (MUT, 'D1 变异定义', MUT_DEF_ANCHOR, MUT_DEF + MUT_DEF_ANCHOR, 'MUT_PROF_NM_MEMO_RESET_ALL = '),
    (MUT, 'D2 变异登记', MUT_REG_ANCHOR, MUT_REG_NEW, 'MUT_PROF_NM_MEMO_RESET_ALL),'),
    (WANT, 'D3 DEFAULT_WANT', WANT_ANCHOR, WANT_NEW, '物品名记忆表连「已到货」也清'),
    (SMOKE, 'E1a 造态硬清正向', OLD_SMOKE_ZAOTAI, NEW_SMOKE_ZAOTAI, 'PD.ResetItemNameMemo(true)'),
    (SMOKE, 'E1b 冒烟行为自检', OLD_SMOKE_TAIL, NEW_SMOKE_TAIL, '"@@MEMO\\t"'),
    (SMOKE, 'E2 冒烟断言', OLD_SMOKE_CK, NEW_SMOKE_CK, '物品名正向记忆跨 Render 存活'),
    (CHECK, 'F1 df 旧断言跟新机制', F1_OLD, F1_NEW, '# ★ 第十一刀（rev17）：机制改成「正负分离」'),
    (CHECK, 'F2 df 旧断言(图标)', F2_OLD, F2_NEW, "and 'local _icNeg, _icN = {}, 0' in profui"),
    (MK, 'F3 mk 旧断言跟新机制', F1_OLD, F1_NEW, '# ★ 第十一刀（rev17）：机制改成「正负分离」'),
    (MK, 'F4 mk 旧断言(图标)', F2_OLD, F2_NEW, "and 'local _icNeg, _icN = {}, 0' in profui"),
]


def main():
    check = '--check' in sys.argv
    bad, plans, raws = 0, {}, {}
    for path, name, old, new, key in JOBS:
        if path not in raws:
            raws[path] = open(path, 'rb').read()
        raw = raws[path]
        src = plans.get(path) or raw.decode('utf-8')
        nl = '\r\n' if b'\r\n' in raw else '\n'

        def fx(s):
            return s if nl == '\n' else s.replace('\n', nl)

        if key and fx(key) in src:
            print('  [SKIP] %-26s 已应用' % name)
            continue

        o, n = fx(old), fx(new)
        if src.count(o) != 1:
            print('  [BAD ] %-26s 锚点 %d 次' % (name, src.count(o)))
            bad += 1
            continue
        plans[path] = src.replace(o, n, 1)
        print('  [OK  ] %-26s 锚点 1 次' % name)

    if bad:
        print('  \u2717 %d 处未通过，未落盘' % bad)
        return 1
    if check:
        print('  [OK  ] 预检通过（未落盘）')
        return 0
    for path, src in plans.items():
        if src != raws[path].decode('utf-8'):
            with open(path, 'wb') as f:
                f.write(src.encode('utf-8'))
            print('  [OK  ] 已写入 %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
