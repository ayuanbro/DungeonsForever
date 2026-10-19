# -*- coding: utf-8 -*-
"""临时探针：判定 zhTW 覆盖层与源文件的一致性口径（不改任何产品文件）。"""
import os
import sys
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_zhtw_data as G  # noqa

DF = os.path.dirname(HERE)
SRC = os.path.join(DF, 'Core', 'Data', 'Data_LootFilter.lua')
ZHTW = os.path.join(DF, 'Core', 'Data', 'zhTW', 'Data_LootFilter.lua')


def read(p):
    return open(p, 'rb').read().decode('utf-8')


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def split_code_comment(line):
    """复刻 gen_zhtw_data.process 的行内 code/comment 切分（字符串感知）。"""
    code, comment = line, ''
    in_str = False
    i = 0
    while i < len(line):
        c = line[i]
        if c == '\\' and in_str:
            i += 2
            continue
        if c in ('"', "'"):
            in_str = not in_str
        elif not in_str and line[i:i + 2] == '--':
            code, comment = line[:i], line[i:]
            break
        i += 1
    return code, comment


def convert_source(src_text):
    nl = '\r\n' if '\r\n' in src_text else '\n'
    lines = src_text.split(nl)
    out = []
    for line in lines:
        code, comment = split_code_comment(line)
        nc, _ = G.convert_line(code)
        out.append(nc + comment)
    return out


def strip_comment_lines(lines):
    """去掉整行注释（lstrip 后以 -- 开头）与空行；行内注释原样保留。"""
    res = []
    for l in lines:
        s = l.rstrip()
        if s.strip() == '':
            continue
        if s.lstrip().startswith('--'):
            continue
        res.append(s)
    return res


def strip_all_comments(lines):
    """去整行注释 + 行内注释 + 空行。"""
    res = []
    for l in lines:
        code, _ = split_code_comment(l)
        code = code.rstrip()
        if code.strip() == '':
            continue
        res.append(code)
    return res


def main():
    src_text = read(SRC)
    zhtw_text = read(ZHTW)
    print('src  bytes=%d md5=%s' % (len(src_text.encode('utf-8')), md5(SRC)))
    print('zhTW bytes=%d md5=%s' % (len(zhtw_text.encode('utf-8')), md5(ZHTW)))
    print('src  lines=%d  zhTW lines=%d' % (len(src_text.split('\n')), len(zhtw_text.split('\n'))))

    conv = convert_source(src_text)
    zlines = zhtw_text.split('\n')
    # 去掉 zhTW 的守卫头：前 12 行（6 注释 + 2 守卫代码 + 空行）
    for g in (10, 11, 12, 13):
        body = zlines[g:]
        print('--- zhTW guard cut = %d ; head[:%d]=%r' % (g, g, zlines[:g]))

    # 找守卫结束位置：首个含 "local gl" 的行之后
    gi = next(i for i, l in enumerate(zlines) if 'local gl' in l)
    body = zlines[gi + 2:]
    print('guard idx=%d ; guard lines shown below:' % gi)
    for l in zlines[:gi + 2]:
        print('   |' + l)
    print('body first non-empty:', next(l for l in body if l.strip()))

    print('zhTW full (incl guard) strip_all_comments =', len(strip_all_comments(zlines)))
    print('zhTW body strip_all_comments =', len(strip_all_comments(body)))
    print('conv strip_all_comments =', len(strip_all_comments(conv)))

    for nm, fn in (('strip_comment_lines', strip_comment_lines), ('strip_all_comments', strip_all_comments)):
        a = fn(conv)
        b = fn(body)
        print('== normalization=%s : conv=%d lines  zhTWbody=%d lines  equal=%s'
              % (nm, len(a), len(b), a == b))
        if a != b:
            for i in range(max(len(a), len(b))):
                x = a[i] if i < len(a) else '<none>'
                y = b[i] if i < len(b) else '<none>'
                if x != y:
                    print('   first diff @%d:\n     conv=%r\n     zhTW=%r' % (i, x, y))
                    break


if __name__ == '__main__':
    main()
