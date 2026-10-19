P = 'Core/DungeonUI.lua'
d = open(P, 'rb').read()
before = len(d)

def b(s):
    return s.replace('\n', '\r\n').encode('utf-8')

old = b('''    local native = false
    if id and GameTooltip.SetItemByID then
        local ok = pcall(GameTooltip.SetItemByID, GameTooltip, id)
''')

new = b('''    local native = false
    local cached = false
    if id then
        local info = DG.ItemInfo(id)
        cached = (type(info) == "string" and info ~= "")
    end
    if id and cached and GameTooltip.SetItemByID then
        local ok = pcall(GameTooltip.SetItemByID, GameTooltip, id)
''')

old2 = b('''    if not native and id and GameTooltip.SetHyperlink then
''')
new2 = b('''    if not native and id and cached and GameTooltip.SetHyperlink then
''')

assert d.count(old) == 1, ('old count', d.count(old))
d = d.replace(old, new, 1)
open(P, 'wb').write(d)
print('size', before, '->', len(d))
print('crlf', d.count(b'\r\n'), 'lone_lf', d.count(b'\n') - d.count(b'\r\n'))
lines = d.decode('utf-8').split('\r\n')
for i in range(3142, 3172):
    print(i + 1, lines[i])
