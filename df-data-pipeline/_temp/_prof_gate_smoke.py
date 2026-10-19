# -*- coding: utf-8 -*-
"""独立冒烟（2026-10-09）：专业页「大列表分帧 + 主界面顶部进度条」运行时验证。

背景两条，都让共享 harness 覆盖不到这条路径：
  ① 共享 harness 的动态块被并行会话的团本页在途改动提前崩掉（wallLabels nil），
     专业页动态断言跑不到（同一原因促成了 _prof_search_smoke.py）；
  ② 共用桩的 `C_Timer.After` 是**空实现** → 分帧泵永远不会被调到，行池停在半截
     （`#PD.rows > 0` 这类断言会假绿）。
本冒烟自建驱动链 + **可手动抽干的泵**：既能断言「边建边推进」的中间态，
也能在抽干后拿到完整的行池。只读产品文件，不写任何产品文件。

覆盖：
  ① 强制分帧 → 进度条亮、分母 = 还没建的行数、done 从 0 起步、条与胶囊都上屏；
  ② 抽一批泵 → 0 < done < total 且条仍亮着（真的分批推进，不是建完才显示）；
  ③ 抽干 → 条收工（on=false / 隐藏）、行池补齐到分母、行帧有落点；
  ④ 阈值内走快速通道 → 当场建完、待建表清空、进度条全程不亮；
  ⑤ 含间距行的页签 → gap 也入队、抽干后行池不留空洞、gap 帧建出来即隐藏
     （配方页的 gap 永远落在 ROW_CAP 之外，单靠 ①③ 覆盖不到 gap 分支）；
  ⑥ 条挂在主界面（与掉落页同一根，锚 TOPRIGHT/-8）。
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # 复用 T.STUB / ADDON / TOC
from lupa import lua51

FAILS = []


def ck(name, ok, extra=''):
    print('  [%s] %s%s' % ('OK ' if ok else 'FAIL', name,
                           ('  [%s]' % extra) if extra != '' else ''))
    if not ok:
        FAILS.append(name)


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    toc = open(os.path.join(addon, os.path.basename(D.TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]

    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(D.T.STUB)
    # ★ 泵改为「只排队、不自动跑」：由本脚本显式抽干，才能观察中间态。
    lua.execute('PUMPS = {}')
    lua.execute('C_Timer = { After = function(t, fn) '
                'PUMPS[#PUMPS + 1] = fn end }')
    lua.execute('CTIMER_REF = C_Timer')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
                'local a, b, c, d = orig(...); return a, b, c, 16001, e end end')
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
  -- 挑「配方行最多」的那个专业，分幀分母才够大
  local best, bestN = nil, -1
  for _, s in ipairs(TF_NS.ProfData.order or {}) do
    PD.Show(s); PD.SetTab("recipe")
    local n = #(PD.specs or {})
    if n > bestN then best, bestN = s, n end
  end
  PD.bestSlug, PD.bestN = best, bestN
end
'''
    lua.execute(DRIVER)

    SCRIPT = r'''
(function()
  local PD = TF_NS.ProfModule
  local DGm = TF_NS.ProfHost.DG
  local out = {}
  local function ck(name, ok, extra)
    out[#out + 1] = { name, ok and 1 or 0, extra or "" }
  end
  local function clearPool()
    for i = #PD.rows, 1, -1 do PD.rows[i]:Hide() end
    PD.rows = {}
  end
  local function drain(cap)
    local n = 0
    while #PUMPS > 0 and n < (cap or 100000) do
      local fn = table.remove(PUMPS, 1)
      fn()
      n = n + 1
    end
    return n
  end
  -- 归零分帧器：`DG.stepping` 是个自锁闩 —— 真机上 pump 下一帧自己跑掉就复位，
  -- 桩里 pump 只排队不自动跑，一旦有渲染排过队它就卡在 true，之后所有 RunSteps
  -- 都 `if DG.stepping then return end` 直接返回（泵再也排不上）。
  local function settle()
    DGm.stepping = false
    DGm.pendingSteps = {}
    PUMPS = {}
  end

  -- 关掉「物品到货重扫」排程：泵队列里只剩分帧回调，抽干计数才干净
  PD.sweeping = true
  -- 驱动链（13 个专业各渲染一遍）已经留下半截泵，先抽干 + 归零。
  drain()
  settle()
  PD.__pendRows = {}
  DGm.Gate.minSteps = 0            -- 多小都亮（正式 24）
  PD.ROW_SYNC_MAX = 0              -- 一律走分帧（正式 20）

  -- ---------- ① 强制分帧：进度条亮起 ----------
  PD.Show(PD.bestSlug); PD.SetTab("recipe")
  clearPool()
  settle()
  PD.Render()
  local total = DGm.Gate.total
  local pend0 = #PD.__pendRows
  ck('① 大页强制分帧：进度条亮起，分母 = 还没建的行数（只增不减）',
     DGm.Gate.on == true and total > 100 and total == pend0,
     'total=' .. tostring(total) .. ' pend=' .. tostring(pend0)
     .. ' specs=' .. tostring(#(PD.specs or {})))
  ck('① 起点 done = 0，条与右下胶囊都真的上屏',
     DGm.Gate.done == 0
     and DGm.Gate.bar ~= nil and DGm.Gate.bar.__shown == true
     and DGm.Gate.pill ~= nil and DGm.Gate.pill.__shown == true)
  -- ★ 断言自己不许炸：条没被建出来（Gate 没 Begin）时下面这些必须**报 FAIL**，
  --   而不是 `index field 'bar' (a nil value)` 把整段 Lua 断言一起崩掉 ——
  --   崩掉 = 一条 FAIL 都不输出，非恒真探针会把「注入有效」误判成「白测」。
  local bar = DGm.Gate.bar or {}
  ck('① 条挂在主界面（与掉落页同一根：TOPLEFT/TOPRIGHT 贴主窗口上缘）',
     bar.__pts ~= nil and bar.__pts[1] == "TOPRIGHT"
     and bar.__pts[4] == -8)
  ck('① 此刻行池还是空的（渲染那一帧只算版式，没同步建帧）',
     #PD.rows == 0)

  -- ---------- ② 抽一批泵：真的分批推进 ----------
  local pumped = 0
  while #PUMPS > 0 and pumped < 60 do
    local fn = table.remove(PUMPS, 1)
    fn()
    pumped = pumped + 1
    if DGm.Gate.done > 0 and DGm.Gate.done < DGm.Gate.total then break end
  end
  ck('② 抽一批泵后 done 严格落在 (0, total) —— 分帧真的在推进',
     DGm.Gate.done > 0 and DGm.Gate.done < total,
     'done=' .. tostring(DGm.Gate.done) .. ' / ' .. tostring(total)
     .. '，pump 回调 ' .. tostring(pumped) .. ' 次')
  ck('② 推进期间进度条仍然亮着（不是建完才显示），行池与 done 同步长',
     DGm.Gate.on == true
     and DGm.Gate.bar ~= nil and DGm.Gate.bar.__shown == true
     and #PD.rows == DGm.Gate.done,
     '#rows=' .. tostring(#PD.rows) .. ' done=' .. tostring(DGm.Gate.done))

  -- ---------- ③ 抽干：收工 + 行池补齐 ----------
  drain()
  ck('③ 抽干后进度条收工（on=false、条与胶囊都隐藏）',
     DGm.Gate.on == false
     and DGm.Gate.bar ~= nil and DGm.Gate.bar.__shown == false
     and DGm.Gate.pill ~= nil and DGm.Gate.pill.__shown == false)
  ck('③ 抽干后行池补齐到分母（一条不漏、也没多建）',
     #PD.rows == total, '#rows=' .. tostring(#PD.rows) .. ' / ' .. tostring(total))
  ck('③ 抽干后待建表清空', #PD.__pendRows == 0, #PD.__pendRows)
  do
    local r1, r2 = PD.rows[1], PD.rows[#PD.rows]
    ck('③ 建出来的行有落点与尺寸（不是只 CreateFrame 没摆位）',
       r1 ~= nil and r1.__pts ~= nil and r1.__w ~= nil
       and r2 ~= nil and r2.__pts ~= nil)
    -- ★ 行池按索引取用：1..total 每个槽位都必须有帧，跳号会在池里留空洞
    --   （间距行入队被摘掉时「#PD.rows == total」照样成立，靠这条才抓得住）。
    local holes = 0
    for i = 1, total do if PD.rows[i] == nil then holes = holes + 1 end end
    ck('③ 行池按索引取用不留空洞（间距行也建出来占位）', holes == 0,
       'holes=' .. tostring(holes) .. ' / ' .. tostring(total))
  end

  -- ---------- ④ 阈值内走快速通道 ----------
  PD.ROW_SYNC_MAX = 1000           -- 阈值调高 = 一律走快速通道
  clearPool()
  settle()
  PD.Render()
  ck('④ 阈值内（量小）走快速通道：当场建完 + 待建表清空 + 进度条全程不亮',
     #PD.__pendRows == 0 and DGm.Gate.on == false
     and DGm.Gate.bar ~= nil and DGm.Gate.bar.__shown == false
     and #PD.rows == total,
     '#rows=' .. tostring(#PD.rows) .. ' / ' .. tostring(total)
     .. ' pend=' .. tostring(#PD.__pendRows))

  -- ---------- ⑤ 含间距行的页面也分帧：gap 一律入队（不跳号） ----------
  -- ★ 为什么单独一段：配方页的 gap 由 RowsRecipe 在「截断提示」处推，永远落在
  --   ROW_CAP**之外** ⇒ 配方页根本走不到 gap 分支（摘掉那半句也不会变红）。
  --   这里扫一遍别的页签，挑一张「可见范围里真有 gap」的列表来覆盖。
  --   ★ 挑页签的依据是 PD.specs（版式事实），不是待建表 —— 否则「gap 不入队」
  --     这条回潮会让 gTab 永远是 nil，下面的抽干断言整段跳过 ⇒ 反而证明不了它。
  PD.ROW_SYNC_MAX = 0
  local gTab, gSpecGap = nil, 0
  for _, t in ipairs({ "overview", "camp", "leveling", "gather", "legacy", "notes" }) do
    if PD.avail and PD.avail[t] then
      PD.Show(PD.bestSlug); PD.SetTab(t)
      clearPool(); settle(); PD.__pendRows = {}
      PD.Render()
      local sp = PD.specs or {}
      local lim = math.min(#sp, PD.ROW_CAP or 300)
      local q = 0
      for i = 1, lim do if sp[i] and sp[i].kind == "gap" then q = q + 1 end end
      if q > gSpecGap then gTab, gSpecGap = t, q end
      PD.__pendRows = {}; settle(); drain(); clearPool()
    end
  end
  ck('⑤ 存在「可见范围里有间距行」的页签（gap 分支真的能走到）',
     gTab ~= nil and gSpecGap >= 1,
     'tab=' .. tostring(gTab) .. ' specGap=' .. tostring(gSpecGap))
  if gTab then
    PD.Show(PD.bestSlug); PD.SetTab(gTab)
    clearPool(); settle(); PD.__pendRows = {}
    PD.Render()
    local total2 = DGm.Gate.total
    local qGap = 0
    for k = 1, #PD.__pendRows do
      if PD.__pendRows[k].gap then qGap = qGap + 1 end
    end
    ck('⑤ 间距行同样入队（分母含 gap，不是跳号只算配方行）',
       qGap == gSpecGap and total2 == #PD.__pendRows,
       'specs里的gap=' .. tostring(gSpecGap) .. ' 入队gap=' .. tostring(qGap)
       .. ' total=' .. tostring(total2) .. ' pend=' .. tostring(#PD.__pendRows))
    local holes2, gapFrames, gapShown = 0, 0, 0
    drain()
    for i = 1, total2 do
      local rf = PD.rows[i]
      if rf == nil then holes2 = holes2 + 1 end
      local sp = (PD.specs or {})[i]
      if sp and sp.kind == "gap" then
        gapFrames = gapFrames + 1
        if rf and rf.__shown == true then gapShown = gapShown + 1 end
      end
    end
    ck('⑤ 抽干后行池无空洞（gap 也建出来占位，索引不断号）', holes2 == 0,
       'holes=' .. tostring(holes2) .. ' / ' .. tostring(total2)
       .. '（tab=' .. tostring(gTab) .. '）')
    ck('⑤ 间距行的帧真的建出来了，且一律隐藏（与同步建帧路径同观感）',
       gapFrames >= 1 and gapShown == 0,
       'gapFrames=' .. tostring(gapFrames) .. ' shown=' .. tostring(gapShown))
  end

  -- 还原（本进程内的一波，不影响别的脚本）
  PD.ROW_SYNC_MAX = 20
  DGm.Gate.minSteps = 24
  PD.sweeping = false
  PUMPS = {}
  return out
end)()
'''
    # ★ 断言段自己崩了也必须变成一条 FAIL：崩掉 = 一条 FAIL 都不输出，
    #   非恒真探针会把「注入有效」误判成「白测」（2026-10-09 实测踩到）。
    try:
        res = lua.eval(SCRIPT)
    except Exception as e:
        ck('Lua 断言段未抛异常（分帧状态机不能把整段断言崩掉）', False,
           str(e)[:160])
        res = None
    if res is not None:
        for i in range(1, len(res) + 1):
            item = res[i]
            ck(item[1], item[2] == 1, item[3])

    print('=' * 56)
    print('冒烟完成：失败 %d 条' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
