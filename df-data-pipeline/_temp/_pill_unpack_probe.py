# -*- coding: utf-8 -*-
"""非恒真证明：把 Unpack 非末位实参的**旧写法**注回去，新断言必须变红。

隔离副本树 + DF_ADDON_ROOT 重定向；只碰临时副本，产品文件零改动。
"""
import os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
PY = sys.executable

FIXED_LINE = b'                local okr, okg, okb = Unpack(C_OK)\n'
BROKEN_LINE = b'                local okr, okg, okb = Unpack(C_OK)\n'  # placeholder

# 把「先接住三通道」改回「Unpack 直接当非末位实参」
OLD_BLOCK = (b'                -- \xe2\x98\x85 Unpack \xe5\xa4\x84\xe4\xba\x8e\xe9\x9d\x9e\xe6\x9c\xab\xe4\xbd\x8d\xe5\xae\x9e\xe5\x8f\x82\xe6\x97\xb6 Lua '
             b'\xe5\x8f\xaa\xe5\xb1\x95\xe5\xbc\x80\xe9\xa6\x96\xe5\x80\xbc\xef\xbc\x88g \xe6\x8e\xa5\xe6\x94\xb6 0.5\xe3\x80\x81b \xe4\xb8\xba nil\xef\xbc\x89\n'
             b'                -- \xe2\x86\x92 \xe5\xbf\x85\xe9\xa1\xbb\xe5\x85\x88\xe6\x8e\xa5\xe4\xbd\x8f\xe4\xb8\x89\xe9\x80\x9a\xe9\x81\x93\xe5\x86\x8d\xe4\xbc\xa0 a\xe3\x80\x82\n'
             b'                local okr, okg, okb = Unpack(C_OK)\n'
             b'                pill(miss, rowsShopMissBg[n + 1], L["\xe5\xb7\xb2\xe5\xa4\x87\xe9\xbd\x90"],'
             b' xMiss, missW, okr, okg, okb, 0.5)\n')
NEW_BLOCK = (b'                pill(miss, rowsShopMissBg[n + 1], L["\xe5\xb7\xb2\xe5\xa4\x87\xe9\xbd\x90"],'
             b' xMiss, missW, Unpack(C_OK), 0.5)\n')


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
    # 基准：源仓（已修）
    base_out = run(SRC)
    base = fails(base_out)
    print('基准（已修）失败 %d 条' % len(base))

    tmp = tempfile.mkdtemp(prefix='dfpill_')
    dst = os.path.join(tmp, 'DungeonsForever')
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns(
        '.git', '.workbuddy', '__pycache__', '_temp'))
    # 把补丁脚本与冒烟也带过去（冒烟从 ..\_temp 找 df_dungeon_check，需要同构目录）
    os.makedirs(os.path.join(tmp, '_temp'), exist_ok=True)
    for f in ('df_dungeon_check.py', 'tf_dryrun.py', '_hud_routemode_smoke.py'):
        shutil.copy(os.path.join(HERE, f), os.path.join(tmp, '_temp', f))
    src_pf = os.path.join(tmp, '_temp', '_hud_routemode_smoke.py')
    s = open(src_pf, encoding='utf-8').read().replace(
        "import df_dungeon_check as D", "import df_dungeon_check as D")
    open(src_pf, 'w', encoding='utf-8').write(s)

    p = os.path.join(dst, 'Core', 'ProfFollow.lua')
    b = open(p, 'rb').read()
    assert b.count(OLD_BLOCK) == 1, '修好的块没找到'
    open(p, 'wb').write(b.replace(OLD_BLOCK, NEW_BLOCK, 1))

    mut_out = run(dst)
    mut = fails(mut_out)
    new = mut - base
    print('注入旧写法后失败 %d 条，其中新增 %d 条：' % (len(mut), len(new)))
    for n in sorted(new):
        print('  ✗ %s' % n)

    ok = len(new) >= 2 and any('非末位实参' in n for n in new)
    print('=' * 56)
    print('非恒真：%s' % ('注入即变红（新断言单独抓住）' if ok else '★ 白测！新断言没抓住'))
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
