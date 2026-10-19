import sys

P = '_temp/df_mut_check.py'

EDITS = [
    (b"                    DG.Q_LIST_W + DG.Q_DET_GAP, -DG.SCROLL_Y)\\r\\n',",
     b"                    DG.Q_LIST_W + DG.Q_DET_GAP, -DG.FILTER_Y)\\r\\n',", 1),
    (b"                    DG.Q_LIST_W, -DG.SCROLL_Y) -- MUT: overlap\\r\\n')",
     b"                    DG.Q_LIST_W, -DG.FILTER_Y) -- MUT: overlap\\r\\n')", 1),
]

check_only = '--check' in sys.argv
raw = open(P, 'rb').read()
print('file CRLF=%d bare_LF=%d' % (raw.count(b'\r\n'), raw.count(b'\n') - raw.count(b'\r\n')))

fails = 0
for i, (old, new, want) in enumerate(EDITS, 1):
    n = raw.count(old)
    if n != want:
        print('  FAIL#%d hits=%d expect=%d : %s' % (i, n, want, old[:70]))
        fails += 1
        continue
    print('  ok  #%d hits=%d : %s' % (i, n, old[:62]))
    if not check_only:
        raw = raw.replace(old, new, 1)

if check_only:
    print('check done, fails=%d' % fails)
    sys.exit(1 if fails else 0)

assert fails == 0
open(P, 'wb').write(raw)
print('patched OK')
