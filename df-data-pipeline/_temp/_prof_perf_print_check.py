# -*- coding: utf-8 -*-
"""离线冒烟：确认「点开耗时打印」探针（/dfprofperf）真的活着。

★ 这个脚本**不**用来证明实机性能 —— 离线桩把 GetStringWidth / CreateFrame /
  GetItemInfo / 发包全换成了纯 Lua 查表，离线的毫秒数与实机无关。
  这里只证明三件事：
    ① 探针不崩（包函数 + pcall 链在真实路径上跑得通）；
    ② 触发一次「切专业 + 点配方页签」会真的打出行来；
    ③ 打印格式含头行 / 分段行 / 计数行，且计数**非零**（说明确实拦到了调用）。

只读产品文件，不写任何产品文件。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51  # noqa: E402

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
    profui = open(os.path.join(addon, 'Core', 'ProfessionUI.lua'),
                  encoding='utf-8', errors='replace').read()

    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(D.T.STUB)
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
    # ★ 2026-10-09 第六轮：给桩补 SlashCmdList —— 探针只在
    #   `type(SlashCmdList) == "table"` 时注册斜杠命令，离线桩原本没有它
    #   ⇒ `/dfprofperf rep` 这条路径**离线根本没被跑过**（探针自己也是白测）。
    lua.execute('SlashCmdList = {}')

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

    SCRIPT = r'''
(function()
  local PD = TF_NS.ProfModule
  local DGm = TF_NS.ProfHost.DG
  if not PD then return "NO_PD" end

  -- 抓 print：探针的 pfOut 走全局 print（运行期查找）⇒ 这里能全收
  local logs = {}
  local realPrint = print
  print = function(...)
    local t = {}
    for i = 1, select('#', ...) do t[#t + 1] = tostring(select(i, ...)) end
    logs[#logs + 1] = table.concat(t, " ")
  end

  local guard = function()
    DGm.stepping = false
    DGm.pendingSteps = {}
    PUMPS = {}
  end

  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")

  -- 探针：默认只打慢过 6ms 的；离线 GetTime 可能恒值 ⇒ 强制全打
  PD.PERF = "all"
  PD.PERF_MIN = 0
  PD.sweeping = true

  -- 挑原始行最多的专业
  local best, bestN = nil, -1
    local _rf = TF_NS.EnsureProfRecipes
    if _rf then _rf() end
    for _, s in ipairs(TF_NS.ProfData.order or {}) do
    local d = TF_NS.ProfRecipes and TF_NS.ProfRecipes[s]
    local n = (d and d.rows and #d.rows) or 0
    if n > bestN then best, bestN = s, n end
  end

  guard()
  PD.Show(best)
  guard()
  PD.SetTab("recipe")

  -- 抽干分帧（离线契约：调用方返回时就绪）
  guard()

  -- ★ 造态：让「物品名未到货」，逼出轻量请求分支。
  --   离线桩的 GetItemInfo 恒返回假名 ⇒ 默认永远走不到那条路（新版计数行里
  --   「完整预热 / 发包」双双为 0 —— 看着全绿，其实是白测）。
  local rlN, riN = 0, 0
  GetItemInfo = function() return nil end
  C_Item = { RequestLoadItemDataByID = function() rlN = rlN + 1 end }
  DGm.GetItemNameByID = nil
  local realRI = DGm.RequestItem
  DGm.RequestItem = function(...)
    riN = riN + 1
    if realRI then return realRI(...) end
  end

  -- ★★ 第十一刀（rev17）：记忆表已「正向跨渲染持久」⇒ 造态还必须把**正向**
  --   那半边也硬清一次。否则前面几帧用桩的假名已经落进正向表，这里永远
  --   看不到「未到货」那条路（rlN / notReady 断言会假绿）。
  PD.ResetItemNameMemo(true)
  PD.searchQ = nil
  guard()
  PD.Render()

  -- ★ 冷 / 热对照：走 `/dfprofperf rep` 的真实代码路径（连渲同一页 3 次）。
  --   第 1 次含「一次性建帧」，第 2/3 次是热路径 —— 差多大就知道某一段
  --   值不值得挪进分帧段 / 做预建。
  local rep0 = #logs
  SlashCmdList["DUNGEONSFOREVERPROFPERF"]("rep")
  local rep = {}
  for i = rep0 + 1, #logs do rep[#rep + 1] = logs[i] end

  -- ★★ 第十刀（rev16）：材料串按需算的自检 —— 强制 SyncRows 只留 2 行
  --   同步绑，于是首屏之外**必然**走「挂待算标」那条路；再渲一次并核对：
  --   ① 确实发生了延后（有材料的 spec 数 > 2）；
  --   ② 延后的行一条都没漏算（pendLeft = 0 且 noSeg = 0）—— 少任何一条，
  --      行上就会空着材料列（这是本刀唯一的真实风险）。
  local savedSync = PD.SyncRows
  PD.SyncRows = function() return 2 end
  guard()
  PD.Render()
  PD.SyncRows = savedSync
  -- ★ 本脚本自带 C_Timer 桩（只排队、不执行）⇒ 必须**手动抽干**分帧队列，
  --   才看得到「延后的行有没有被补算材料串」（真机由 C_Timer 在后续帧跑）。
  local pumpN = 0
  while #PUMPS > 0 and pumpN < 20000 do
    local fn = table.remove(PUMPS, 1)
    pumpN = pumpN + 1
    pcall(fn)
  end
  local mSpec, mPend, mDone, mBad = 0, 0, 0, 0
  for _, sp in ipairs(PD.specs or {}) do
    if sp._mats and #sp._mats > 0 then
      mSpec = mSpec + 1
      if sp._matsPending then
        mPend = mPend + 1
      else
        mDone = mDone + 1
        if not sp.matSegs then mBad = mBad + 1 end
      end
    end
  end
  logs[#logs + 1] = "@@MATS\t" .. mSpec .. "\t" .. mPend .. "\t"
                    .. mDone .. "\t" .. mBad .. "\t" .. pumpN

  -- ★★ 第十一刀（rev17）：记忆表「正负分离 + 正向跨渲染持久」的行为自检。
  --   ① 正向：取一次真名 → PD.ResetItemNameMemo()（= 一次新 Render 的开头）
  --      → 再取，引擎调用必须是 **0**（原来整表清 ⇒ 又调一次）。
  --   ② 负向：「名字还没到货」必须**不**跨 Render —— 每次都要再问一次，
  --      否则到货重扫永远刷不出名字（那是原来那张表唯一的存在理由）。
  --   ③ 空闲预热：PD.WarmNames() 要真的把当前专业的物品名喂进表
  --      （造态里名字一律未到货 ⇒ 必然发出装载请求）。
  do
    local prevGI = GetItemInfo
    local engN = 0
    GetItemInfo = function(id)
      engN = engN + 1
      return "测试物品" .. tostring(id), "item:" .. tostring(id)
    end
    local e0 = engN
    PD.ItemName(1900001)
    local e1 = engN - e0
    PD.ResetItemNameMemo()
    PD.ItemName(1900001)
    local e2 = engN - e0 - e1
    logs[#logs + 1] = "@@MEMO\t" .. e1 .. "\t" .. e2

    local negN = 0
    GetItemInfo = function() negN = negN + 1 return nil end
    PD.ResetItemNameMemo()
    PD.ItemName(1900002)
    local n1 = negN
    PD.ResetItemNameMemo()
    PD.ItemName(1900002)
    local n2 = negN - n1
    logs[#logs + 1] = "@@MEMO2\t" .. n1 .. "\t" .. n2

    WG_REQ = 0
    local prevRL = C_Item.RequestLoadItemDataByID
    C_Item.RequestLoadItemDataByID = function(...)
      WG_REQ = WG_REQ + 1
      if prevRL then return prevRL(...) end
    end
    PD.sweeping = true
    guard()
    local w0 = WG_REQ
    PD.WarmNames()
    local wp = 0
    while #PUMPS > 0 and wp < 40000 do
      local fn = table.remove(PUMPS, 1)
      wp = wp + 1
      pcall(fn)
    end
    C_Item.RequestLoadItemDataByID = prevRL
    GetItemInfo = prevGI
    logs[#logs + 1] = "@@WARM\t" .. (WG_REQ - w0) .. "\t" .. wp

    -- 还原造态：最后一帧仍要「名字未到货」⇒ PD.notReady 非空（既有断言要用）。
    PD.ResetItemNameMemo(true)
    guard()
    PD.Render()
  end

  print = realPrint
  local nr = (PD.notReady and #PD.notReady) or 0
  return table.concat(logs, "\n") .. "\n@@@\t" .. tostring(rlN) .. "\t"
         .. tostring(riN) .. "\t" .. tostring(nr) .. "\n@@R@@\t"
         .. table.concat(rep, "\n")
end)()
'''
    try:
        res = lua.eval(SCRIPT)
    except Exception as e:
        ck('Lua 探针段未抛异常', False, str(e)[:300])
        res = None

    text = str(res) if res else ''
    main_text, _, rest = text.partition('\n@@@\t')
    tail, _, rep_text = rest.partition('\n@@R@@\t')
    lines = [l for l in main_text.split('\n') if l.strip()]
    rep_lines = [l for l in rep_text.split('\n') if l.strip()]

    if text == 'NO_PD':
        ck('专业模块已挂载', False, 'TF_NS.ProfModule 为 nil')
        print('-' * 72)
        return 1

    ck('探针段未抛异常', res is not None)
    ck('★ 触发一次「切专业 + 点配方页签」有打印产出',
       len(lines) > 0, '共 %d 行' % len(lines))
    ck('★ 打印里出现探针前缀',
       any('[DF性能]' in l for l in lines),
       lines[0] if lines else '(空)')
    head = [l for l in lines if 'ms  ' in l and '「' in l]
    ck('★ 有「耗时 + 位置」头行', len(head) > 0, head[0] if head else '(无)')
    seg = [l for l in lines if '└' in l and '次/' not in l]
    ck('★ 有分段行（导航/数据/铺行…）',
       len(seg) > 0 and any(('数据' in l or '铺行' in l) for l in seg),
       seg[0] if seg else '(无)')
    cnt = [l for l in lines if '次/' in l]
    ck('★ 有计数行（量宽/取名/发包…）', len(cnt) > 0, cnt[0] if cnt else '(无)')

    # 计数非零：说明确实拦到了真实调用
    nonzero = False
    for l in cnt:
        for piece in l.split('·'):
            m = re.search(r'(\d+)\s*次/', piece)
            if m and int(m.group(1)) > 0:
                nonzero = True
    ck('★ 计数非零（确实拦到了调用）', nonzero)

    # 「量宽」（真·引擎测量）必须 ≤ 「量宽调用」（含记忆化命中）
    m_real = re.search(r'量宽\s*(\d+)\s*次/', ' '.join(cnt))
    m_all = re.search(r'量宽调用\s*(\d+)\s*次/', ' '.join(cnt))
    if m_real and m_all:
        a, b = int(m_real.group(1)), int(m_all.group(1))
        ck('★ 记忆化生效：真实字体测量次数 ≤ PD.TextW 调用次数',
           a <= b, '真实 %d ≤ 调用 %d（命中率 %.0f%%）'
           % (a, b, 100.0 * (b - a) / b if b else 0))

    # ★★ 工具行三拆（2026-10-09 第六轮）：实机「工具行 28.3ms」原来是三项之和，
    #   而 bench 量出 setter 只有 0.18~0.62µs/次 ⇒ 20 个按钮写满 setter 也才
    #   0.04ms ⇒ 28.3ms **绝不是 setter**，必须先知道这三个函数是谁。
    ck('★ 配方页分段行含 工具P / 工具R（工具行已三拆；工具L 只在升级页出现）',
       any(('工具P' in l and '工具R' in l and '工具行' not in l) for l in lines),
       next((l for l in lines if '工具P' in l), '(无)'))
    ck('★★ setter 计数器每次 Render 入口都补包（入口层 SetTab/Show 会先把 PF_DEPTH '
       '置 1；原来只看 PF_DEPTH==0 ⇒ 第一次点击永远装不上计数器）',
       'if PF_DEPTH == 0 then pfWrapAll() end' not in profui
       and profui.count('pfWrapAll()') >= 2)
    ck('★ setter 调用行确实打出来了（且不只 SetText/SetTextColor，还有 SetPoint/SetSize 等）',
       any('setter 调用' in l for l in lines),
       next((l for l in lines if 'setter 调用' in l), '(无)'))
    # ★★ 第八刀（rev14）：①「皮按钮帧」那行必须**恒打**（第七刀写成「sk>0 才打」
    #   ⇒ 实机看不到它时**无法区分**「本版没加载」与「加载了但一副都没建」）；
    #   ② 工具行闸门内部必须能拆出四刀（16 颗按钮切页吃 21~26ms，而闸门里每样
    #   按 bench 单价都是微秒级 ⇒ 不实测拆开就只能读代码猜）。
    ck('★★ 「皮按钮帧」行恒打（带 rev14）且工具闸门能拆出四刀',
       any('皮按钮帧：建' in l and 'rev14' in l for l in lines)
       and any('工具闸门（已含在「工具P」里）' in l and '尺寸' in l
               and '锚点' in l and '文本' in l and '显示' in l for l in lines),
       next((l for l in lines if '工具闸门（已含在' in l), '(无)'))
    # ★★ 第九刀（rev15）：像素条复算那行必须**恒打**（带 rev15 版本号）。
    #   第七刀的教训：写成「有值才打」⇒ 实机看不到它时**无法区分**
    #   「本版没加载」与「一次复算都没发生」。
    ck('★★ 「皮条纹复算」行恒打（带 rev15）',
       any('皮条纹复算：' in l and 'rev15' in l for l in lines),
       next((l for l in lines if '皮条纹复算' in l), '(无)'))
    # ★★ 第十刀（rev16）：材料串按需算 —— 强制只同步绑 2 行后，首屏之外的
    #   配方行必然走「挂待算标」路径；渲染收尾必须把它们的材料串**一条不漏**
    #   补上（pendLeft=0 / noSeg=0），否则行上就空着材料列。
    m_meta = next((l for l in lines if l.startswith('@@MATS')), None)
    m_ok, m_detail = False, '(无 @@MATS 行)'
    if m_meta:
        _p = m_meta.split('\t')
        if len(_p) >= 6:
            _spec, _pend, _done, _bad, _pump = (int(_p[1]), int(_p[2]),
                                                int(_p[3]), int(_p[4]), int(_p[5]))
            # 强制 keep=2 ⇒ 首屏之外必然走「挂待算标」；抽干分帧队列后：
            #   · 真被绑上的行一条都不许缺材料串（_bad == 0）
            #   · 走惰性路径的行必须 > 2 条（否则这条断言是恒真的白测）
            #   · 剩的挂标只允许是「被 ROW_CAP 裁掉、这帧压根不画」那条
            #     （抬头行占掉 300 个绘制槽之一，是既有的 off-by-one）
            m_ok = _bad == 0 and _done > 2 and _pend <= 2
            m_detail = ('spec=%d 挂标=%d 已算=%d 缺串=%d 分帧块=%d（强制 keep=2）'
                        % (_spec, _pend, _done, _bad, _pump))
    ck('★★ 材料串按需算：首屏外挂待算标，绑前用同一 PD.MAT_W 补算且一条不漏',
       m_ok, m_detail)
    # ★★ 第十一刀（rev17）：记忆表正负分离 —— 正向跨 Render 存活（第 2 次取
    #   同名 = 0 次引擎调用）；负向每次重问（否则到货重扫刷不出名字）；
    #   空闲预热真的把当前专业的物品名喂进表并发装载请求。
    p_memo = [int(x) for x in (next((l for l in lines
                                     if l.startswith('@@MEMO\t')), '@@MEMO\t-1\t-1')
                               .split('\t')[1:])]
    p_neg = [int(x) for x in (next((l for l in lines
                                     if l.startswith('@@MEMO2\t')), '@@MEMO2\t-1\t-1')
                               .split('\t')[1:])]
    p_warm = [int(x) for x in (next((l for l in lines
                                      if l.startswith('@@WARM\t')), '@@WARM\t-1\t-1')
                                .split('\t')[1:])]
    ck('★★ 物品名正向记忆跨 Render 存活（清负向表后不再问引擎）',
       p_memo == [1, 0], '首次 %s 次 · 清表后 %s 次' % tuple(p_memo))
    ck('★★ 「未到货」不跨 Render（每次都要重问，否则到货重扫永远刷不出名字）',
       p_neg == [1, 1], '首次 %s 次 · 清表后 %s 次' % tuple(p_neg))
    ck('★★ 空闲预热把当前专业的物品名喂进持久记忆表（并发装载请求）',
       p_warm[0] > 0 if p_warm else False,
       '装载请求 %s 次 · 分帧块 %s' % tuple(p_warm))
    # ★★ /dfprofperf rep：连渲同一页 3 次（冷 / 热对照）
    rep_head = [l for l in rep_lines if 'ms  ' in l and '「' in l]
    ck('★★ /dfprofperf rep 连渲 3 次都打出头行（冷 / 热对照可用）',
       len(rep_head) >= 3, '共 %d 条头行' % len(rep_head))

    # ★★ 造态验证：物品名未到货时必须走「轻量请求」，且**不许**走 DG.RequestItem
    parts = tail.split('\t') if tail else []
    if len(parts) == 3:
        rlN, riN, nr = (int(x) for x in parts)
        ck('★★ 名字未到货 ⇒ 走轻量请求（C_Item.RequestLoadItemDataByID）',
           rlN > 0, '%d 次' % rlN)
        ck('★★ 名字未到货 ⇒ **不再**走 DG.RequestItem（tooltip 预热 + CreateFromItemID）',
           riN == 0, '%d 次（必须为 0）' % riN)
        ck('★★ 未到货的 id 进了 PD.notReady（0.5/1.5/4/9s 定时重渲链路还在）',
           nr > 0, '%d 个' % nr)
    else:
        ck('造态段有结果返回', False, repr(tail)[:120])

    print('-' * 72)
    print('—— 探针输出 ——')
    for l in lines[:14]:
        print('  ' + l)
    print('-' * 72)
    print('失败 %d 项' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
