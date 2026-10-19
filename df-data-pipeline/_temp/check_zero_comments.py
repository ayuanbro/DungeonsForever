# -*- coding: utf-8 -*-
"""注释零容忍检查（2026-10-17 用户定：插件不带任何注释）。

范围 = 打包集（toc + Core/**.lua + Locales/*.lua）。Libs/ 不扫：
第三方库的版权头 / 注册名必须原样保留（AGENTS.md 明文豁免）。

与 check_comment_redline.py 的分工：那个查「注释里有没有别的插件名」，
这个查「到底还有没有注释」—— 只要打包集里出现任何一行注释就 FAIL。

用法：
  python check_zero_comments.py          # 全量扫，有注释 exit=1
  python check_zero_comments.py <file>   # 只扫单个文件
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strip_comments import comment_spans  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def scan(paths):
    """返回 {相对路径: [行号...]}，只含真有注释的文件。"""
    bad = {}
    for p in paths:
        try:
            with open(p, 'rb') as f:
                text = f.read().decode('utf-8', errors='replace')
        except OSError as e:
            print('!! 读不了 %s: %s' % (p, e))
            return None
        lf = text.replace('\r\n', '\n')
        spans = comment_spans(lf)
        if not spans:
            continue
        lines = set()
        for s, _ in spans:
            lines.add(lf.count('\n', 0, s) + 1)
        if lines:
            bad[os.path.relpath(p, ROOT).replace('\\', '/')] = sorted(lines)
    return bad


def main():
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = [os.path.join(ROOT, 'DungeonsForever.toc')]
        for sub in ('Core', 'Locales'):
            files += glob.glob(os.path.join(ROOT, sub, '**', '*.lua'), recursive=True)
        files = sorted(set(files))
    bad = scan(files)
    if bad is None:
        return 2
    if bad:
        total = sum(len(v) for v in bad.values())
        print('[FAIL] 注释零容忍：%d 个文件仍有 %d 行注释' % (len(bad), total))
        for rel, ls in sorted(bad.items())[:40]:
            head = ','.join(str(x) for x in ls[:8]) + ('…' if len(ls) > 8 else '')
            print('  %s  行 %s' % (rel, head))
        print('  修法：python _temp/strip_lua_comments.py --apply')
        return 1
    print('[OK] 注释零容忍：打包集 0 行注释（%d 个文件）' % len(files))
    return 0


if __name__ == '__main__':
    sys.exit(main())
