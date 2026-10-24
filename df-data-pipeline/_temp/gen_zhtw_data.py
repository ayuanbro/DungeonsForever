# -*- coding: utf-8 -*-
"""生成繁体数据副本：Core/Data/Data_*.lua → Core/Data/zhTW/Data_*.lua（生成物）。

机制（2026-09-25 本地化第 2 步）：
- 每个数据文件转换其中的 CJK 字符串字面量内容（TW 术语词表 + opencc s2t，
  与 gen_zhtw.py 的 UI 文案同一条管线，保证「数据 ↔ 代码 L 键」对查两侧一致）；
- 产物头部加 zhTW 守卫：仅繁体客户端加载并覆盖 ns.X，zhCN 客户端秒退；
  原文件不加守卫（zhTW 副本在 toc 里排在其后，加载时覆盖）；
- 注释不转换不检查（不上屏）；字符串里的转义引号 \\" 用字符级扫描处理。

用法：python gen_zhtw_data.py
"""
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_zhtw import to_tw  # noqa: E402  同一条词表 + opencc 管线

DF = os.path.dirname(HERE)
SRC_DIR = os.path.join(DF, 'Core', 'Data')
DST_DIR = os.path.join(DF, 'Core', 'Data', 'zhTW')

GUARD = (
    "local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'%s"
    "if gl ~= 'zhTW' then return end%s%s"
)


def convert_line(code):
    """字符串字面量内的 CJK 内容做简→繁；其余逐字节保留。返回 (新行, 转换数)。"""
    out = []
    n = 0
    i = 0
    L = len(code)
    while i < L:
        c = code[i]
        if c in ('"', "'"):
            q = c
            j = i + 1
            buf = []
            while j < L:
                if code[j] == '\\' and j + 1 < L:
                    buf.append(code[j:j + 2])
                    j += 2
                    continue
                if code[j] == q:
                    break
                buf.append(code[j])
                j += 1
            if j >= L:
                raise SystemExit('引号不配对（跨行串？）：%s' % code.rstrip())
            inner = ''.join(buf)
            tw = to_tw(inner)
            if tw != inner:
                n += 1
            out.append(q + tw + q)
            i = j + 1
        else:
            out.append(c)
            i += 1
    return ''.join(out), n


def process(name):
    src_path = os.path.join(SRC_DIR, name)
    src = open(src_path, 'rb').read().decode('utf-8')
    nl = '\r\n' if '\r\n' in src else '\n'
    lines = src.split(nl)
    total = 0
    out_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('--'):
            out_lines.append(line)
            continue
        # 行内注释段不转换：-- 在字符串外才算注释起点
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
        new_code, n = convert_line(code)
        total += n
        out_lines.append(new_code + comment)
    body = nl.join(out_lines)
    head = GUARD % ((nl,) * 3)
    dst = os.path.join(DST_DIR, name)
    open(dst, 'wb').write((head + body).encode('utf-8'))
    return total


def main():
    os.makedirs(DST_DIR, exist_ok=True)
    names = sorted(f for f in os.listdir(SRC_DIR)
                   if f.startswith('Data_') and f.endswith('.lua'))
    grand = 0
    for name in names:
        n = process(name)
        grand += n
        print('  %-28s 转换 %4d 处' % (name, n))
    print('共 %d 个文件、%d 条字符串转为繁体 → Core/Data/zhTW/' % (len(names), grand))




def _strip_comments_after_gen():
    """注释精简：**只清理本生成器写出的文件**（Core/Data/zhTW/Data_*.lua）。

    ★ 2026-09-29 收口（第五轮）：旧实现无条件重扫整个 Core/，副作用有二：
      (1) 剥掉 Core/Data/enUS/Data_ClassGuide.lua 的头部表结构注释块 —— 使上轮
          「还原 enUS 头块」**不幂等**（再跑一次 gen 又被剥）；
      (2) 剥掉并行会话手改文件（LootFilterUI / MainFrame / Core / LootFilter）的注释 —— 干扰他人。
      现限定为「本次实际生成的 zhTW 副本」白名单，杜绝上述外溢。
      注释口径本身不变：每个 Lua 只留文件头注释块（逻辑仍在 _temp/strip_comments.py）。
    """
    import os as _os
    import sys as _sys
    _here = _os.path.dirname(_os.path.abspath(__file__))
    if _here not in _sys.path:
        _sys.path.insert(0, _here)
    import strip_comments as _S
    names = sorted(f for f in _os.listdir(DST_DIR)
                   if f.startswith('Data_') and f.endswith('.lua'))
    n = 0
    for _p in _S.walk([_os.path.join(DST_DIR, name) for name in names]):
        _raw = open(_p, 'rb').read()
        _txt = _raw.decode('utf-8')
        _new, _c, _t = _S.strip_all_text(_txt)
        if _new != _txt:
            open(_p, 'wb').write(_new.encode('utf-8'))
            n += 1
    if n:
        print('注释精简：收尾清理 %d 个文件（仅 zhTW 副本）' % n)


if __name__ == '__main__':
    from fc_locales import locale_cli
    locale_cli('zhTW')
