import sys

P = '_temp/df_dungeon_check.py'

OLD = (
    "       and 'DG.Q_LIST_W + DG.Q_DET_GAP,' in src)\n"
    "    ck('★ 全局间距标准"
)
NEW = (
    "       and 'DG.Q_LIST_W + DG.Q_DET_GAP,' in src)\n"
    "    ck('★ 任务页重排（2026-10-13）：两卡顶上移贴 hero + 筛选按钮入左卡顶部 + 进度行不再显示',\n"
    "       'plateL:SetPoint(\"TOPLEFT\", detail, \"TOPLEFT\", 0, -DG.FILTER_Y)' in src\n"
    "       and 'DG.Q_HEAD_H = DG.Q_PAD + 24 + DG.Q_PAD' in src\n"
    "       and 'local nH, nR, y = 0, 0, -DG.Q_HEAD_H' in src\n"
    "       and 'U.dungeonQuestSum:Hide()' in src\n"
    "       and 'bt:SetPoint(\"TOPLEFT\", plateL, \"TOPLEFT\", DG.Q_PAD + (i - 1) * 100, -DG.Q_PAD)' in src)\n"
    "    ck('★ 全局间距标准"
)

raw = open(P, 'rb').read()
print('file CRLF=%d bare_LF=%d' % (raw.count(b'\r\n'), raw.count(b'\n') - raw.count(b'\r\n')))

ob = OLD.encode('utf-8')
nb = NEW.encode('utf-8')
n = raw.count(ob)
print('anchor hits=%d expect=1' % n)
if n != 1:
    sys.exit(1)

if '--check' in sys.argv:
    print('check ok')
    sys.exit(0)

raw = raw.replace(ob, nb, 1)
open(P, 'wb').write(raw)
print('patched OK')
