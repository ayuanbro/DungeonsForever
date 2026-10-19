# -*- coding: utf-8 -*-
"""第五刀收尾（只改文档注释，不动一行逻辑）：
DG.Loader 的头部注释里还写着「数量闸 budgetObj」—— 那个字段在第四刀已经被删掉了
（改由 DG.LOOT_ROW_FRAME_CAP / DG.CARD_POOL_CAP 各自夹住）。注释与代码不符会让下一个人
照着注释去找一个不存在的字段，所以这里把注释改成实际口径。

★ 只做「文档与代码一致」这一件事：锚点是注释行，命中必须恰好 1 次；改动后仍须 CRLF、
  裸 LF 必须为 0（DungeonUI.lua 是全 CRLF 手写件）。
"""
import io
import sys

P = 'Core/DungeonUI.lua'

OLD = (
    '--     \u00b7 \u6570\u91cf\u95f8 budgetObj\uff1a\u8ba1\u65f6\u53e3\u4e0d\u53ef\u7528 / '
    '\u8ba1\u65f6\u5f02\u5e38\u65f6\u7684\u515c\u5e95\uff0c\u9632\u4e00\u5e27\u5931\u63a7\u3002\r\n'
)
NEW = (
    '--     \u00b7 \u6570\u91cf\u95f8 DG.LOOT_ROW_FRAME_CAP / DG.CARD_POOL_CAP\uff1a'
    '\u8ba1\u65f6\u53e3\u4e0d\u53ef\u7528 / \u8ba1\u65f6\u5f02\u5e38\r\n'
    '--       \u65f6\u7684\u515c\u5e95\uff0c\u9632\u4e00\u5e27\u5931\u63a7\uff08'
    '\u79bb\u7ebf\u6869\u5c31\u8d70\u8fd9\u6761\uff09\u3002\r\n'
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

    if 'budgetObj' in txt:
        left = txt.count('budgetObj')
        print('FAIL: budgetObj \u4ecd\u6b8b\u7559 %d \u5904' % left)
        return 1

    out = txt.encode('utf-8')
    bare = out.count(b'\n') - out.count(b'\r\n')
    if bare != 0:
        print('FAIL: \u51fa\u73b0\u88f8 LF %d \u4e2a' % bare)
        return 1

    with io.open(P, 'wb') as f:
        f.write(out)
    print('OK: \u6ce8\u91ca\u5df2\u6539\u6210\u5b9e\u9645\u53e3\u5f84\uff1bbytes=%d CRLF=%d \u88f8LF=0'
          % (len(out), out.count(b'\r\n')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
