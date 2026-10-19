# -*- coding: utf-8 -*-
"""钉死「止点」语义：自动路线存储的 st[2] 到底是「最后制作的技能值」还是「达到的技能值」。

对每段同时给出三个数：
  · qty            —— 算法报的制作次数（= 积分 [from, X] 的 ceil，X = 最后可做技能值）
  · integ[from,to] —— 积分到存储的 to
  · integ[from,to-1] —— 积分到 to-1（ProfFollow.craftsLeft 的口径 = [from, seg[2]-1]）

若 qty ≈ integ[from,to] 且 ≠ integ[from,to-1]，说明 **to = 最后制作的技能值**，
实际达到的技能是 to+1 ⇒ 显示应 +1（用户诉求），且 HUD 的 craftsLeft 少算一点。

用法：python _temp/_reach_semantics_probe.py [slug]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51


def make_lua(addon):
    toc = open(os.path.join(addon, os.path.basename(D.TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(D.T.STUB)
    lua.execute('C_Timer = { After = function(t, fn) fn() end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 end')
    lua.execute('BG.hui.OnThemeChange = function(fn) end')
    lua.execute('BG.hui = nil')
    lua.execute('UnitName = function() return "p" end')
    lua.execute('GetRealmName = function() return "r" end')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local o=GetBuildInfo; GetBuildInfo=function(...) '
                'local a,b,c,d=o(...); return a,b,c,16001,e end end')
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_Map = { GetAreaInfo = function(id) return "z"..tostring(id) end }
Auctionator = { API = { v1 = {
  GetAuctionPriceByItemID = function(c,id) return 1000 end,
  GetAuctionAgeByItemID = function(c,id) return 0 end,
  GetVendorPriceByItemID = function(c,id) return 500 end } },
  SavedState = { TimeOfLastGetAllScan = 1796850000 - 3600 } }
''')
    lf = lua.eval('function(rel)\n'
                  '  local ch = loadfile(ADDON_ROOT .. "/" .. rel)\n'
                  '  if not ch then return nil end\n'
                  '  return function() return ch("DungeonsForever", TF_NS) end\n'
                  'end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        c = lf(rel)
        if c is None:
            raise RuntimeError('loadfile nil: ' + rel)
        c()
    return lua


DUMP = r'''
(function(slug)
  local RA = TF_NS.ProfRouteAuto
  RA.Invalidate()
  local res = RA.Compute(slug, { start = 1, target = 300 })
  local rm = {}
  for _, r in ipairs((TF_NS.ProfRecipes[slug] or {}).rows or {}) do rm[r[1]] = r end
  for sp, ri in pairs((TF_NS.ProfLeveling[slug] or {}).rinfo or {}) do
    if not rm[sp] then rm[sp] = ri end
  end
  local function integ(a, b, o, y, g, gr)
    if b < a then return 0 end
    local t = 0
    for sk = a, b do
      local e
      if sk < o or sk >= gr then return -1 end
      if sk < y then e = 1
      elseif sk < g then e = 1 / (1 - 0.5 * (sk - y) / (g - y))
      else e = 1 / (0.5 - 0.45 * (sk - g) / (gr - g)) end
      t = t + e
    end
    return t
  end
  local out = {}
  for i, st in ipairs(res.steps) do
    local rec = rm[st[3]]
    local o = rec and (rec[7] or rec.learn)
    local y = rec and (rec[8] or rec.yellow)
    local g = rec and (rec[9] or rec.green)
    local gr = rec and (rec[10] or rec.grey)
    local a, b = st[1], st[2]
    -- ★ st[2] 已含 Compute 出口的 +1（= 练到的技能值）；可做点区间 = [a, b - 1]
    local i_to = o and integ(a, b - 1, o, y, g, gr) or -1
    local i_at0 = o and integ(a, b, o, y, g, gr) or -1
    out[#out + 1] = string.format(
      "%d,%d-%d,%d,qty=%d,i[%d..%d]=%.2f,i[%d..%d]=%.2f,grey=%s,to+1==grey=%s",
      i, a, b, st[3], st[4], a, b - 1, i_to, a, b, i_at0,
      tostring(gr), tostring(gr and (b + 1 == gr)))
  end
  return table.concat(out, "\n")
end)
'''


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    slug = sys.argv[1] if len(sys.argv) > 1 else 'alchemy'
    lua = make_lua(addon)
    print('=== %s ===' % slug)
    print('段,i 区间,spell,qty,i[from..to],i[from..to-1],grey,to+1==grey')
    print(lua.eval(DUMP)(slug))
    return 0


if __name__ == '__main__':
    sys.exit(main())
