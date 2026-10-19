# -*- coding: utf-8 -*-
"""第五刀收尾②：状态丸补上 hui 圆角皮。

项目铁律「圆角半径 ≥ 8」；本文件既有范式（EnsureContent / LootFilterUI 的 popup）都是
`if IsHui() and ns.hui and ns.hui.SkinPopup then ns.hui.SkinPopup(f, 8) end`。
进度条那 3px 细条不套圆角（不是框体，圆角在 3px 高上只会糊成锯齿）。

锚点 = 状态丸的 SetBackdrop 三连 + 两个颜色设置（字面相邻、文件里唯一）。
★ 改完仍须 CRLF、裸 LF 必须为 0。
"""
import io
import sys

P = 'Core/DungeonUI.lua'

OLD = (
    '    pill:SetBackdropBorderColor(1, 0.82, 0, 0.45)\r\n'
    '    pill.text = MakeFS(pill, 12, C_TEXT, "LEFT")\r\n'
)
NEW = (
    '    pill:SetBackdropBorderColor(1, 0.82, 0, 0.45)\r\n'
    '    -- \u2605 \u5706\u89d2 8 \u2265 \u672c\u63d2\u4ef6\u94c1\u5f8b\u4e0b\u9650\uff1b'
    '\u975e hui \u4e3b\u9898\u4e0b\u4e0a\u9762\u90a3\u5957\u7eaf\u8272\u5e95 + 1px \u63cf\u8fb9'
    '\u5c31\u662f\u515c\u5e95\u5916\u89c2\u3002\r\n'
    '    if IsHui() and ns.hui and ns.hui.SkinPopup then\r\n'
    '        ns.hui.SkinPopup(pill, 8)\r\n'
    '    end\r\n'
    '    pill.text = MakeFS(pill, 12, C_TEXT, "LEFT")\r\n'
)


def main():
    with io.open(P, 'rb') as f:
        data = f.read()
    txt = data.decode('utf-8')
    n = txt.count(OLD)
    if n != 1:
        print('FAIL: \u951a\u70b9\u547d\u4e2d %d \u6b21\uff08\u671f\u671b 1\uff09' % n)
        return 1
    txt = txt.replace(OLD, NEW)
    out = txt.encode('utf-8')
    bare = out.count(b'\n') - out.count(b'\r\n')
    if bare != 0:
        print('FAIL: \u51fa\u73b0\u88f8 LF %d \u4e2a' % bare)
        return 1
    with io.open(P, 'wb') as f:
        f.write(out)
    print('OK: \u72b6\u6001\u4e38\u5df2\u5957 hui \u5706\u89d2\u76ae\uff1bbytes=%d CRLF=%d \u88f8LF=0'
          % (len(out), out.count(b'\r\n')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
