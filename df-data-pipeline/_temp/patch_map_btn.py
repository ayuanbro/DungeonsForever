import sys, io

PATH = 'Core/MapUI.lua'
EDITS = [
    ('M.LAYER_W, M.LAYER_GAP = 46, 4',
     'M.LAYER_W, M.LAYER_GAP = 66, 8'),
    ('M.BAR_H = 20                     -- 楼层按钮条高度',
     'M.BAR_H = 24                     -- 楼层按钮条高度'),
    ('M.BOSS_BTN_W = 72',
     'M.BOSS_BTN_W = 80'),
    ('local bt = Host.NewButton(bar, "", M.LAYER_W, M.BAR_H, 12)',
     'local bt = Host.NewButton(bar, "", M.LAYER_W, M.BAR_H, 14)'),
    ('local bossBtn = Host.NewButton(frame, "", M.BOSS_BTN_W, M.BAR_H, 12)',
     'local bossBtn = Host.NewButton(frame, "", M.BOSS_BTN_W, M.BAR_H, 14)'),
]

check_only = '--check' in sys.argv
raw = open(PATH, 'rb').read()
crlf = raw.count(b'\r\n')
assert crlf == 0, 'expected LF file, got CRLF=%d' % crlf
text = raw.decode('utf-8')

fails = 0
for old, new in EDITS:
    n = text.count(old)
    if n != 1:
        print('  FAIL hits=%d expect=1 : %s' % (n, old[:60]))
        fails += 1
        continue
    print('  ok   hits=1 : %s' % old[:60])
    if not check_only:
        text = text.replace(old, new, 1)

if check_only:
    print('check done, fails=%d' % fails)
    sys.exit(1 if fails else 0)

assert fails == 0, 'anchor mismatch'
open(PATH, 'wb').write(text.encode('utf-8'))
print('patched OK')
