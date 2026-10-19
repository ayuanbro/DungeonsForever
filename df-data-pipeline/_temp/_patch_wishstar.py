import io, sys

P = 'Core/DungeonUI.lua'
d = open(P, 'rb').read()
orig = d

def b(s):
    return s.replace('\n', '\r\n').encode('utf-8')

# 1) remove inner definition (lines 3531-3541 incl trailing blank)
inner = b('''    local function PaintWishStar(bt, id)
        local gm = ns.GearModule
        local on = gm and gm.WishIs and id and gm.WishIs(id)
        bt.star:SetText(on and "\u2605" or "\u2606")
        if on then
            bt.star:SetTextColor(1, 0.82, 0, 1)
        else
            bt.star:SetTextColor(0.55, 0.58, 0.65, 1)
        end
    end

''')
assert d.count(inner) == 1, ('inner count', d.count(inner))
d = d.replace(inner, b(''), 1)

# 2) hoist to file level, immediately before U:RenderDungeonLoot
anchor = b('function U:RenderDungeonLoot()\n')
assert d.count(anchor) == 1, ('anchor count', d.count(anchor))
hoisted = b('''local function PaintWishStar(bt, id)
    local gm = ns.GearModule
    local on = gm and gm.WishIs and id and gm.WishIs(id)
    bt.star:SetText(on and "\u2605" or "\u2606")
    if on then
        bt.star:SetTextColor(1, 0.82, 0, 1)
    else
        bt.star:SetTextColor(0.55, 0.58, 0.65, 1)
    end
end

''') + anchor
d = d.replace(anchor, hoisted, 1)

open(P, 'wb').write(d)

print('size', len(orig), '->', len(d))
print('crlf', d.count(b'\r\n'), 'lone_lf', d.count(b'\n') - d.count(b'\r\n'))
t = d.decode('utf-8')
lines = t.split('\r\n')
for i, l in enumerate(lines, 1):
    if 'PaintWishStar' in l:
        print(i, repr(l))
