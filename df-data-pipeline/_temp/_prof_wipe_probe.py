# -*- coding: utf-8 -*-
"""专业页 · 切页「内容除净」探针（2026-10-09）。

被保护的不变量
--------------
切页（页签 / 专业 / 升级子页 / 设置页 任一身份变化）之后，**不属于本页规格**的
行帧必须**连内容一起**抹净，而不只是 `Hide()`：

    f 文本 = ""、dv 文本 = ""、blk 里没有任何 ic/ct 显示中、mn/mz 没有显示中

为什么这条不变量值得单独立闸
----------------------------
离线 harness 的桩把「隐藏」记在**帧自己**的 `__shown` 上，而真机是「父帧隐藏 ⇒
整棵子树不渲染」。所以「只 Hide」在离线看永远是干净的 —— 而用户报的
「配方页 → 升级页，页面有材料残留」，恰恰是**内容还挂在行帧上**的形态：
只要有任何一条路径（分帧补建 / 同索引复用 / 皮肤重建）在没重新 BindRow 的
情况下把行 Show 出来，露出来的就是上一页的材料。

判据设计
--------
- 基线页（直接进目标页，池子干净）→ 记下每行的 `f`/`dv` 文本与 blk 显示数；
- 往返页（配方页 → 目标页）→ 再记一次；
- **只对「本页没有对应 spec」的行**做断言（有 spec 的行本来就该显示本页内容）；
- 断言：往返之后这些行的 `f`/`dv` 文本必须是空、blk 必须没有显示中的 ic。

只读，不写产品文件。
用法：DF_ADDON_ROOT=<addon> python _temp/_prof_wipe_probe.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51  # noqa: E402

SLUGS = ["alchemy", "blacksmithing", "enchanting", "engineering",
         "leatherworking", "tailoring"]


def build(addon):
    toc = open(os.path.join(addon, os.path.basename(D.TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    stub = D.T.STUB.replace(
        '            elseif NUMERIC[k] then f = function() return 100 end',
        '            elseif k == "GetStringWidth" then'
        ' f = function(self) return #(self.__text or "") * 6 end\n'
        '            elseif NUMERIC[k] then f = function() return 100 end', 1)
    assert stub != D.T.STUB
    lua.execute(stub)
    lua.execute('C_Timer = { After = function(t, fn) fn() end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local o = GetBuildInfo; GetBuildInfo = function(...) '
                'local a, b, c, d = o(...); return a, b, c, 16001, e end end')
    lua.execute('UIErrorsFrame = { AddMessage = function() end }')
    lua.execute('C_Map = { CanSetUserWaypointOnMap = function() return true end, '
                'SetUserWaypoint = function() end, OpenWorldMap = function() end, '
                'GetAreaInfo = function() return "x" end }')
    lf = lua.eval('function(rel) local c = loadfile(ADDON_ROOT .. "/" .. rel) '
                  'if not c then return nil end '
                  'return function() return c("DungeonsForever", TF_NS) end end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        lf(rel)()
    lua.execute('do UnitLevel = function() return 60 end '
                'if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end '
                'TF_NS.DungeonUI:Build() TF_NS.DungeonUI:SwitchSub("Professions") end')

    # 采集：所有「本页没有 spec」的行 —— 它们的 f/dv 文本与 blk 显示数
    lua.execute(r'''
function WIPE_SURVEY()
  local PD = TF_NS.ProfModule
  local nSpec = #(PD.specs or {})
  local dirty = {}
  for i, r in pairs(PD.rows or {}) do
    if not (PD.specs and PD.specs[i]) then
      local f = rawget(r, "f"); local dv = rawget(r, "dv")
      local ft = f and rawget(f, "__text") or ""
      local dt = dv and rawget(dv, "__text") or ""
      local nblk = 0
      for j = 1, #(rawget(r, "blk") or {}) do
        local b = rawget(r, "blk")[j]
        if rawget(b.ic, "__shown") == true then nblk = nblk + 1 end
      end
      local nmn, nmz = 0, 0
      for j = 2, #(rawget(r, "mn") or {}) do
        if rawget(rawget(r, "mn")[j], "__shown") == true then nmn = nmn + 1 end
      end
      for j = 1, #(rawget(r, "mz") or {}) do
        if rawget(rawget(r, "mz")[j], "__shown") == true then nmz = nmz + 1 end
      end
      if (ft ~= "" and ft ~= nil) or (dt ~= "" and dt ~= nil)
         or nblk > 0 or nmn > 0 or nmz > 0 then
        dirty[#dirty + 1] = string.format(
          "idx=%s f=%q dv=%q 材料块=%d 分段字串=%d 分段热区=%d",
          tostring(i), tostring(ft), tostring(dt), nblk, nmn, nmz)
      end
    end
  end
  return nSpec, #dirty, table.concat(dirty, " ;; ")
end
''')

    def survey():
        nspec, ndirty, body = lua.eval('WIPE_SURVEY()')
        return nspec, ndirty, str(body) if body else ""

    def go_lv(mode):
        lua.eval('(function() local PD=TF_NS.ProfModule PD.setOpen=false '
                 'PD.autoPage=%r PD.SetTab("leveling") return 1 end)()' % mode)
        lua.eval('(function() local PD=TF_NS.ProfModule PD.setOpen=false '
                 'PD.autoPage=%r PD.SetTab("leveling") return 1 end)()' % mode)

    return lua, survey, go_lv


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    fails = 0
    total = 0
    for slug in SLUGS:
        lua, survey, go_lv = build(addon)
        lua.eval('(function() local PD=TF_NS.ProfModule PD.sweeping=true '
                 'PD.Show(%r) return 1 end)()' % slug)
        for mode in ("route", "shop"):
            # 直进基线：池子干净，记下「本页无 spec 的行」有多脏（应为 0 或仅无关紧要）
            go_lv(mode)
            go_lv(mode)
            base_n, base_dirty, base_body = survey()
            # 往返：配方页 → 目标页
            lua.eval('(function() local PD=TF_NS.ProfModule PD.setOpen=false '
                     'PD.SetTab("recipe") return 1 end)()')
            go_lv(mode)
            go_lv(mode)
            n_n, n_dirty, n_body = survey()
            total += 1
            # ★ 绝对口径：修好后基线也必须是 0（切页那道闸会把全池抹净）。
            #   用「相对基线」会放走「基线本身就脏」的格子（实测变异版里
            #   `升级/购物清单` 就是 141→141，相对口径判它 OK）。
            bad = (n_dirty > 0) or (base_dirty > 0)
            if bad:
                fails += 1
            print("[%s] %-14s 升级/%-4s：spec %s→%s  越界脏行 %d→%d"
                  % ('FAIL' if bad else 'OK  ', slug, mode,
                     base_n, n_n, base_dirty, n_dirty))
            if n_dirty:
                print("       往返后仍带内容的越界行：%s" % n_body[:400])
            elif base_dirty:
                print("       基线本就有 %d 行带内容：%s" % (base_dirty, base_body[:200]))
    print("\n结论：%s（%d 组 / 6 专业 × 2 子页）"
          % ('★ 切页后有内容残留' if fails else '切页后越界行内容全部除净', total))

    # ── 第二段：**同页内 n 变小**（配方页搜索）—— 不换页面身份，切页那道闸不响，
    #    只能靠 PD.PaintRows 收尾那句「正显示着的越界行除内容」兜住。
    print("\n— 同页收窄（配方页搜索把 180 行收成几行）：越界行内容必须除净 —")
    for slug in ("alchemy", "tailoring"):
        lua, survey, go_lv = build(addon)
        lua.eval('(function() local PD=TF_NS.ProfModule PD.sweeping=true '
                 'PD.Show(%r) return 1 end)()' % slug)
        lua.eval('(function() local PD=TF_NS.ProfModule PD.setOpen=false '
                 'PD.SetTab("recipe") return 1 end)()')
        n_full, dirty_full, _ = survey()
        # 收窄：把搜索词设成一个绝不可能命中的串 ⇒ n 骤降，越界行是「刚才还显示着」的
        lua.eval('(function() local PD=TF_NS.ProfModule PD.searchQ="zzz_no_hit_zzz" '
                 'PD.Render() PD.searchQ=nil return 1 end)()')
        lua.eval('(function() local PD=TF_NS.ProfModule PD.searchQ="zzz_no_hit_zzz" '
                 'PD.Render() PD.searchQ=nil return 1 end)()')
        n_small, dirty_small, body = survey()
        total += 1
        bad = dirty_small > 0
        if bad:
            fails += 1
        print("[%s] %-14s 配方 spec %s→%s  收窄后越界脏行 %d"
              % ('FAIL' if bad else 'OK  ', slug, n_full, n_small, dirty_small))
        if bad:
            print("       收窄后仍带内容的越界行：%s" % body[:400])
    print("\n最终结论：%s（共 %d 组）"
          % ('★ 有内容残留' if fails else '越界行内容全部除净', total))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
