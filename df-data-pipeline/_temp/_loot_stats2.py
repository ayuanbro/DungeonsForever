import lupa.lua51 as lua51
import collections

L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute('ns={}')
src = open('Core/Data/Data_DungeonLoot.lua', 'rb').read()
L.eval('function(s) local f=assert(loadstring(s,"c")); f("DF",ns) end')(src.decode('utf-8'))
f = L.eval('''function()
  local out={}
  for did,srcs in pairs(ns.DungeonLoot) do
    for i=1,#srcs do local s=srcs[i]
      out[#out+1]={did,s[1] or "",s[2] or "",s[3] or "",s[5] and #s[5] or 0}
    end
  end
  return out
end''')
d = f()
rows = []
for i in range(1, 5000):
    v = d[i]
    if v is None:
        break
    rows.append((int(v[5]), v[1], v[2], v[3], v[4]))

rows.sort(key=lambda r: -r[0])
print('单来源件数 Top15:')
for c, did, a, b, sub in rows[:15]:
    print('  %3d  %-22s %s / %s / %s' % (c, did, a, b, sub))
print()
print('全库来源条目:', len(rows))
for t in (10, 15, 20, 25, 30, 40, 50):
    print('  件数 >= %-2d : %d 条' % (t, sum(1 for r in rows if r[0] >= t)))
print()
print('最长来源名 Top5:')
for c, did, a, b, sub in sorted(rows, key=lambda r: -len(r[2]))[:5]:
    print('  %d 字: %s | %s | %s' % (len(b), b, a, sub))
print()
# 每个副本的 来源数 & 峰值
per = {}
for c, did, a, b, sub in rows:
    n, mx = per.get(did, (0, 0))
    per[did] = (n + 1, max(mx, c))
print('副本数:', len(per), ' boss 数中位/最大:', sorted(n for n, _ in per.values())[len(per)//2], max(n for n, _ in per.values()))
