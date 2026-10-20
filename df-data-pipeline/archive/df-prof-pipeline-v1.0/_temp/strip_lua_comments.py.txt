# -*- coding: utf-8 -*-
"""全删 lua 注释：整行注释 + 行尾注释 + **文件头注释块**（口径 2026-10-17 用户定：
「我们插件不要带任何注释」）。

与 strip_comments.py 的区别：那个保文件头块，这个一个不留。

  · 真词法扫描（复用 strip_comments.comment_spans），字符串内的 `--` 不受影响。
  · 行尾风格原样保留（CRLF 保持 CRLF）。
  · 落盘前做「代码投影」硬校验：剥掉注释与空白后的字符流必须逐字节一致，
    不一致即视为误伤代码，拒绝写盘。
  · Libs/ 下第三方库默认豁免（保留原版版权声明），自家 LibHUI 走 --include-libhui。

用法：
    python strip_lua_comments.py --dry-run            # 干跑，默认范围 Core + Locales
    python strip_lua_comments.py --apply              # 落盘
    python strip_lua_comments.py --apply Core/Data    # 指定目录/文件
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strip_comments import comment_spans  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 第三方库：保留原版（版权声明在注释里）；自家 LibHUI 不在此列
VENDOR = (
    'Libs/CallbackHandler-1.0',
    'Libs/LibDBIcon-1.0',
    'Libs/LibDataBroker-1.1',
    'Libs/LibStub',
    'Libs/UTF8',
)


def strip_all_text(text):
    """返回 (新文本, 删除整行注释数, 删除行尾注释数)。头块一并删。"""
    lf = text.replace('\r\n', '\n')
    lines = lf.split('\n')
    spans = comment_spans(lf)

    def covered(pos):
        lo, hi = 0, len(spans) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            s, e = spans[mid]
            if pos < s:
                hi = mid - 1
            elif pos >= e:
                lo = mid + 1
            else:
                return True
        return False

    starts, off = [], 0
    for ln in lines:
        starts.append(off)
        off += len(ln) + 1

    kept, only, tail = [], 0, 0
    for i, ln in enumerate(lines):
        base = starts[i]
        cut = None
        for col, ch in enumerate(ln):
            if covered(base + col):
                cut = col
                break
        if cut is None:
            kept.append(ln)
            continue
        pre = ln[:cut].rstrip()
        if pre == '':
            only += 1
            kept.append(None)
        else:
            tail += 1
            kept.append(pre)

    res, pending = [], 0
    for ln in kept:
        if ln is None:
            continue
        if ln.strip() == '':
            pending += 1
            continue
        if pending and res:
            res.append('')
        pending = 0
        res.append(ln)

    out = ('\n'.join(res).rstrip('\n') + '\n') if res else ''
    if '\r\n' in text:
        out = out.replace('\n', '\r\n')
    return out, only, tail


def code_projection(text):
    """剥掉注释与全部空白后的字符流，用于「只删注释、不动代码」硬校验。"""
    lf = text.replace('\r\n', '\n')
    spans = comment_spans(lf)
    for s, e in reversed(spans):
        lf = lf[:s] + lf[e:]
    return ''.join(ch for ch in lf if not ch.isspace())


def walk(paths):
    for p in paths:
        if os.path.isdir(p):
            for dp, _, fn in os.walk(p):
                for f in sorted(fn):
                    if f.endswith('.lua'):
                        yield os.path.join(dp, f)
        elif p.endswith('.lua'):
            yield p


def is_vendor(p):
    rel = os.path.relpath(p, ROOT).replace('\\', '/')
    return any(rel.startswith(v + '/') for v in VENDOR)


def main():
    argv = sys.argv[1:]
    apply = '--apply' in argv
    args = [a for a in argv if not a.startswith('--')]
    include_libhui = '--include-libhui' in argv

    roots = [os.path.join(ROOT, a) for a in args] if args \
        else [os.path.join(ROOT, 'Core'), os.path.join(ROOT, 'Locales')]

    targets, skipped = [], []
    for p in walk(roots):
        if is_vendor(p):
            skipped.append(p)
            continue
        if (not include_libhui) and p.replace('\\', '/').startswith(
                os.path.join(ROOT, 'Libs').replace('\\', '/') + '/LibHUI/'):
            skipped.append(p)
            continue
        targets.append(p)

    print('范围：待处理 %d 个；跳过第三方/未启用 %d 个' % (len(targets), len(skipped)))
    tot_o = tot_t = tot_l = 0
    unsafe = []
    for p in sorted(targets):
        with open(p, 'rb') as f:
            raw = f.read()
        text = raw.decode('utf-8')
        new, only, tail = strip_all_text(text)
        if new == text:
            continue
        if code_projection(text) != code_projection(new):
            unsafe.append(os.path.relpath(p, ROOT).replace('\\', '/'))
            continue
        d = text.count('\n') - new.count('\n')
        tot_o += only
        tot_t += tail
        tot_l += d
        rel = os.path.relpath(p, ROOT).replace('\\', '/')
        if only or tail:
            print('  %-46s -%4d 行（整行 %d / 行尾 %d）' % (rel, d, only, tail))
        if apply:
            with open(p, 'wb') as f:
                f.write(new.encode('utf-8'))
    print('-' * 78)
    if unsafe:
        print('!! 代码投影不一致，拒绝写盘的文件：', unsafe)
        return 2
    print('%s：整行注释 %d 行 + 行尾注释 %d 处，共减少 %d 行'
          % ('已落盘' if apply else '（dry-run 未落盘）', tot_o, tot_t, tot_l))
    return 0


if __name__ == '__main__':
    sys.exit(main())
