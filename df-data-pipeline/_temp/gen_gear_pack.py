# -*- coding: utf-8 -*-
"""装备库行打包生成器：10 槽行 -> {id,name,pack,icon} 4 槽行
用法：
  python gen_gear_pack.py --check  只做 round-trip 校验 + 内存 A/B
  python gen_gear_pack.py --apply  重写 Core/Data/{,zhTW/,enUS/}Data_Gear.lua
位布局（LSB->MSB）：q(3) ilvl(8) req(8) u(5) cIs4(1) st_new(1) sIdx(6) = 32bit
槽位字典内嵌为 ns.GearSlots（随 EnsureGearData 惰性赋值，逐文件自洽）。
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FILES = [
    os.path.join(ROOT, 'Core/Data/Data_Gear.lua'),
    os.path.join(ROOT, 'Core/Data/zhTW/Data_Gear.lua'),
    os.path.join(ROOT, 'Core/Data/enUS/Data_Gear.lua'),
]

def lua_str(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

def load_ns(path):
    from lupa import lua51
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    loc = 'zhTW' if 'zhTW' in path else ('enUS' if 'enUS' in path else 'zhCN')
    L.globals()['GetLocale'] = L.eval('function() return "%s" end' % loc)
    code = open(path, 'rb').read().decode('utf-8')
    f = L.eval("function(src,name) local f,err=loadstring(src,name) if not f then error(err) end return f end")(
        code, os.path.basename(path))
    ns = L.table()
    f('addon', ns)
    ns.EnsureGearData()
    return L, ns

def process(path, apply):
    L, ns = load_ns(path)
    G = ns.GearData
    items = G['items']
    n = len(items)
    rows = []
    slots = {}
    for i in range(1, n + 1):
        it = items[i]
        r = [it[j] for j in range(1, 11)]
        if len(r) != 10 or not isinstance(r[0], int):
            raise SystemExit('%s: row %d bad shape len=%d' % (path, i, len(r)))
        q, ilv, rq, s, c, u, st = r[2], r[3], r[4], str(r[5]), r[6], r[7], str(r[9])
        if not (0 <= q <= 7 and 0 <= ilv <= 255 and 0 <= rq <= 255 and 0 <= u <= 31 and c in (2, 4) and st in ('', 'new')):
            raise SystemExit('%s: row %d out of range q=%s ilvl=%s req=%s c=%s u=%s st=%r' % (path, i, q, ilv, rq, c, u, st))
        slots.setdefault(s, len(slots))
        rows.append(r)
    if len(slots) > 64:
        raise SystemExit('%s: too many slots %d' % (path, len(slots)))
    slot_names = sorted(slots.keys())
    slot_idx = {s: i for i, s in enumerate(slot_names)}

    pack_fn = L.eval(r'''
function(rows, slotidx)
    local out = {}
    for i = 1, #rows do
        local r = rows[i]
        local sidx = slotidx[r[6]]
        if not sidx then error("no slot: " .. tostring(r[6])) end
        local pack = r[3] % 8
            + r[4] * 8
            + r[5] * 2048
            + r[8] * 524288
            + (r[7] == 4 and 16777216 or 0)
            + (r[10] == "new" and 33554432 or 0)
            + sidx * 67108864
        if pack >= 4294967296 then error("overflow row " .. i) end
        out[i] = {r[1], r[2], pack, r[9]}
    end
    return out
end
''')
    idx = L.table()
    for s, i in slot_idx.items():
        idx[s] = i
    rows_lua = L.table(*[L.table(*r) for r in rows])
    packed = pack_fn(rows_lua, idx)

    verify_fn = L.eval(r'''
function(orig, packed, slotnames)
    local slot = {}
    for i, s in ipairs(slotnames) do slot[i - 1] = s end
    local floor = math.floor
    local bad = 0
    for i = 1, #orig do
        local a, b = orig[i], packed[i]
        local p = b[3]
        local q = p % 8
        local ilv = floor(p / 8) % 256
        local rq = floor(p / 2048) % 256
        local u = floor(p / 524288) % 32
        local c = (floor(p / 16777216) % 2 == 1) and 4 or 2
        local st = (floor(p / 33554432) % 2 == 1) and "new" or ""
        local s = slot[floor(p / 67108864) % 64]
        if b[1] ~= a[1] or b[2] ~= a[2] or b[4] ~= a[9]
            or q ~= a[3] or ilv ~= a[4] or rq ~= a[5] or s ~= a[6]
            or c ~= a[7] or u ~= a[8] or st ~= a[10] then
            if bad < 5 then
                print(("MISMATCH row %d id=%s: q %s/%s ilvl %s/%s req %s/%s s %s/%s c %s/%s u %s/%s st %s/%s")
                    :format(i, tostring(a[1]),
                        tostring(a[3]), tostring(q), tostring(a[4]), tostring(ilv),
                        tostring(a[5]), tostring(rq), tostring(a[6]), tostring(s),
                        tostring(a[7]), tostring(c), tostring(a[8]), tostring(u),
                        tostring(a[10]), tostring(st)))
            end
            bad = bad + 1
        end
    end
    return bad
end
''')
    bad = verify_fn(rows_lua, packed, L.table(*slot_names))
    if bad:
        raise SystemExit('%s: round-trip FAIL %d rows' % (path, bad))

    if not apply:
        print('%s: OK rows=%d slots=%d round-trip PASS' % (os.path.relpath(path, ROOT), n, len(slot_names)))
        return

    src = open(path, 'rb').read().decode('utf-8')
    lines = src.split('\n')
    start = end = None
    for i, ln in enumerate(lines):
        if ln == '  items = {':
            start = i
            break
    if start is None:
        raise SystemExit('%s: items block not found' % path)
    for j in range(start + 1, len(lines)):
        if lines[j] == '  },':
            end = j
            break
    if end is None:
        raise SystemExit('%s: items block end not found' % path)
    out_rows = []
    for i in range(1, n + 1):
        b = packed[i]
        out_rows.append('{%d,%s,%d,%s}' % (int(b[1]), lua_str(str(b[2])), int(b[3]), lua_str(str(b[4]))))
    body = []
    per = 8
    for k in range(0, len(out_rows), per):
        body.append('    ' + ', '.join(out_rows[k:k + per]) + ',')
    new_lines = lines[:start + 1] + body + lines[end:]
    text = '\n'.join(new_lines)
    slot_line = 'ns.GearSlots = { ' + ', '.join(lua_str(s) for s in slot_names) + ' }\n'
    marker = 'return ns.GearData'
    pos = text.rfind(marker)
    if pos < 0:
        raise SystemExit('%s: return marker not found' % path)
    text = text[:pos] + slot_line + text[pos:]
    open(path, 'wb').write(text.encode('utf-8'))
    print('%s: WROTE rows=%d slots=%d old_lines=%d->%d' % (
        os.path.relpath(path, ROOT), n, len(slot_names), len(lines), len(new_lines) + 1))

def main():
    apply = '--apply' in sys.argv
    for p in FILES:
        process(p, apply)

if __name__ == '__main__':
    main()
