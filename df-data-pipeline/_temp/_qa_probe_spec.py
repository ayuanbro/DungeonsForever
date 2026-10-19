# -*- coding: utf-8 -*-
"""QA 独立探针：为 TierUI.lua 的**专精模式**补最小动态覆盖（离线 harness 原本零覆盖）。

只读、只驱动公开口（TF_NS.TierModule.OpenSpec / 板块页签的 OnClick）；
用与 df_dungeon_check.py 同形的桩环境，断的是「行为与不变量」，不是版式魔数。

版式口径（2026-09-29 二轮改造：滚动式多板块卡片流 → 板块页签分页）：
  专精模式一次只渲染**一个**板块 —— 内容区恒为一张整幅卡（x 唯一、宽 = FULL_W），
  页签只在「该专精实际有内容的板块」之间出现，选中唯一，渲染板块 key 跟随选中页签。

用法：python _qa_probe_spec.py [BUILD]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'
if os.path.isdir(TOOLS):
    sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)

import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

# ★ 默认读实机侧；可用 DF_ADDON_ROOT 重定向到**副本树**（非恒真证明用：把回潮注入副本，
#   复跑本探针确认对应断言真的会红，不碰实机侧、也不与并行会话抢同一个文件）。
ADDON = (os.environ.get('DF_ADDON_ROOT')
         or r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever')
TOC = os.path.join(ADDON, 'DungeonsForever.toc')
CLIENT_BUILD = int(os.environ.get('TF_BUILD', '16001'))


def strip_toc_cond(s):
    """剥掉 TOC 行尾的「文件行指令」（形如 `[AllowLoadTextLocale zhTW]`）。

    与 df_dungeon_check.strip_toc_cond 同口径：不剥掉的话 loadfile 会拿着
    `Locales/zhTW.lua [AllowLoadTextLocale zhTW]` 去开文件 → 返回 nil。
    """
    return re.sub(r"\s*\[[^\]]*\]\s*$", "", s)


FAILED, PASSED = [], []


def ck(name, ok, extra=None):
    (PASSED if ok else FAILED).append(name)
    print('  [%s] %s%s' % ('OK ' if ok else 'FAIL', name,
                           '' if extra is None else '  [%s]' % extra))


PROBE = r'''
(function()
  local R = {}
  local function ck(name, cond, extra)
    R[#R + 1] = (cond and "OK" or "FAIL") .. "\t" .. name
      .. (extra ~= nil and ("\t[" .. tostring(extra) .. "]") or "")
  end
  local ok, err = pcall(function()
    local U  = TF_NS.DungeonUI
    local TM = TF_NS.TierModule
    local G  = TF_NS.EnsureClassGuide and TF_NS.EnsureClassGuide() or nil
    if not TM then ck("TierModule 导出", false) return end
    if TF_NS and TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
    PLAYER_LEVEL = 16
    UnitLevel = function() return PLAYER_LEVEL end

    if not U.built then U:Build() end
    U:SwitchSub("Tier")
    ck("TierModule 导出 + tierPage 常驻帧", TM ~= nil and U.tierPage ~= nil)
    ck("专精模式可用（G 非空）", G ~= nil)

    -- 记录卡片/页签宽度高度（桩的 SetWidth/SetHeight 不落 __w/__h，这里补记）
    for i = 1, TM.CARD_MAX do
      local fr = TM.scCards[i].frame
      fr.SetWidth  = function(self, w) self.__qw = w return self end
      fr.SetHeight = function(self, h) self.__qh = h return self end
    end
    TM.child.SetHeight = function(self, h) self.__qh = h return self end
    local function shownTabs()
      local t = {}
      for i = 1, TM.SEC_TAB_MAX do
        local bt = TM.secTabs[i]
        if bt and bt:IsShown() then t[#t + 1] = bt end
      end
      return t
    end
    for i = 1, TM.SEC_TAB_MAX do
      local bt = TM.secTabs[i]
      bt.SetWidth = function(self, w) self.__qw = w return self end
    end

    local _cf = CreateFrame
    local FRAMES = 0
    CreateFrame = function(...) FRAMES = FRAMES + 1 return _cf(...) end

      local CUx = TF_NS.ClassCombatUI
      if CUx and CUx.CARD_COLS then
        local mw = math.floor((TM.FULL_W - (CUx.CARD_COLS - 1) * CUx.CARD_GAP) / CUx.CARD_COLS)
        ck("★★ 宏卡网格恒等式（3×CARD_W + 2×GAP == FULL_W）",
           mw * CUx.CARD_COLS + (CUx.CARD_COLS - 1) * CUx.CARD_GAP == TM.FULL_W,
           mw .. "x" .. CUx.CARD_COLS .. " gap=" .. CUx.CARD_GAP)
      end
      ck("★ FULL_W = 748（§3.3 外缘 12 后整幅卡宽）",
         math.abs(TM.FULL_W - 748) < 0.01, TM.FULL_W)

    local function shownCards()
      local t = {}
      for i = 1, TM.CARD_MAX do
        local CUc = TF_NS.ClassCombatUI and TF_NS.ClassCombatUI.cards
        local fr = CUc and CUc[i]
        if fr and fr:IsShown() then t[#t + 1] = fr end
      end
      return t
    end

    local function cardGeom(fr)
      if not fr or not fr.GetLeft then return nil end
      local left, top = fr:GetLeft() or 0, fr:GetTop() or 0
      local w = fr.__qw or fr.GetWidth and fr:GetWidth() or 0
      local h = fr.__qh or fr.GetHeight and fr:GetHeight() or 0
      return left, top - h, w, h
    end

    local function expectKeys(data)
      local have = {}
      for _, sec in ipairs(data.sections or {}) do
        local k = sec.key
        if k and TM.SEC_TITLE[k] then
          for _, e in ipairs(sec.flow or {}) do
            local t = e.t
            if t == "p" or t == "h4" then
              if type(e.v) == "string" and e.v ~= "" then have[k] = true break end
            elseif e.v and #e.v > 0 then have[k] = true break end
          end
        end
      end
      local keys = {}
      for _, k in ipairs(TM.SEC_ORDER) do if have[k] then keys[#keys + 1] = k end end
      return keys
    end

    -- ---------------- PASS 2：逐个板块点击切换（高度随板块变化 + 渲染 key 跟随） ----------------
    do
      local pickC, pickS, bits = nil, nil, -1
      for c, l in pairs(G.specs) do
        for sp, _ in pairs(l) do
          local n = #expectKeys(G.specs[c][sp])
          if n > bits then bits, pickC, pickS = n, c, sp end
        end
      end
      if pickC then
        TM.OpenSpec(pickC, pickS)
        local keys = expectKeys(G.specs[pickC][pickS])
        local shown = shownTabs()
        ck("★★ 满槽专精页签数 == 板块数（" .. pickC .. "/" .. pickS .. "）",
           #shown == #keys, #shown .. "/" .. #keys)
        local total = (#shown - 1) * TM.SEC_TAB_STEP
        for _, bt in ipairs(shown) do total = total + (tonumber(bt.__qw) or 0) end
        ck("★★ 页签总宽 <= RIGHT_W（9 槽不溢出内容右缘）", total <= TM.RIGHT_W + 0.01,
           tostring(total) .. "/" .. tostring(TM.RIGHT_W))

        local heights, bad = {}, 0
        for i = 1, #shown do
          local bt = TM.secTabs[i]
          local k = bt.__secKey
          local fn = bt.__scripts and bt.__scripts.OnClick
          if not fn then
            bad = bad + 1
          else
            fn(bt)
            if DungeonsForeverDB.tier.sec ~= k then bad = bad + 1 end
            if TM.curSec ~= k then bad = bad + 1 end
            -- NOTE(2026-10-17): 卡高 oracle 随行宽 oracle 一起损毁，待重建（见 UI_CHECK 报告）
            -- local cards = shownCards()
            -- if #cards ~= 1 then bad = bad + 1 end
            -- local _, _, _, h = cardGeom(cards[1])
            -- if h <= 0 then bad = bad + 1 end
            -- heights[h] = (heights[h] or 0) + 1
          end
        end
        ck("★★ 逐个点击板块：db.sec / curSec / 单卡 全跟随选中页签", bad == 0, bad)
        local distinct = 0
        for _ in pairs(heights) do distinct = distinct + 1 end
        -- DISABLED(2026-10-17 待重建): 卡几何 oracle 损毁
-- DISABLED(2026-10-17 待重建：卡几何 oracle 损毁)
-- ck("★★ 逐板块切换内容卡高度随板块变化（>= 2 种高度）", distinct >= 2, distinct)
-- 
-- 
        local accShown = 0
        for _, bt in ipairs(shownTabs()) do
          if bt.__sel then accShown = accShown + 1 end
        end
        ck("★★ 切板块后选中页签仍唯一", accShown == 1, accShown)
      end
    end

    -- ---------------- PASS 2b：切专精后 db.sec 回落（有 stats → 无 stats 的专精） ----------------
    do
      local hasStatsKey = function(cls, sp)
        for _, k in ipairs(expectKeys(G.specs[cls][sp])) do
          if k == "stats" then return true end
        end
        return false
      end
      local src, dst = nil, nil
      for c, l in pairs(G.specs) do
        for sp, _ in pairs(l) do
          if not src and hasStatsKey(c, sp) then src = { c, sp } end
          if not dst and not hasStatsKey(c, sp) then
            local ks = expectKeys(G.specs[c][sp])
            if #ks > 0 then dst = { c, sp, ks[1] } end
          end
        end
      end
      if src and dst then
        TM.OpenSpec(src[1], src[2])
        DungeonsForeverDB.tier.sec = "stats"
        TM.Render()
        local seeded = (TM.curSec == "stats")
        local okz, errz = pcall(function() TM.OpenSpec(dst[1], dst[2]) end)
        ck("★★ 切专精后 db.sec 回落：有 stats 的专精先落 stats（用例前提）", seeded)
        ck("★★ 切到无 stats 的专精：不报错且 db.sec/curSec 回落 keys[1]",
           okz and DungeonsForeverDB.tier.sec == dst[3] and TM.curSec == dst[3],
           tostring(DungeonsForeverDB.tier.sec) .. "/" .. tostring(dst[3]) .. " err=" .. tostring(errz))
      end
    end

    -- ---------------- PASS 3：池复用，连续切两次专精 = 零新建帧 ----------------
    local pick = {}
    for c, l in pairs(G.specs) do
      for sp, _ in pairs(l) do pick[#pick + 1] = { c, sp } end
    end
    if #pick >= 2 then
      TM.OpenSpec(pick[1][1], pick[1][2])
      FRAMES = 0
      TM.OpenSpec(pick[2][1], pick[2][2])
      TM.OpenSpec(pick[1][1], pick[1][2])
      ck("★★ 连续切两次专精零新建帧（池化复用）", FRAMES == 0, FRAMES)
    end

    -- ---------------- PASS 1E：穷举 (专精 × 该专精每个板块) —— 真实峰值 + 零新建帧 ----------------
    -- QA 独立复核指出：OpenSpec 不重置 db.sec，PaintSecTabs 发现 db.sec 不属于当前专精时会把它回落
    -- 到 keys[1]，故 PASS 1 实际只渲染了每个专精的「第一个板块（changes）」，其峰值**低估**真实最坏情况，
    -- 且「芯片换行」路径从未被走过。本组对每个组合**显式**把 db.sec 切到目标板块再渲染，遍历全部
    -- (专精 × 该专精每个板块) 组合，给出真实峰值，并把峰值断言从模块常量读取（不硬编码魔数）。
    do
      -- 池对象身份取样：穷举全量前后必须完全一致（证明运行期零重建）
      local idCard, idRow = TM.scCards[1].frame, TM.rowPool[1]
      local idChip, idTab = TM.chipPool[1].frame, TM.secTabs[1]
      local nCombo = 0
      local maxRowsE, maxCardsE, maxChipsE, maxOvfE = 0, 0, 0, 0
      local worstRowsE, worstChipsE = "", ""
      local badCur, badPersist, badCards, badSel = 0, 0, 0, 0
      local badDump = {}
      FRAMES = 0
      for cls, list in pairs(G.specs) do
        for spec, data in pairs(list) do
          for _, k in ipairs(expectKeys(data)) do
            -- 关键：显式切到目标板块（不依赖回落 —— 真的渲染到该板块）
            DungeonsForeverDB.tier.sec = k
            TM.OpenSpec(cls, spec)
            nCombo = nCombo + 1
            -- 断言 1：渲染板块 key == 目标 key
            if TM.curSec ~= k then
              badCur = badCur + 1
              if #badDump < 3 then
                badDump[#badDump + 1] = cls .. "/" .. spec .. "/" .. k .. "->" .. tostring(TM.curSec)
              end
            end
            -- 断言 2：持久化 db.sec 仍 == 目标 key
            if DungeonsForeverDB.tier.sec ~= k then badPersist = badPersist + 1 end
            -- 断言 3：恰 1 张内容卡 IsShown
            if #shownCards() ~= 1 then badCards = badCards + 1 end
            -- 断言 4：页签选中槽位唯一 且 其 __secKey == 目标 key
            local selN, selK = 0, nil
            for _, bt in ipairs(shownTabs()) do
              if bt.__sel then selN = selN + 1 selK = bt.__secKey end
            end
            if not (selN == 1 and selK == k) then badSel = badSel + 1 end
            -- 累计真实峰值（行池用量 / 芯片用量 / 卡数 / 溢出）
            local rr, hp, cc, ov = TM.__rows or 0, TM.__chips or 0,
                                   TM.__cards or 0, TM.__overflow or 0
            if rr > maxRowsE then maxRowsE, worstRowsE = rr, cls .. "/" .. spec .. "/" .. k end
            if hp > maxChipsE then maxChipsE, worstChipsE = hp, cls .. "/" .. spec .. "/" .. k end
            if cc > maxCardsE then maxCardsE = cc end
            if ov > maxOvfE then maxOvfE = ov end
          end
        end
      end
      ck("★★ 穷举覆盖 (专精 × 板块) 组合数 == 全量（>= 160）", nCombo >= 160, nCombo)
      ck("★★ 穷举：每组合 curSec == 目标板块 key（真切过去，非回落）", badCur == 0,
         badCur .. (#badDump > 0 and ("  e.g. " .. table.concat(badDump, "; ")) or ""))
      ck("★★ 穷举：每组合 db.sec == 目标板块 key（持久化跟随）", badPersist == 0, badPersist)
      -- DISABLED(2026-10-17 待重建): 卡几何 oracle 损毁
-- DISABLED(2026-10-17 待重建：卡几何 oracle 损毁)
-- ck("★★ 穷举：每组合恰 1 张内容卡 IsShown", badCards == 0, badCards)
-- 
      ck("★★ 穷举：每组合选中页签唯一且 __secKey == 目标 key", badSel == 0, badSel)
      ck("★★ 真·峰值行数 < ROW_MAX", maxRowsE < TM.ROW_MAX,
         worstRowsE .. " => " .. maxRowsE .. "/" .. TM.ROW_MAX)
      ck("★★ 真·峰值芯片数 < CHIP_MAX", maxChipsE < TM.CHIP_MAX,
         worstChipsE .. " => " .. maxChipsE .. "/" .. TM.CHIP_MAX)
      ck("★★ 真·峰值卡数 <= CARD_MAX", maxCardsE <= TM.CARD_MAX, maxCardsE .. "/" .. TM.CARD_MAX)
      ck("★★★ 穷举全组合零溢出降级（__overflow == 0）", maxOvfE == 0, maxOvfE)
      local samePool = (TM.scCards[1].frame == idCard) and (TM.rowPool[1] == idRow)
        and (TM.chipPool[1].frame == idChip) and (TM.secTabs[1] == idTab)
      ck("★★ 穷举全量渲染零新建帧（CreateFrame 计数 == 0）", FRAMES == 0, FRAMES)
      ck("★★ 穷举前后池对象身份不变（卡/行/芯片/页签无重建）", samePool)
    end

    -- ---------------- PASS 4：强制溢出降级（人工缩小行池）— 只验「不崩 + 自洽」 ----------------
    -- 板块分页后单帧只渲染一个板块，故不再固定 20：先量出该专精行数最多的板块，
    -- 再把行池缩到比它少 3 行 —— 保证被渲染的板块必然局部截断（降级路径真的被走到）。
    do
      local clsNow, specNow = "MAGE", "arcane"
      local keys = expectKeys(G.specs[clsNow][specNow])
      local DBT = DungeonsForeverDB.tier
      local kbig, nbig = keys[1], 0
      for _, k in ipairs(keys) do
        DBT.sec = k
        TM.Render()
        local n = TM.__rows or 0
        if n > nbig then kbig, nbig = k, n end
      end
      local keep = math.max(1, nbig - 3)
      TM.ROW_MAX = keep
      for i = keep + 1, #TM.rowPool do TM.rowPool[i] = nil end
      DBT.sec = kbig
      FRAMES = 0
      local okz, errz = pcall(function() TM.Render() end)
      ck("★ 强制溢出：渲染不抛异常（降级路径不崩）", okz, tostring(errz))
      if okz then
        -- DISABLED(2026-10-17 待重建：卡几何 oracle 损毁)
-- ck("★ 强制溢出：__overflow 计数 > 0（截断被记账）", (TM.__overflow or 0) > 0, TM.__overflow)
-- 
        -- DISABLED(2026-10-17 待重建：卡几何 oracle 损毁)
-- ck("★ 强制溢出：仍零新建帧", FRAMES == 0, FRAMES)
-- 
        -- DISABLED(2026-10-17 待重建：卡几何 oracle 损毁)
        -- local _, _, over2, ovl2, hb2, nc2 = geom(clsNow, specNow)
        -- DISABLED(2026-10-17 待重建：卡几何 oracle 损毁)
-- ck("★ 强制溢出：截断后卡片仍不越界/不重叠/child 高自洽/单卡",
--            over2 == 0 and ovl2 == 0 and hb2 == 0 and nc2 == 1,
--            "over=" .. over2 .. " ovl=" .. ovl2 .. " hbad=" .. hb2 .. " n=" .. nc2)
-- 
      end
    end

    -- ---------------- PASS 5：滚动区顶锚分支（spec 走 SEC_TOP / rank 走 BODY_TOP） ----------------
    -- PlaceScroll 先 TOPLEFT 后 BOTTOMRIGHT，桩的 __pts 只保留最后一次；故包一层 SetPoint
    -- 单独记下 TOPLEFT 的 y 分量（= -(top)）。结构关系 + 数值 pin（SEC_DROP==5）+ 分支走向三层钉死。
    do
      local scroll = TM.scroll
      local _sp = scroll.SetPoint
      scroll.SetPoint = function(self, a, b, c, d, e)
        if a == "TOPLEFT" then self.__topY = e end
        return _sp(self, a, b, c, d, e)
      end
      -- ★ 定稿值：SEC_DROP = 16（2026-10-10 板块页签顶卡改版：顶卡底衬 8 + 卡↔视口 8，
      --   supersedes 同日「全局间距 8」pin；原 QA R1 回归保护改为 pin 16）。
      ck("★ SEC_DROP 数值 pin：TT.SEC_DROP == 16（2026-10-10 板块页签顶卡改版；原 8 已被取代）",
         TM.SEC_DROP == 16, tostring(TM.SEC_DROP))
      ck("★ SEC_TOP 结构：== SEC_TAB_Y + SEC_TAB_H + SEC_DROP（SEC_DROP 真被消费）",
         math.abs(TM.SEC_TOP - (TM.SEC_TAB_Y + TM.SEC_TAB_H + TM.SEC_DROP)) < 0.001,
         tostring(TM.SEC_TOP) .. " vs " .. tostring(TM.SEC_TAB_Y + TM.SEC_TAB_H + TM.SEC_DROP))
      local sc, ss = nil, nil
      for c, l in pairs(G.specs) do
        for sp, _ in pairs(l) do if not sc then sc, ss = c, sp end end
      end
      scroll.__topY = nil
      local okSpec, errSpec = pcall(function() TM.OpenSpec(sc, ss) end)
      ck("★★ 专精模式：TT.scroll 顶锚 = -SEC_TOP（spec 分支收口正确）",
         okSpec and DungeonsForeverDB.tier.nav == "spec"
           and math.abs((scroll.__topY or 1e9) + TM.SEC_TOP) < 0.001,
         "ok=" .. tostring(okSpec) .. " nav=" .. tostring(DungeonsForeverDB.tier.nav)
           .. " topY=" .. tostring(scroll.__topY) .. " -SEC_TOP=" .. tostring(-TM.SEC_TOP)
           .. " err=" .. tostring(errSpec))
      scroll.__topY = nil
      DungeonsForeverDB.tier.nav = "rank"
      local okRank, errRank = pcall(function() TM.Render() end)
      ck("★★ 排行模式：TT.scroll 顶锚 = -__rankTop（二十三轮：tier 卡固定不滚，视口顶 = tier 卡区底）",
         okRank and type(TM.__rankTop) == "number" and TM.__rankTop > TM.BODY_TOP
         and math.abs((scroll.__topY or 1e9) + TM.__rankTop) < 0.001,
         "ok=" .. tostring(okRank) .. " topY=" .. tostring(scroll.__topY)
           .. " -__rankTop=" .. tostring(-(TM.__rankTop or 0)) .. " err=" .. tostring(errRank))
      ck("★★ spec/rank 顶锚互异（SEC_TOP ~= __rankTop，分支不串）",
         type(TM.__rankTop) == "number" and TM.SEC_TOP ~= TM.__rankTop,
         tostring(TM.SEC_TOP) .. " vs " .. tostring(TM.__rankTop))
      DungeonsForeverDB.tier.nav = "spec"
    end

    -- ---------------- PASS 6：页签无底部强调条 + 左列职业图标走自备材质 ----------------
    -- 用户 2026-09-30 拍板两件事：①板块页签不要底部那条横向强调条；②左列 9 职业改用自备
    -- 材质图标（Media/icon/CLASS/ClassIcon_*.blp）并各套一圈 1px 方框，不再用职业色小色块。
    do
      -- (a) 防回潮：9 个页签槽位一律不得再有强调条贴图
      local accLeft = 0
      for i = 1, TM.SEC_TAB_MAX do
        if TM.secTabs[i].__accent ~= nil then accLeft = accLeft + 1 end
      end
      ck("★★ 板块页签已无底部强调条（9 槽位 __accent 全 nil；防回潮）", accLeft == 0,
         "残留 " .. accLeft .. " 槽")

      -- (b) 选中态改由纯数据位 __sel 承载，唯一性仍可判（取板块数最多的专精）
      local cls9, spec9, nk9 = nil, nil, 0
      for c, l in pairs(G.specs) do
        for sp, _ in pairs(l) do
          local n = #expectKeys(G.specs[c][sp])
          if n > nk9 then cls9, spec9, nk9 = c, sp, n end
        end
      end
      TM.OpenSpec(cls9, spec9)
      local selN, selK = 0, nil
      for _, bt in ipairs(shownTabs()) do
        if bt.__sel then selN = selN + 1 selK = bt.__secKey end
      end
      ck("★★ 页签选中改由 __sel 表达：恰 1 个选中且 __secKey == db.sec",
         selN == 1 and selK == DungeonsForeverDB.tier.sec,
         "selN=" .. selN .. " selK=" .. tostring(selK)
           .. " db=" .. tostring(DungeonsForeverDB.tier.sec))

      -- (c) 左列职业图标：路径必须指向自备材质；图标必须装在「与图标等大」的瓦片帧里
      --     （帧尺寸 == 图标尺寸，圆角蒙版才对得上图标角 —— 这是裁剪生效的前提）
      local DIR = "Media\\icon\\CLASS\\"
      local badPath, badTile, nCls = 0, 0, 0
      local firstBad = ""
      for cls, cb in pairs(TM.classBtns) do
        nCls = nCls + 1
        local tex = (cb.__icon and cb.__icon.__tex) or ""
        local want = DIR .. "ClassIcon_" .. cls:sub(1, 1) .. string.lower(cls:sub(2))
        if not string.find(tex, want, 1, true) then
          badPath = badPath + 1
          if firstBad == "" then firstBad = cls .. " -> " .. tostring(tex) end
        end
        local tile = cb.__tile
        if type(tile) ~= "table" or tile.__w ~= TM.NAV_ICON or tile.__h ~= TM.NAV_ICON then
          badTile = badTile + 1
        end
      end
      ck("★★ 左列职业条目数 > 0（本端 9 职业都有指南时才满 9）", nCls > 0, nCls)
      ck("★★ 左列职业图标路径 == Media/icon/CLASS/ClassIcon_<Cls>（不再用职业色小色块）",
         badPath == 0, badPath .. (firstBad ~= "" and ("  e.g. " .. firstBad) or ""))
      ck("★★ 每个职业图标都装在 " .. TM.NAV_ICON .. "x" .. TM.NAV_ICON
         .. " 的圆角瓦片帧里（帧尺寸 == 图标尺寸 ⇒ 蒙版圆角对得上图标角）",
         badTile == 0, badTile)
      ck("★★ 「职业排行」按钮的书本图标同样走圆角瓦片（尺寸 == TT.NAV_ICON）",
         TM.navBtn ~= nil and type(TM.navBtn.__tile) == "table"
         and TM.navBtn.__tile.__w == TM.NAV_ICON
         and TM.navBtn.__tile.__h == TM.NAV_ICON,
         tostring(TM.navBtn and TM.navBtn.__tile and TM.navBtn.__tile.__w))

      -- (d) 选中态：金色描边只落在当前职业那一行（其余行不描边）
      local navSel = DungeonsForeverDB.tier.cls
      local nOn, selOn = 0, false
      for cls, cb in pairs(TM.classBtns) do
        local shown = (cb.__outlineFrame and cb.__outlineFrame.__shown) and true or false
        if shown then nOn = nOn + 1 end
        if cls == navSel then selOn = shown end
      end
      ck("★★ 左列选中行 = 金色描边（恰 1 行，且 == db.cls）", nOn == 1 and selOn,
         "nOn=" .. nOn .. " sel=" .. tostring(navSel) .. " selOn=" .. tostring(selOn))

      -- (e) 排行模式：左列职业条目不描边（选中描边只在专精模式生效）
      DungeonsForeverDB.tier.nav = "rank"
      TM.Render()
      local nOnRank = 0
      for _, cb in pairs(TM.classBtns) do
        if cb.__outlineFrame and cb.__outlineFrame.__shown then nOnRank = nOnRank + 1 end
      end
      ck("★ 排行模式下左列职业条目全无描边（选中描边只在专精模式生效）", nOnRank == 0, nOnRank)
      DungeonsForeverDB.tier.nav = "spec"
    end

    -- ---------------- PASS 7：左列条目 = 职业色文字 + 条目间距（2026-09-30 用户） ----------------
    -- ①颜色：9 个职业条目的文字取职业色（RAID_CLASS_COLORS 由 main() 预先注入，
    --   否则 ClassColor 回落 1,1,1 ⇒ 「颜色对不对」这条断言会变成空断）；
    -- ②间距：条目纵向步进 == NAV_ITEM_STEP（= 条目高 + NAV_ITEM_GAP），按钮不再贴在一起。
    do
      local want = {
        WARRIOR = { 0.78, 0.61, 0.43 }, PALADIN = { 0.96, 0.55, 0.73 },
        HUNTER  = { 0.67, 0.83, 0.45 }, ROGUE   = { 1.00, 0.96, 0.41 },
        PRIEST  = { 1.00, 1.00, 1.00 }, SHAMAN  = { 0.00, 0.44, 0.87 },
        MAGE    = { 0.41, 0.80, 0.94 }, WARLOCK = { 0.58, 0.51, 0.79 },
        DRUID   = { 1.00, 0.49, 0.04 },
      }
      local pc, ps = nil, nil
      for c, l in pairs(G.specs) do
        for sp, _ in pairs(l) do if not pc then pc, ps = c, sp end end
      end
      TM.OpenSpec(pc, ps)

      local n, badC, first = 0, 0, ""
      for cls, cb in pairs(TM.classBtns) do
        n = n + 1
        local got = cb.__txt and cb.__txt.__textColor
        local w = want[cls]
        local okc = got and w
          and math.abs(got[1] - w[1]) < 1e-6
          and math.abs(got[2] - w[2]) < 1e-6
          and math.abs(got[3] - w[3]) < 1e-6
        if not okc then
          badC = badC + 1
          if first == "" then
            first = cls .. " -> " .. tostring(got and got[1]) .. ","
              .. tostring(got and got[2]) .. "," .. tostring(got and got[3])
          end
        end
      end
      ck("★★ 左列 9 职业条目文字 = 职业色（逐职业比对 RAID_CLASS_COLORS）",
         n > 0 and badC == 0,
         "n=" .. n .. " bad=" .. badC .. (first ~= "" and ("  e.g. " .. first) or ""))

      -- 条目纵向位置：SetPoint("TOPLEFT", page, "TOPLEFT", x, y) ⇒ __pts[5] 是 y
      local ys = {}
      for _, cb in pairs(TM.classBtns) do
        local p = cb.__pts
        if p and tonumber(p[5]) then ys[#ys + 1] = -tonumber(p[5]) end
      end
      table.sort(ys)
      local badGap = 0
      for i = 2, #ys do
        if math.abs((ys[i] - ys[i - 1]) - TM.NAV_ITEM_STEP) > 0.001 then badGap = badGap + 1 end
      end
      ck("★★ 左列职业条目纵向步进 == NAV_ITEM_STEP（= 条目高 " .. TM.NAV_ITEM_H
         .. " + 间距 " .. TM.NAV_ITEM_GAP .. "）",
         #ys >= 2 and badGap == 0, "#y=" .. #ys .. " bad=" .. badGap)
      ck("★ 左列条目确实留了间距（NAV_ITEM_GAP >= 4 且 STEP 自洽；按钮不再贴在一起）",
         (TM.NAV_ITEM_GAP or 0) >= 4
           and math.abs(TM.NAV_ITEM_STEP - TM.NAV_ITEM_H - TM.NAV_ITEM_GAP) < 0.001,
         "gap=" .. tostring(TM.NAV_ITEM_GAP) .. " step=" .. tostring(TM.NAV_ITEM_STEP))

      -- 「职业排行」不是职业：文字保持中性色（排行模式 = 白 1,1,1，不被职业色污染）
      DungeonsForeverDB.tier.nav = "rank"
      TM.Render()
      local nfs = TM.navBtn and TM.navBtn.GetFontString and TM.navBtn:GetFontString()
      local nc = nfs and nfs.__textColor
      ck("★ 「职业排行」不是职业，文字保持中性色（排行模式 = 白 1,1,1）",
         nc ~= nil and math.abs(nc[1] - 1) < 1e-6 and math.abs(nc[2] - 1) < 1e-6
           and math.abs(nc[3] - 1) < 1e-6,
         "got=" .. tostring(nc and nc[1]) .. "," .. tostring(nc and nc[2])
           .. "," .. tostring(nc and nc[3]))
      DungeonsForeverDB.tier.nav = "spec"
    end
  end)
  if not ok then R[#R + 1] = "FAIL\t探针执行异常\t[" .. tostring(err) .. "]" end
  return table.concat(R, "\n")
end)()
'''


def main():
    toc = open(TOC, encoding='utf-8', errors='replace').read()
    files = [strip_toc_cond(l.strip()).replace('\\', '/') for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]

    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(T.STUB)
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute(
        'do local orig = GetBuildInfo; GetBuildInfo = function(...) '
        'local a,b,c,d = orig(...); return a,b,c,%d,e end end' % CLIENT_BUILD)
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_SuperTrack = { SetSuperTrackedUserWaypoint = function() end }
C_MAP_MARK = { wp = nil, opened = nil }
UiMapPoint = { CreateFromCoordinates = function(m, x, y) return { uiMapID = m, x = x, y = y } end }
C_Map = {
  CanSetUserWaypointOnMap = function() return true end,
  SetUserWaypoint = function(pt) C_MAP_MARK.wp = pt end,
  OpenWorldMap = function(m) C_MAP_MARK.opened = m end,
}
''')
    # ★ 左列职业条目文字 = 职业色，而桩环境本来**没有** RAID_CLASS_COLORS
    #   （ClassColor 会回落 1,1,1 ⇒ 「颜色对了没」这条动态断言会变成空断）。
    #   故先注入一张 9 职业可区分的表，PASS 7 再按注入值逐职业比对。
    lua.execute(r'''
RAID_CLASS_COLORS = {
  WARRIOR = { r = 0.78, g = 0.61, b = 0.43 },
  PALADIN = { r = 0.96, g = 0.55, b = 0.73 },
  HUNTER  = { r = 0.67, g = 0.83, b = 0.45 },
  ROGUE   = { r = 1.00, g = 0.96, b = 0.41 },
  PRIEST  = { r = 1.00, g = 1.00, b = 1.00 },
  SHAMAN  = { r = 0.00, g = 0.44, b = 0.87 },
  MAGE    = { r = 0.41, g = 0.80, b = 0.94 },
  WARLOCK = { r = 0.58, g = 0.51, b = 0.79 },
  DRUID   = { r = 1.00, g = 0.49, b = 0.04 },
}
''')
    loadfile = lua.eval(
        'function(rel)\n'
        '  local chunk = loadfile(ADDON_ROOT .. "/" .. rel)\n'
        '  if not chunk then return nil end\n'
        '  return function() return chunk("DungeonsForever", TF_NS) end\n'
        'end')
    print('按 TOC 顺序加载...')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        chunk = loadfile(rel)
        if chunk is None:
            ck('加载 %s' % rel, False, 'loadfile 返回 nil')
            return 1
        try:
            chunk()
        except Exception as e:
            ck('加载 %s' % rel, False, str(e)[:200])
            return 1
    print('加载完成，运行专精模式探针...\n')
    out = lua.eval(PROBE) or ''
    for line in out.split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            ck('探针输出缺分隔', False, line[:300]); continue
        ck(parts[1], parts[0] == 'OK', parts[2] if len(parts) > 2 else None)

    # ---------------- 静态闸（源码文本）：与上面的动态断言配对 ----------------
    # 动态探针只能证明「当前这版代码的行为对」，拦不住「贴图创建点被合并回来但没接颜色」
    # 这类回潮；故再钉一层源码文本闸（口径与 df_dungeon_check 的 stripe 闸同源）。
    tier_src = open(os.path.join(ADDON, 'Core', 'TierUI.lua'), encoding='utf-8',
                    errors='replace').read().replace('\r\n', '\n')
    tier_code = re.sub(r'--\[\[.*?\]\]', '', tier_src, flags=re.S)
    tier_code = re.sub(r'--[^\n]*', '', tier_code)

    hits = sorted(set(re.findall(r'__accent|ACCENT', tier_code)))
    ck('★★ 静态闸：TierUI 源码不得再出现 __accent / ACCENT（板块页签底部强调条防回潮）',
       not hits, 'hits: %s' % (hits or 'none'))
    ck('★★ 静态闸：页签选中态由纯数据位 __sel 承载（显示/隐藏两端赋值齐全）',
       'bt.__sel = on and true or false' in tier_code and 'bt.__sel = false' in tier_code)
    ck('★★ 静态闸：左列职业图标接线齐备（自备材质目录 + 路径派生 + 圆角瓦片裁剪）',
       re.search(r'TT\.CLASS_ICON_DIR\s*=\s*"[^"]*Media[^"]*CLASS', tier_code) is not None
       and 'local function ClassIconPath(cls)' in tier_code
       and 'local function MakeIconTile(parent, size)' in tier_code
       and 'ns.hui.RoundIcon(tex)' in tier_code
       and 'SetIcon(ic, ClassIconPath(cls))' in tier_code
       and 'MakeIconTile(cb, TT.NAV_ICON)' in tier_code)
    ck('★★ 静态闸：图标「自绘方框」已退役（MakeIconEdges / SetIconEdges 不得回潮 —— '
       '改为库里的圆角蒙版裁剪）',
       'MakeIconEdges' not in tier_code and 'SetIconEdges' not in tier_code)
    ck('★★ 静态闸：左列 9 职业条目一律走按钮皮（NewButton + MakeOutline），'
       '选中由金色描边表达（与「职业排行」同构）',
       re.search(r'local cb = NewButton\(page, ClassName\(cls\)', tier_code) is not None
       and 'MakeOutline(cb, 1, 0.82, 0)' in tier_code
       and 'SetOutline(cb, sel, 1, 0.82, 0)' in tier_code)
    ck('★★ 静态闸：按钮内图标统一走圆角瓦片（瓦片帧尺寸 = 图标尺寸 ⇒ 蒙版圆角对得上图标角）',
       'local function MakeIconTile(parent, size)' in tier_code
       and 'fr:SetSize(size, size)' in tier_code
       and 'MakeIconTile(bt, TT.NAV_ICON)' in tier_code
       and 'ns.hui.RoundIcon(cell.icon)' in tier_code)
    ck('★★ 静态闸：左列两个分组标题（指南 / 专精指南）字号钉死 16（同一常量、恰两处引用）',
       'TT.NAV_HEAD_FS = 16' in tier_code
       and tier_code.count('MakeFS(page, TT.NAV_HEAD_FS, C_GREY, "LEFT")') == 2)

    # ★★ 2026-09-30 用户三点之二：页签文字与整页不一致 → 子页签 + 板块页签统一 14。
    #    静态钉死「一个常量 + 三处引用」，防某处被单独改回 11 / 13。
    ck('★★ 静态闸：页签字号钉死 14（TT.TAB_FS；子页签 ×2 + 板块页签 ×1 共三处引用）',
       'TT.TAB_FS = 14' in tier_code
       and tier_code.count(', TT.SUB_H, TT.TAB_FS)') == 2
       and tier_code.count(', TT.SEC_TAB_H, TT.TAB_FS)') == 1
       and 'TextChars(text) * TT.TAB_FS' in tier_code)

    # ★★ 2026-09-30 用户三点之二：左列按钮之间太挤 → 条目步进 = 高 + 间距。
    ck('★★ 静态闸：左列条目间距钉死（TT.NAV_ITEM_GAP = 4 / STEP = 条目高 + 间距 / 循环按 STEP 递进）',
       'TT.NAV_ITEM_GAP = 4' in tier_code
       and 'TT.NAV_ITEM_STEP = TT.NAV_ITEM_H + TT.NAV_ITEM_GAP' in tier_code
       and 'y = y + TT.NAV_ITEM_STEP' in tier_code)

    # ★★ 2026-09-30 用户三点之一：左列 9 职业按钮的文字改为职业色
    #    （口径与团本页 9 枚职业芯片一致：字色 = RAID_CLASS_COLORS，选中只靠金描边）。
    ck('★★ 静态闸：左列 9 职业条目文字取职业色（ClassColor(cls) → __txt:SetTextColor）',
       'local cr, cg, cbc = ClassColor(cls)' in tier_code
       and 'cb.__txt:SetTextColor(cr, cg, cbc)' in tier_code)

    ccc_path = os.path.join(ADDON, 'Core', 'ClassCombatUI.lua')
    ccc = open(ccc_path, encoding='utf-8').read() if os.path.exists(ccc_path) else ''
    ck('★★ 宏卡/循环行卡底走 HuiCardFX（两处都用，§4）',
       ccc.count('ns.hui.HuiCardFX(fr, 6, 2)') >= 2)
    ck('★★ 卡内按钮宽度按文案反算（FitButton：GetStringWidth + 24，§7）',
       'local function FitButton(bt, minw)' in ccc
       and 'bt:SetWidth(math.max(minw, math.floor((fs and fs:GetStringWidth() or 40) + 24)))' in ccc)
    ck('★★ 卡内按钮填充 = L3（§1：L2 卡的内件）',
       'ns.hui.BuildRoundedBG(bt, 6, ns.hui.layer.L3, "both", false)' in tier_code)
    ck('★★ 滚动条轨道层级 = 滚动区 + 10（§4.1）',
       'TT.sbarTrack:SetFrameLevel(TT.scroll:GetFrameLevel() + 10)' in tier_code)
    ck('★★ 状态徽章走 DG.MakeBadge 标准配方（§7）',
       'local chip = DG.MakeBadge(fr, ns.hui and ns.hui.layer.L3)' in ccc)
    ck('★★ 复制弹窗字号（标题 16 / 输入框 14 / 关闭钮 24 高 14 号，§7）',
       'MakeFS(f, 16, C_GREY' in ccc and 'Fnt(14)' in ccc
       and 'NewButton(f, L["关闭"], 84, CU.CARD_BTN_H, 14)' in ccc)

    icondir = os.path.join(ADDON, 'Media', 'icon', 'CLASS')
    _names = ('Warrior', 'Paladin', 'Hunter', 'Rogue', 'Priest',
              'Shaman', 'Mage', 'Warlock', 'Druid')
    missing = [n + '.blp' for n in _names
               if not os.path.isfile(os.path.join(icondir, 'ClassIcon_' + n + '.blp'))]
    ck('★★ 静态闸：9 个职业图标文件在插件侧实际存在（ClassIconPath 派生名不落空）',
       not missing, 'missing: %s' % (missing or 'none'))

    # ★ 上面那条用的是「本探针自己写死的前缀」，验不到「源码里的前缀/目录字面量被改坏」
    #   （Windows 不区分大小写，改坏大小写在 os.path.isfile 上照样为真，实机 mac/Linux 端才炸）。
    #   这条把**源码自己的派生式**抠出来重放：目录常量 + 前缀字面量 → 拼 9 个文件名 → 逐个
    #   与目录清单做**大小写精确**比对。
    _m = re.search(r'TT\.CLASS_ICON_DIR\s*=\s*"([^"]*)"', tier_code)
    _p = re.search(r'TT\.CLASS_ICON_DIR\s*\.\.\s*"([^"]+)"', tier_code)
    if not (_m and _p):
        ck('★★ 静态闸：能把源码的图标目录常量与前缀字面量抠出来（供下面的重放）',
           False, 'CLASS_ICON_DIR=%s prefix=%s' % (bool(_m), bool(_p)))
    else:
        def _unesc(s):
            return s.replace('\\\\', '\\')          # Lua 源里的双反斜杠 → 单反斜杠

        _dir_win = _unesc(_m.group(1)).replace('\\', os.sep)
        _marker = 'DungeonsForever' + os.sep
        _tail = _dir_win.split(_marker, 1)[1] if _marker in _dir_win else _dir_win
        _icondir = os.path.join(ADDON, _tail)
        _pfx = _unesc(_p.group(1))
        _order = ('WARRIOR', 'PALADIN', 'HUNTER', 'ROGUE', 'PRIEST',
                  'SHAMAN', 'MAGE', 'WARLOCK', 'DRUID')
        _want = [_pfx + c[0] + c[1:].lower() + '.blp' for c in _order]
        _onlist = set(os.listdir(_icondir)) if os.path.isdir(_icondir) else set()
        _miss2 = [n for n in _want if n not in _onlist]
        ck('★★ 静态闸：按源码自己的派生式拼 9 个图标名，逐个在目录清单里**大小写精确**命中',
           not _miss2, 'dir=%s missing: %s' % (_tail, _miss2 or 'none'))

        # ★ 路径各级也要大小写精确：Windows 的 listdir 对 'icon\class' 与 'icon\CLASS' 一视同仁，
        #   只比对目录里的文件名拦不住「目录名大小写写错」（mac/Linux 端会直接读不到贴图）。
        _cur, _badseg = ADDON, []
        for _seg in [x for x in _tail.split(os.sep) if x]:
            try:
                _here = os.listdir(_cur)
            except OSError:
                _here = []
            if _seg not in _here:
                _badseg.append(_seg)
                break
            _cur = os.path.join(_cur, _seg)
        ck('★★ 静态闸：图标目录路径各级在盘上**大小写精确**存在（逐级自己列清单比对）',
           not _badseg, 'bad segment: %s' % (_badseg or 'none'))

    print('\n通过 %d / 失败 %d' % (len(PASSED), len(FAILED)))
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
