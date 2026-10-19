# -*- coding: utf-8 -*-
import io, sys
from lupa import LuaRuntime

lua = LuaRuntime(unpack_returned_tuples=True)
src = open('Core/Data/Data_BIS.lua','rb').read().decode('utf-8')
B = lua.execute(src)

LUA = r'''
function(classes)
  local out = {}
  local function sidehas(sp, k, side)
    local sides = sp.slots and sp.slots[k]
    if type(sides) ~= "table" then return false end
    local s = sides[(side == "h") and 2 or 1]
    return type(s) == "table" and s[1] ~= nil
  end
  local function mainkey(sp, side)
    if sidehas(sp, "two-hand", side) then return "two-hand" end
    if sidehas(sp, "main-hand", side) then return "main-hand" end
    if sp.slots["two-hand"] then return "two-hand" end
    return "main-hand"
  end
  local function offkey(sp, side)
    for _, k in ipairs({ "off-hand", "held", "shield" }) do
      if sidehas(sp, k, side) then return k end
    end
    for _, k in ipairs({ "off-hand", "held", "shield" }) do
      if sp.slots[k] then return k end
    end
    return "off-hand"
  end
  for _, c in ipairs(classes) do
    for _, sp in ipairs(c.specs or {}) do
      for _, side in ipairs({ "a", "h" }) do
        local mk = mainkey(sp, side)
        local ok = sidehas(sp, mk, side)
        out[#out+1] = {
          slug = c.slug, key = sp.key, side = side,
          mk = mk, mkHasValue = ok,
          standalone = (not sidehas(sp, "two-hand", side)) and (not sidehas(sp, "main-hand", side)),
          off = offkey(sp, side),
        }
      end
    end
  end
  return out
end
'''
rows = lua.execute(LUA)(B['classes']).values()
rows = list(rows)

bad = [r for r in rows if not r['mkHasValue']]
print("total page-side combos:", len(rows))
print("MainKey resolves to empty:", len(bad))
for r in bad[:20]:
    print("  BAD", r['slug'], r['key'], r['side'], "mk=", r['mk'])

# 单侧槽分布统计
from collections import Counter
c_two = Counter(); c_main = Counter(); c_held = Counter()
for _, c in ipairs_dummy() if False else []:
    pass

def counts(classes, k):
    a=0;h=0
    for c in classes.values():
        for sp in (c['specs'] or {}).values():
            sides = sp['slots'].get(k)
            if sides is None: continue
            if sides[1] is not None and sides[1][1] is not None: a+=1
            if sides[2] is not None and sides[2][1] is not None: h+=1
    return a,h

print("two-hand  a/h:", counts(B['classes'],'two-hand'))
print("main-hand a/h:", counts(B['classes'],'main-hand'))
print("held      a/h:", counts(B['classes'],'held'))

# 关键案例
for c in B['classes'].values():
    for sp in (c['specs'] or {}).values():
        if c['slug']=='warlock' and sp['key']=='warlock/affli':
            for log in []: pass
            def sh(k,s):
                sd=sp['slots'].get(k)
                if sd is None: return False
                x=sd[2 if s=='h' else 1]
                return x is not None and x[1] is not None
            print("warlock/affli  A: two=%s main=%s held=%s | H: two=%s main=%s held=%s" % (
              sh('two-hand','a'),sh('main-hand','a'),sh('held','a'),
              sh('two-hand','h'),sh('main-hand','h'),sh('held','h')))
