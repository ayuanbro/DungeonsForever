# -*- coding: utf-8 -*-
"""独立冒烟（2026-10-11）：专业升级 HUD 的数据随「固定路线 / 自动计算」模式切换。

背景：共享 harness（df_dungeon_check.py）的动态块被并行会话的在途改动提前崩掉
      （`wallLabels` nil）→ 运行时段跑不到，本冒烟自建驱动链。
只读产品文件、只在内存桩里跑，不写任何产品文件。

用法：
  python _temp/_hud_routemode_smoke.py                    # 打 beta 副本（harness 口径）
  DF_ADDON_ROOT=D:/workspace/DungeonsForever python _temp/_hud_routemode_smoke.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # 复用 T.STUB / ADDON / TOC
from lupa import lua51

FAILS = []


def ck(name, ok, extra=''):
    tag = 'OK ' if ok else 'FAIL'
    line = '  [%s] %s%s' % (tag, name, ('  [%s]' % extra) if extra != '' else '')
    print(line)
    if not ok:
        FAILS.append(name)


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    build = 16001
    toc = open(os.path.join(addon, os.path.basename(D.TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]

    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(D.T.STUB)
    lua.execute('C_Timer = { After = function(t, fn) fn() end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('UnitName = function() return "冒烟角色" end')
    lua.execute('GetRealmName = function() return "测试服" end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute(
        'do local orig = GetBuildInfo; GetBuildInfo = function(...) '
        'local a,b,c,d = orig(...); return a, b, c, %d, e end end' % build)
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_Map = {
  CanSetUserWaypointOnMap = function() return true end,
  SetUserWaypoint = function(pt) end,
  OpenWorldMap = function(mapID) end,
  GetAreaInfo = function(id) return "测区" .. tostring(id) end,
}
''')
    loadfile = lua.eval(
        'function(rel)\n'
        '  local chunk = loadfile(ADDON_ROOT .. "/" .. rel)\n'
        '  if not chunk then return nil end\n'
        '  return function() return chunk("DungeonsForever", TF_NS) end\n'
        'end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        chunk = loadfile(rel)
        if chunk is None:
            print('加载 %s 失败（loadfile nil）' % rel)
            return 1
        try:
            chunk()
        except Exception as e:
            print('加载 %s 抛异常：%s' % (rel, str(e)[:300]))
            return 1
    print('已加载 %d 个 Lua 文件，开始驱动链'
          % len([f for f in files if not f.lower().endswith('.xml')]))

    DRIVER = r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
  local PD = TF_NS.ProfModule
  PD.Show("alchemy")
  PD.SetTab("leveling")
end
'''
    lua.execute(DRIVER)

    SCRIPT = r'''
(function()
  local PD  = TF_NS.ProfModule
  local PF  = TF_NS.ProfFollow
  local LV  = TF_NS.ProfLeveling
  local RA  = TF_NS.ProfRouteAuto
  local out = {}
  local function ck(name, ok, extra)
    out[#out + 1] = { name, ok and 1 or 0, extra or "" }
  end

  local function followEntry(slug)
    local p = DungeonsForeverDB and DungeonsForeverDB.prof
    local fu = p and p.follow
    if not fu then return nil end
    for _, e in pairs(fu) do if e and e.slug == slug then return e end end
    return nil
  end
  local function segText() return (PF.f and PF.f.seg and PF.f.seg.__text) or "" end
  local function cardName()
    local c = PF.f and PF.f.card
    return (c and c.name and c.name.__text) or ""
  end
  local function optsFor(skill)
    return {
      start = (PD.Setting("autoFromCurrent") and skill) and math.max(1, skill) or 1,
      onlyAH = PD.Setting("autoOnlyAH"),
      noFormula = PD.Setting("autoNoFormula"),
      learnedOnly = PD.Setting("autoLearnedOnly"),
      target = PD.LvTarget(),
    }
  end
  local function derivedOf(steps, skill)
    for i, s in ipairs(steps or {}) do if skill < s[2] then return i end end
    return #(steps or {}) + 1
  end

  if RA and RA.Invalidate then RA.Invalidate() end
  Auctionator = nil

  -- ---------- 阶段 1：默认（设置关）→ 固定路线 ----------
  local slug = "alchemy"
  DungeonsForeverDB.prof.autoRoute = false
  PF.Toggle(slug)
  local fu = followEntry(slug)
  ck("★ 入口打开 HUD（跟随激活且窗口显示）",
     PF.IsActive(slug) == true and PF.f ~= nil and PF.f.__shown == true,
     tostring(PF.IsActive(slug)))
  ck("★ 跟随状态落存档（含路线指纹）", fu ~= nil and fu.rkey ~= nil, fu and fu.rkey)
  ck("★★ 固定模式：路线指纹 = fixed 前缀",
     fu ~= nil and tostring(fu.rkey):sub(1, 6) == "fixed:", fu and fu.rkey)
  ck("★★ 固定模式：段标为「固定路线 · 段落 x / N」，N = 固定路线段数",
     segText():find("固定路线", 1, true) ~= nil
     and segText():find("段落", 1, true) ~= nil
     and segText():find("/ " .. tostring(#(LV[slug].steps)), 1, true) ~= nil,
     segText() .. "  （固定段数 " .. tostring(#(LV[slug].steps)) .. "）")
  local fixedCard = cardName()
  ck("★ 固定模式：段卡画出了配方（不是空卡）", fixedCard ~= "", fixedCard)

  -- ---------- 阶段 1b：固定路线按「目标等级」裁剪（2026-10-11 用户：
  --   「hud 固定路线显示也需要 根据我设置等级 显示」） ----------
  --   专业页 RowsLeveling 走 ClipFixedSteps(lv.steps, PD.LvTarget())；HUD 原先直接吃全量
  --   lv.steps（1–300）⇒ 段标分母 / 购物清单 / 完成判定都与专业页对不上。
  do
    local function clipExpect(steps, target)
      if not target or target >= 300 then return steps end
      local out = {}
      for _, st in ipairs(steps or {}) do
        local a, b = st[1], st[2]
        if a > target then break end
        local nb, nq = math.min(b, target), st[4] or 0
        if b > target then
          nq = math.max(1, math.ceil(nq * (target - a) / (b - a) - 1e-9))
        end
        out[#out + 1] = { a, nb, st[3], nq }
      end
      return out
    end
    -- 验证器：解析 HUD 段标里的「/ N」，N 必须 = 裁剪后段数
    local function segN()
      return tonumber(segText():match("段落 %d+ / (%d+)") or "")
    end
    -- 全量 vs 裁剪 对照（alchemy 末段 2329–2331 ⇒ 目标 100 应落在若干段之后）
    local fullN = #(LV[slug].steps)
    local targets = { 100, 150, 200 }
    local okAll, detail = true, {}
    PF.showShop = true            -- 购物清单要打开才读得到表头「共N种」
    for _, t in ipairs(targets) do
      DungeonsForeverDB.prof.lvTarget = DungeonsForeverDB.prof.lvTarget or {}
      DungeonsForeverDB.prof.lvTarget[slug] = t
      PF.RefreshRoute(slug)                 -- 即时推送（专业页 ApplyTarget 同款调用）
      fu = followEntry(slug)
      local want = #clipExpect(LV[slug].steps, t)
      local got = segN()
      -- 购物清单「共N种」也要跟着目标变（段少了 ⇒ 材料只减不增）
      local headN = tonumber(((PF.f and PF.f.shop and PF.f.shop.head
                               and PF.f.shop.head.__text) or ""):match("共(%d+)种") or "")
      detail[#detail + 1] = ("目标%d → %s(期望 %d) 购物%d种"):format(
        t, tostring(got), want, tonumber(headN) or -1)
      if got ~= want or want >= fullN or headN == nil then okAll = false end
    end
    PF.showShop = false
    ck("★★ 固定路线按目标等级裁剪（段标分母 = 裁剪后段数，且严格短于全量 300）",
       okAll and #LV[slug].steps > 0, table.concat(detail, " | ")
       .. ("  全量 " .. tostring(fullN)))
    -- 目标 >= 300 ⇒ 回到全量（不与旧行为回归）
    DungeonsForeverDB.prof.lvTarget[slug] = nil
    PF.RefreshRoute(slug)
    ck("★★ 目标 = 300/全程 ⇒ 段数回到全量（不误裁）",
       segN() == fullN, tostring(segN()) .. " 期望 " .. tostring(fullN))
    -- 指针不得越界：目标调到 80 之后，step 必须夹在裁剪后的段数内
    DungeonsForeverDB.prof.lvTarget[slug] = 80
    fu.skill = 5
    PF.RefreshRoute(slug)
    fu = followEntry(slug)
    local n80 = #clipExpect(LV[slug].steps, 80)
    ck("★★ 目标改小后段落指针自动重推且不越界（step <= N+1）",
       (fu.step or 1) >= 1 and (fu.step or 1) <= n80 + 1,
       "step=" .. tostring(fu.step) .. " N=" .. tostring(n80))
    DungeonsForeverDB.prof.lvTarget[slug] = nil
    PF.RefreshRoute(slug)
  end

  -- ---------- 阶段 2：设置开但没装 Auctionator → 回落固定 ----------
  DungeonsForeverDB.prof.autoRoute = true
  if RA and RA.Invalidate then RA.Invalidate() end
  PF.Sync(); PF.Paint()
  fu = followEntry(slug)
  ck("★★ 自动开着但无 Auctionator → 回落固定路线（指纹仍 fixed / 段标仍「固定路线」）",
     tostring(fu and fu.rkey):sub(1, 6) == "fixed:"
     and segText():find("固定路线", 1, true) ~= nil,
     tostring(fu and fu.rkey) .. " | " .. segText())

  -- ---------- 阶段 2b：装了 Auctionator 但一条价格都没有（未扫描）→ 也必须回落固定 ----------
  Auctionator = { API = { v1 = {
    GetAuctionPriceByItemID = function(caller, id) return nil end,
  } } }
  ck("★ Auctionator 桩就位但无价（RA.Available 真 / 无价格数据）",
     RA.Available() == true)
  if RA and RA.Invalidate then RA.Invalidate() end
  PF.Sync(); PF.Paint()
  fu = followEntry(slug)
  do
    local resN = RA.Get(slug, optsFor(fu and fu.skill))
    ck("★ 无价快照 → RA 结果 priced=false（本阶段前提）",
       resN == nil or resN.priced ~= true, resN and tostring(resN.priced))
  end
  ck("★★ 自动有 Auctionator 但没价格数据 → 仍回落固定路线（不回退成空页）",
     tostring(fu and fu.rkey):sub(1, 6) == "fixed:"
     and segText():find("固定路线", 1, true) ~= nil,
     tostring(fu and fu.rkey) .. " | " .. segText())

  -- ---------- 阶段 3：装上 Auctionator → 切自动路线 ----------
  Auctionator = { API = { v1 = {
    GetAuctionPriceByItemID = function(caller, id) return 1000 end,
  } } }
  ck("★ Auctionator 桩就位（RA.Available 为真）", RA.Available() == true)
  if RA and RA.Invalidate then RA.Invalidate() end
  PF.Sync(); PF.Paint()
  fu = followEntry(slug)
  local resA = RA.Get(slug, optsFor(fu and fu.skill))
  ck("★ 自动路线算得出结果且有价（本阶段前提）",
     resA ~= nil and resA.priced == true and #(resA.steps or {}) > 0,
     resA and ("段数 " .. tostring(#resA.steps) .. " priced=" .. tostring(resA.priced)))
  ck("★★ 装 Auctionator 后 HUD 切成自动路线（指纹 = auto 前缀）",
     fu ~= nil and tostring(fu.rkey):sub(1, 5) == "auto:", fu and fu.rkey)
  do
    local vi = math.max(1, math.min(#(resA.steps or {}), (fu.step or 1) + (PF.view or 0)))
    local want = "自动计算 · 段落 " .. tostring(vi) .. " / " .. tostring(#resA.steps)
    ck("★★ 自动模式段标与自动路线段数逐字对齐（数据真换了源，不只是标签）",
       resA ~= nil and segText() == want, segText() .. "  vs  " .. want)
  end
  ck("★★ 自动路线 ≠ 固定路线（价格驱动，路线内容确实不同）",
     resA ~= nil and (#resA.steps ~= #(LV[slug].steps)
        or (resA.steps[1] and resA.steps[1][3] ~= LV[slug].steps[1][3])),
     tostring(resA and #resA.steps) .. " / " .. tostring(#LV[slug].steps))

  -- 段指针按自动路线推导：把技能抬到 150，Sync 后 step 必须落在自动路线的对应段
  do
    fu.skill = 150
    PF.Sync(); PF.Paint()
    local resB = RA.Get(slug, optsFor(150))
    local want = derivedOf(resB and resB.steps or {}, 150)
    ck("★★ 段落指针按自动路线推导（技能 150 → 第一段「上限 > 150」的段）",
       fu.step == want and tostring(fu.rkey):sub(1, 5) == "auto:",
       "step=" .. tostring(fu.step) .. " 期望 " .. tostring(want))
  end

  -- 浏览偏移夹在自动路线的段数内
  do
    local n = #(resA.steps or {})
    local v0 = PF.view or 0
    PF.Skip()
    local v1 = PF.view or 0
    for _ = 1, n + 4 do PF.Skip() end
    local vmax = PF.view or 0
    for _ = 1, n + 8 do PF.Prev() end
    local vmin = PF.view or 0
    ck("★★ 下一步 / 上一步 夹在自动路线的段数内（浏览偏移不越界）",
       v1 > v0 and vmax <= n - (fu.step or 1) + 1 and vmin >= -((fu.step or 1) - 1),
       tostring(v0) .. "/" .. tostring(v1) .. " max=" .. tostring(vmax)
       .. " min=" .. tostring(vmin) .. " 段数=" .. tostring(n))
    PF.view = 0; PF.Paint()
  end

  -- 购物清单：表头「共 N 种」必须等于「自动路线现算」的去重材料种数（数据真来自自动路线）
  do
    PF.showShop = true
    PF.Paint()
    local head = (PF.f.shop and PF.f.shop.head and PF.f.shop.head.__text) or ""
    local got = tonumber(head:match("共(%d+)种") or "")
    -- 期望值：从当前段起到末尾，按「配方表 + rinfo 合并」的去重材料 id 数（复刻 shopList 的选择口径）
    local rm = {}
    local rr = TF_NS.ProfRecipes[slug]
    for _, r in ipairs((rr and rr.rows) or {}) do rm[r[1]] = r end
    for sp, ri in pairs(LV[slug].rinfo or {}) do if not rm[sp] then rm[sp] = ri end end
    local resC = RA.Get(slug, optsFor(fu and fu.skill))
    local seen, want = {}, 0
    for i = (fu.step or 1), #(resC.steps or {}) do
      local rec = rm[resC.steps[i][3]]
      local mats = rec and (rec[12] or rec.mats)
      if mats then
        for _, m in ipairs(mats) do
          if not seen[m[1]] then seen[m[1]] = true; want = want + 1 end
        end
      end
    end
    ck("★★ 自动模式购物清单 = 自动路线现算（材料种数逐字对齐）",
       got ~= nil and got > 0 and got == want,
       "HUD " .. tostring(got) .. " / 期望 " .. tostring(want) .. " | " .. head)
    PF.showShop = false
    PF.Paint()
  end

  -- ---------- 阶段 4：关掉自动 → 回到固定路线（实时生效，不需要重载） ----------
  DungeonsForeverDB.prof.autoRoute = false
  if RA and RA.Invalidate then RA.Invalidate() end
  PF.Sync(); PF.Paint()
  fu = followEntry(slug)
  ck("★★ 关掉自动路线 → HUD 立刻回固定路线（无需重载；指纹回 fixed）",
     tostring(fu and fu.rkey):sub(1, 6) == "fixed:"
     and segText():find("固定路线", 1, true) ~= nil,
     tostring(fu and fu.rkey) .. " | " .. segText())

  -- ---------- 阶段 5：rinfo 并入（附魔路线大量引用 rinfo-only 法术） ----------
  do
    local PF_OK, PL_OK = false, false
    local esteps = LV.enchanting and LV.enchanting.steps
    local rr = TF_NS.ProfRecipes and TF_NS.ProfRecipes.enchanting
    local inRows, rinfo = {}, (LV.enchanting and LV.enchanting.rinfo) or {}
    for _, r in ipairs((rr and rr.rows) or {}) do inRows[r[1]] = true end
    local onlyRinfo = 0
    for _, s in ipairs(esteps or {}) do
      if not inRows[s[3]] and rinfo[s[3]] then onlyRinfo = onlyRinfo + 1 end
    end
    ck("★ 附魔路线确有 rinfo-only 段（本阶段前提 >= 5 段）", onlyRinfo >= 5, onlyRinfo)
    PF.Toggle("enchanting")
    local fu2 = followEntry("enchanting")
    ck("★ 切到附魔专业，HUD 跟随切过去", fu2 ~= nil and fu2.slug == "enchanting")
    if fu2 and esteps then
      local missing = 0
      for i = 1, #esteps do
        fu2.step = i
        PF.view = 0
        PF.Paint()
        local mh = PF.f.card.matHead
        if mh and mh.__shown == true then missing = missing + 1 end
      end
      ck("★★ 附魔全部段都能取到材料（rinfo 已并入配方查找表；旧写法 11 段显示「材料未收录」）",
         missing == 0, "缺材料的段数 " .. tostring(missing) .. " / " .. tostring(#esteps))
      fu2.step = 1
      PF.Paint()
    end
  end

  -- ---------- 阶段 6：购物清单「已备齐」药丸（★ 实机 25 连崩的触发分支） ----------
  -- 背景：pill(..., Unpack(C_OK), 0.5) 里 Unpack 处于**非末位实参**，Lua 只展开首值
  --      ⇒ g 收到 0.5、b 为 nil ⇒ PillBaseCol 预混 b*a2 直接「算术运算 nil」崩。
  --      只在 row.missing <= 0（已备齐）时触发 ⇒ 离线桩无 GetItemCount、Have() 恒 0
  --      ⇒ 该分支历次零覆盖。本阶段塞满背包把这条分支逼出来。
  do
    PF.showShop = false
    PF.Paint()
    PF.Toggle("alchemy")              -- 附魔阶段跑完，切回炼金
    local fu3 = followEntry("alchemy")
    if fu3 and fu3.hidden then PF.Toggle("alchemy") end
    fu3 = followEntry("alchemy")
    GetItemCount = function(id, includeBank) return 99999 end   -- ★ 满背包 → 全部「已备齐」
    C_Item = nil
    PF.showShop = true
    local ok, err = pcall(PF.Paint)
    ck("★★ 购物清单「已备齐」药丸不崩（Unpack 非末位实参 → b=nil 算术崩，实机 25 连报）",
       ok, ok and "" or tostring(err):sub(1, 160))
    -- 真画出绿丸：在 f.shop 的子件里能找到「已备齐」文案（绑不到就是分支没走到）
    local want = TF_NS.L["已备齐"]
    local hit = 0
    for _, c in ipairs(PF.f.shop.__children or {}) do
      if c.__text == want then hit = hit + 1 end
    end
    -- ★ 这条同时兜住「崩在第一行」：变异时只有第 1 行来得及 SetText，hit 停在 1。
    ck("★★ 已备齐分支全行画完（不是崩在第一行 / 也不是分支没走到而假绿）", hit >= 5,
       "命中 " .. tostring(hit) .. " 行")
    -- ★ 底色必须真是「C_OK 按 a2=0.5 预混」，而不是首值兜底把 0.5 塞进 g。
    --   直售丸走 a2=0.9，与本式不同值 ⇒ 不共享命中。
    local function pillBase()
      local l2 = (TF_NS.huiTheme == "hui" and TF_NS.hui
                  and TF_NS.hui.layer and TF_NS.hui.layer.L2) or nil
      if l2 then
        return 0.04 + 0.96 * (l2[1] or 0), 0.04 + 0.96 * (l2[2] or 0),
               0.04 + 0.96 * (l2[3] or 0)
      end
      return 0, 0, 0
    end
    local br, bgs, bbs = pillBase()
    local a2 = 0.5
    local wr = 0.27 * a2 + br * (1 - a2)
    local wg = 0.75 * a2 + bgs * (1 - a2)
    local wb = 0.45 * a2 + bbs * (1 - a2)
    local matched = 0
    for _, c in ipairs(PF.f.shop.__children or {}) do
      local v = c.__vc
      if v and v[4] == 0.99 and math.abs(v[1] - wr) < 1e-9
         and math.abs(v[2] - wg) < 1e-9 and math.abs(v[3] - wb) < 1e-9 then
        matched = matched + 1
      end
    end
    ck("★★ 已备齐绿丸底色 = C_OK 按 a2=0.5 预混（Unpack 首值兜底会把 0.5 塞进 g）",
       matched > 0, "对上 " .. tostring(matched) .. " 段")
    PF.showShop = false
    pcall(PF.Paint)
  end

  -- ---------- 阶段 7：「只显示缺失」开关（2026-10-11 用户） ----------
  -- 开关 = 表头右侧 CheckButton；开 = 滤掉已备齐行；一键导入始终全量（只动渲染层）。
  do
    PF.Toggle("alchemy")
    if followEntry("alchemy") and followEntry("alchemy").hidden then PF.Toggle("alchemy") end
    C_Item = nil
    GetItemCount = nil                 -- 空背包：全部「缺N」
    DungeonsForeverDB.prof.shopOnlyMiss = nil
    PF.showShop = true
    pcall(PF.Paint)
    local function headText() return (PF.f.shop.head and PF.f.shop.head.__text) or "" end
    local function headN() return tonumber(headText():match("共(%d+)种") or "") end
    local tog = PF.f.shop.missTog
    -- ★ 点击必须包 pcall：开关的 OnClick 会直接 PF.Paint()，产品一旦在这条路径上崩，
    --   不包的话整个 SCRIPT 抛出去 ⇒ 连 return out 都走不到 ⇒ 一条 FAIL 都不输出
    --   （= PROF_PITFALLS 的「断言段自己不许炸」，会让非恒真探针误判白测）。
    local lastClickErr = nil
    local function click()
      local fn = tog and tog.__scripts and tog.__scripts.OnClick
      if not fn then return false end
      local ok, err = pcall(fn, tog)
      if not ok then lastClickErr = tostring(err) end
      return ok
    end

    ck("★ 表头文案已改短（「购物清单 · 共N种」，不再带「从当前段累计到 300，含银行」）",
       headText():find(TF_NS.L["购物清单"], 1, true) == 1
       and headText():find("从当前段累计", 1, true) == nil
       and headText():find("种", 1, true) ~= nil,
       headText())
    ck("★ 开关建在表头右侧（CheckButton 挂 f.shop，带 OnClick）",
       tog ~= nil and tog.__scripts ~= nil and tog.__scripts.OnClick ~= nil)

    -- ★★ 开关左侧的文字标签（2026-10-11 用户：「只显示缺失的这个开关，左边写上文字“仅显示缺失”」）。
    --   动态只断「对象存在 + 文字是 L["仅显示缺失"]」（桩只记 __text）；
    --   「挂父帧 / 右对齐 / 锚在开关左缘」三条靠下面的静态断言钉死
    --   —— 桩的 CreateFontString 既不记 __parent 也不记 JustifyH，动态断这两项会是恒真白测。
    local lab = PF.f.shop.missLab
    ck("★★ 开关左侧有文字标签，文案 = L[\"仅显示缺失\"]（不是旧键「只显示缺失」）",
       lab ~= nil and tostring(lab.__text) == tostring(TF_NS.L["仅显示缺失"]),
       "text=" .. tostring(lab and lab.__text))

    -- 空背包 ⇒ 全缺：开/关计数必须一致（只该滤「已备齐」，不许误滤）
    local nOff = headN()
    local ok1 = click()
    local nOn = headN()
    ck("★★ 空背包下 开/关 计数一致（只滤已备齐，不误滤缺料行）",
       ok1 and DungeonsForeverDB.prof.shopOnlyMiss == true and nOn == nOff and (nOff or 0) > 0,
       "关 " .. tostring(nOff) .. " 开 " .. tostring(nOn) .. " | " .. headText()
       .. (ok1 and "" or (" ERR " .. tostring(lastClickErr):sub(1, 130))))

    -- 满背包 ⇒ 全已备齐：开 = 0 行，关 = 全量
    GetItemCount = function(id, bank) return 99999 end
    click()                                  -- 关（回全量）
    local okOff, errOff = pcall(PF.Paint)
    local nFullOff = headN()
    DungeonsForeverDB.prof.shopOnlyMiss = true
    local okPaint, errPaint = pcall(PF.Paint)
    local nFullOn = headN()
    ck("★★ 满背包 + 开关开 → 计数归零且不崩（已备齐全被滤掉；关=全量）",
       okOff and okPaint and nFullOn == 0 and (nFullOff or 0) > 0,
       "关 " .. tostring(nFullOff) .. " 开 " .. tostring(nFullOn)
       .. ((okOff and okPaint) and "" or (" ERR " .. tostring(errOff or errPaint):sub(1, 130))))

    -- ★★ 用户报的 bug（2026-10-11）：「开关一开、材料全备齐 ⇒ 永远点不开购物清单」。
    --   根因 n == 0 走 else f.shop:Hide()。空清单也必须把面板打开 + 显示灰字说明。
    local empTxt = (PF.f.shop.empty and PF.f.shop.empty.__text) or ""
    ck("★★ 满背包 + 开关开：空清单也把面板打开（不是 Hide；用户报的「永远点不开」）",
       okPaint and PF.f.shop.__shown == true and PF.f.shop.empty ~= nil,
       "shown=" .. tostring(PF.f.shop.__shown))
    ck("★★ 满背包 + 开关开：空清单显示灰字「所有物品已备齐」",
       tostring(empTxt) == TF_NS.L["所有物品已备齐"] and PF.f.shop.empty.__shown == true,
       "「" .. tostring(empTxt) .. "」")

    -- 再关回来：计数必须复原（开关可逆，不是单向丢行）
    DungeonsForeverDB.prof.shopOnlyMiss = false
    local okBack, errBack = pcall(PF.Paint)
    ck("★★ 开关关回来 → 计数复原（可逆，不是单向丢行；顺带证明渲染路径不崩）",
       okBack and headN() == nFullOff,
       "关 " .. tostring(headN()) .. " 期望 " .. tostring(nFullOff)
       .. (okBack and "" or (" ERR " .. tostring(errBack):sub(1, 130))))
    ck("★★ 关回来后空清单灰字收起（有行就不该再显示提示）",
       PF.f.shop.empty.__shown == false, "shown=" .. tostring(PF.f.shop.empty.__shown))

    -- 本来是「无材料」（当前段之后没有配方材料）时，空清单也应打开且文案不同
    DungeonsForeverDB.prof.shopOnlyMiss = true
    local okNoMat = pcall(PF.Paint)
    ck("★ 空清单提示与开关状态无关（关开关也照常打开面板，不隐藏）",
       okNoMat and PF.f.shop.__shown == true, "shown=" .. tostring(PF.f.shop.__shown))

    DungeonsForeverDB.prof.shopOnlyMiss = nil
    PF.showShop = false
    pcall(PF.Paint)      -- ★ 也要包：空背包下清开关会再画一遍（产品若崩不该拖垮整段）
  end

  return out
end)()
'''
    res = lua.eval(SCRIPT)
    for i in range(1, len(res) + 1):
        item = res[i]
        ck(item[1], item[2] == 1, item[3])

    # ---------- 静态断言（源码口径） ----------
    src = open(os.path.join(addon, 'Core', 'ProfFollow.lua'), encoding='utf-8',
               errors='replace').read().replace('\r\n', '\n')
    live = '\n'.join(l.split('--')[0] for l in src.split('\n'))
    ck("★ 静态：routeFor 存在，自动门禁含 RA.Available()，固定分支按目标等级裁剪",
       'local function routeFor(slug, skill)' in src
       and 'PD.Setting("autoRoute") and RA and RA.Available()' in src
       # 2026-10-11：固定分支不再直接吃全量 lv.steps，改为走 clipFixedSteps(lv.steps, target)
       and 'return "fixed", clipFixedSteps(lv and lv.steps or nil, routeTarget(slug))' in src
       and 'local function clipFixedSteps(steps, target)' in src)
    ck("★★ 静态：HUD 的固定路线裁剪口径与专业页 ClipFixedSteps 逐字一致（同一套折算公式）",
       'nq = math.max(1, math.ceil(nq * (target - a) / (b - a) - 1e-9))' in src
       and 'if not target or target >= 300 then return steps end' in src
       and 'out[#out + 1] = { a, nb, st[3], nq, _clip = isClip or nil }' in src)
    ck("★ 静态：routeFor 的 opts 与专业页逐项一致（起点 / 三个过滤 / 目标）",
       src.count('PD.Setting("autoFromCurrent")') >= 1
       and src.count('PD.Setting("autoOnlyAH")') >= 1
       and src.count('PD.Setting("autoNoFormula")') >= 1
       and src.count('PD.Setting("autoLearnedOnly")') >= 1
       and 'target = routeTarget(slug)' in src)
    ck("★★ 静态：移动路径全部走 routeFor（不再直接读 LV[slug].steps）",
       '#lv.steps' not in live and 'LV[s.slug]' not in live
       and live.count('routeFor(s.slug, s.skill)') == 4   # Prev / Skip / OnMouseWheel / shopList
       and 'local mode, steps = routeFor(slug, s.skill)' in live)
    ck("★★ 静态：段标带模式前缀（复用既有 L 键，未新增文案）",
       '((mode == "auto") and L["自动计算"] or L["固定路线"])' in live
       and 'format(L["段落 %d / %d"], vi, #steps)' in live)
    ck("★★ 静态：recMap 并入 rinfo，取数走 recMats / recItem（兼容 rinfo 命名字段）",
       'if lv and type(lv.rinfo) == "table" then' in live
       and 'local function recMats(rec) return rec and (rec[12] or rec.mats) or nil end' in live
       and 'local function recItem(rec) return rec and (rec[2] or rec.makes) or nil end' in live
       and live.count('recMats(rec)') >= 2)
    ck("★ 静态：Sync 按「模式 + 内容」指纹重推指针",
       'local key = routeKey(mode, steps)' in live and 'if key ~= s.rkey then' in live)
    # ★★ 开关左侧标签的三条硬约束（2026-10-11 用户：「只显示缺失的这个开关，左边写上文字“仅显示缺失”」）。
    #   ① 挂 f.shop 父帧 —— 挂开关上会被 ReskinToggle 的 PurgeNative 当「非自建子件」Hide 掉；
    #   ② 右对齐 —— 面板随购物列加宽时标签要贴着开关走；
    #   ③ 锚在开关**左**缘（RIGHT→开关 LEFT, -4）—— 锚错成 RIGHT 就跑到开关右边了。
    ck("★★ 静态：标签挂 f.shop 父帧（挂开关上会被 ReskinToggle 的 PurgeNative 隐藏 = 实机看不到）",
       'f.shop.missLab = MakeFS(f.shop, 14, C_TEXT, "RIGHT")' in live)
    ck("★★ 静态：标签锚在开关左缘（RIGHT→missTog LEFT, -4 ⇒ 真在「左边」）",
       'f.shop.missLab:SetPoint("RIGHT", f.shop.missTog, "LEFT", -4, 0)' in live)
    ck("★★ 静态：标签文案走 L 键「仅显示缺失」，且不再引用旧键「只显示缺失」",
       'f.shop.missLab:SetText(L["仅显示缺失"])' in src
       and 'L["只显示缺失"]' not in src)
    ck("★★ 静态：表头让位量按标签实测宽现算（写死会在 enUS 压表头）",
       'local SHOP_TOG_W = labW + 48' in live
       and 'pcall(PDw.TextW, L["仅显示缺失"], 14)' in live)

    print('=' * 56)
    print('冒烟完成：失败 %d 条' % len(FAILS))
    for f in FAILS:
        print('  ✗ %s' % f)
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
