# -*- coding: utf-8 -*-
"""QA 辅助：把打包集文件复制到变体目录，并按需打几何补丁，供 geom 探针复测。

用法：
  python _qa_variant_setup.py B     # 变体B：yCur=-46 保留 -34 锚点
  python _qa_variant_setup.py C44   # 变体：yCur=-44（2px 缝）
  python _qa_variant_setup.py C42   # 变体：yCur=-42（0px 缝）
"""
import os
import re
import shutil
import sys

SRC = r'D:\workspace\DungeonsForever'
DST = r'D:\workspace\_qa_variant'

PATCHES = {
    # key: (old_line_substring, new_line_substring, 期望出现次数)
    'B':  ('c:SetPoint("TOPLEFT", root, "TOPLEFT", x0, yCur)',
           'c:SetPoint("TOPLEFT", root, "TOPLEFT", x0, yCur - 34)', 1),
    'C44': ('local yCur = -46', 'local yCur = -44', 1),
    'C42': ('local yCur = -46', 'local yCur = -42', 1),
    'OLD': (('local yCur = -46', 'local yCur = -56'),
            ('c:SetPoint("TOPLEFT", root, "TOPLEFT", x0, yCur)',
             'c:SetPoint("TOPLEFT", root, "TOPLEFT", x0, yCur - 34)')),
}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'B'
    if os.path.isdir(DST):
        # 不整树删除（安全策略），直接覆写补丁目标文件
        pass
    toc = open(os.path.join(SRC, 'DungeonsForever.toc'),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]
    n = 0
    for rel in files:
        s = os.path.join(SRC, rel)
        if os.path.isfile(s):
            d = os.path.join(DST, rel)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n += 1
    shutil.copy2(os.path.join(SRC, 'DungeonsForever.toc'),
                 os.path.join(DST, 'DungeonsForever.toc'))
    print('copied %d files -> %s' % (n, DST))

    if mode in PATCHES:
        spec = PATCHES[mode]
        if mode == 'OLD':
            pairs = [(spec[0][0], spec[0][1], 1), (spec[1][0], spec[1][1], 1)]
        else:
            old, new, cnt = spec
            pairs = [(old, new, cnt)]
        p = os.path.join(DST, 'Core', 'ProfessionUI.lua')
        src = open(p, 'rb').read().decode('utf-8')
        for old, new, cnt in pairs:
            got = src.count(old)
            assert got == cnt, 'patch anchor %r count %d != %d' % (old, got, cnt)
            src = src.replace(old, new)
            print('variant %s patched: %r -> %r' % (mode, old, new))
        open(p, 'wb').write(src.encode('utf-8'))
    else:
        print('variant %s: no patch (baseline copy)' % mode)
    return 0


if __name__ == '__main__':
    sys.exit(main())
