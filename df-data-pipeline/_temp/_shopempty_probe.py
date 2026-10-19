# -*- coding: utf-8 -*-
"""非恒真证明（2026-10-11 购物清单空清单）：把「n==0 就 Hide」的旧行为注回去，
新断言必须变红。

隔离副本树 + DF_ADDON_ROOT 重定向；只碰临时副本，产品文件零改动。

用法：python _temp/_shopempty_probe.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
PY = sys.executable

# 修好的空清单分支（当前产品写法）
OLD_BLOCK = (
    '            f.shop.empty:SetText(#list > 0 and L["所有物品已备齐"] or L["无材料"])\n'
    '            f.shop.empty:Show()\n'
    '            local shopH = 30 + 20 + 10\n'
    '            f.shop:ClearAllPoints()\n'
    '            f.shop:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, y)\n'
    '            f.shop:SetSize(W - 2 * PAD, shopH)\n'
    '            f.shop:Show()\n'
    '            y = y - shopH - 8\n'
).encode('utf-8')
# 旧行为：空清单直接把面板藏掉（= 用户报的「永远点不开」）
NEW_BLOCK = b'            f.shop:Hide()\n'


def run(addon):
    env = dict(os.environ, DF_ADDON_ROOT=addon)
    p = subprocess.run([PY, os.path.join(HERE, '_hud_routemode_smoke.py')],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', env=env)
    return p.stdout or ''


def fails(out):
    got = set()
    for line in out.splitlines():
        s = line.strip()
        if s.startswith('[FAIL]'):
            got.add(s[6:].strip().split('  [')[0])
    return got


def main():
    base_out = run(SRC)
    base = fails(base_out)
    print('基准（已修）失败 %d 条' % len(base))

    tmp = tempfile.mkdtemp(prefix='dfshopempty_')
    dst = os.path.join(tmp, 'DungeonsForever')
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns(
        '.git', '.workbuddy', '__pycache__', '_temp'))
    os.makedirs(os.path.join(tmp, '_temp'), exist_ok=True)
    for f in ('df_dungeon_check.py', 'tf_dryrun.py', '_hud_routemode_smoke.py'):
        shutil.copy(os.path.join(HERE, f), os.path.join(tmp, '_temp', f))

    p = os.path.join(dst, 'Core', 'ProfFollow.lua')
    b = open(p, 'rb').read()
    assert b.count(OLD_BLOCK) == 1, '修好的空清单块没找到（锚点变了？）'
    open(p, 'wb').write(b.replace(OLD_BLOCK, NEW_BLOCK, 1))

    mut_out = run(dst)
    mut = fails(mut_out)
    new = mut - base
    print('注入旧写法后失败 %d 条，其中新增 %d 条：' % (len(mut), len(new)))
    for n in sorted(new):
        print('  ✗ %s' % n)

    ok = len(new) >= 1 and any('永远点不开' in n for n in new)
    print('=' * 56)
    print('非恒真：%s' % ('注入即变红（新断言单独抓住）' if ok
                        else '★ 白测！新断言没抓住'))
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
