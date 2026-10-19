# -*- coding: utf-8 -*-
"""把每个副本每层的地图底图导出成 _route_plan/img/maps/<dungeonId>_<层号>.jpg

来源三路：
  ART             客户端 CASC 的 Interface\\WorldMap\\<dir>\\<layer><n>.blp，12 块 256 拼 4x3 再裁 1002x668
  CUSTOM          自制整图 Media\\Maps\\*.tga（单层）
  CUSTOM_FLOOR    自制整图但按层挂（覆盖 ART 的对应层）
"""
import io
import json
import os
import re
import subprocess
import sys

from PIL import Image

ROOT = 'D:/workspace/DungeonsForever'
MAPUI = ROOT + '/Core/MapUI.lua'
MEDIA = ROOT + '/Media/Maps'
INV = ROOT + '/_temp/_map_inv.json'
CACHE = ROOT + '/_temp/_mapbake'
OUT = ROOT + '/_temp/_route_plan/img/maps'

LYCH = r'C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-6/lycheedev'
PIN = 'PIN-b8df92449fdc30df27327253cb594807d3dfeb6a4067a8da3f48453c5d923329'
INST = 'D:/Game/World of Warcraft/_classic_beta_'
HOME = r'D:\workspace\project-021-lycheedev\data\lycheedev-home'

ART_W, ART_H = 1002, 668
TILE = 256
COLS, ROWS = 4, 3

env = dict(os.environ, LYCHEEDEV_HOME=HOME)


def parse_lua_tables():
    s = io.open(MAPUI, encoding='utf-8').read()

    def block(name):
        m = re.search(r'from_start', name)
        return None

    dm = re.search(r'local DM = \{ "([^"]+)",\s*\{([^}]*)\} \}', s)
    st = re.search(r'local ST = \{ "([^"]+)", \{([^}]*)\} \}', s)
    smdir = re.search(r'local SM_DIR = "([^"]+)"', s)

    DM = [dm.group(1).strip()] + [x.strip().strip('"') for x in dm.group(2).split(',') if x.strip()]
    ST = [st.group(1).strip()] + [x.strip().strip('"') for x in st.group(2).split(',') if x.strip()]
    SMD = smdir.group(1).strip()

    m = re.search(r'^local ART = \{(.*?)\n\}', s, re.S | re.M)
    body = m.group(1)
    art = {}
    for line in body.split('\n'):
        line = line.strip()
        mm = re.match(r'^(\w+)\s*=\s*\{\s*"([^"]+)",\s*\{([^}]*)\}\s*\},?$', line)
        if mm:
            art[mm.group(1)] = [mm.group(2)] + [x.strip().strip('"') for x in mm.group(3).split(',') if x.strip()]
            continue
        mm = re.match(r'^(\w+)\s*=\s*(DM|ST)\s*,?$', line)
        if mm:
            art[mm.group(1)] = DM if mm.group(2) == 'DM' else ST
            continue
        mm = re.match(r'^(\w+)\s*=\s*SMW\("([^"]+)"\)\s*,?$', line)
        if mm:
            art[mm.group(1)] = [SMD, [mm.group(2)]]
            continue
    # 多行写法（shadowfang / gnomeregan 等）单独补
    for mm in re.finditer(r'(\w+)\s*=\s*\{\s*"([^"]+)",\s*\n\s*\{([^}]*)\}\s*\}', body):
        layers = [x.strip().strip('"') for x in mm.group(3).split(',') if x.strip()]
        art.setdefault(mm.group(1), [mm.group(2)] + layers)

    def flat(v, out):
        for x in v:
            if isinstance(x, list):
                flat(x, out)
            elif isinstance(x, str):
                out.append(x)
        return out

    for k, v in list(art.items()):
        rest = flat(v[1:], [])
        art[k] = (v[0], rest)

    def simple(name):
        m = re.search(r'^local %s = \{(.*?)\n\}' % name, s, re.S | re.M)
        d = {}
        for line in m.group(1).split('\n'):
            mm = re.match(r'^\s*(\w+)\s*=\s*"([^"]+)",?$', line)
            if mm:
                d[mm.group(1)] = mm.group(2)
        return d

    custom = simple('CUSTOM')

    m = re.search(r'^local CUSTOM_FLOOR = \{(.*?)\n\}', s, re.S | re.M)
    cf = {}
    for mm in re.finditer(r'(\w+)\s*=\s*\{\s*\[(\d+)\]\s*=\s*"([^"]+)"', m.group(1)):
        cf.setdefault(mm.group(1), {})[int(mm.group(2))] = mm.group(3)
    return art, custom, cf


def tga_path(lua_path):
    name = lua_path.rsplit('\\', 1)[-1]
    return os.path.join(MEDIA, name + '.tga')


def export_tile(fid):
    f = os.path.join(CACHE, '%d.png' % fid)
    if os.path.exists(f) and os.path.getsize(f) > 500:
        return f
    os.makedirs(CACHE, exist_ok=True)
    r = subprocess.run([LYCH, 'asset', 'export', '--snapshot', PIN, '--installation', INST,
                        '--file-id', str(fid), '--encoding', 'png', '--output', f,
                        '--overwrite', '--format', 'json'],
                       capture_output=True, text=True, env=env, shell=True)
    if os.path.exists(f) and os.path.getsize(f) > 500:
        return f
    sys.stderr.write('tile %d FAIL %s\n' % (fid, (r.stdout or '')[-200:]))
    return None


def stitch(fids):
    canvas = Image.new('RGB', (TILE * COLS, TILE * ROWS), (0, 0, 0))
    got = 0
    for i in range(1, COLS * ROWS + 1):
        fid = fids.get(str(i))
        if not fid:
            continue
        p = export_tile(fid)
        if not p:
            continue
        im = Image.open(p).convert('RGB')
        if im.size != (TILE, TILE):
            im = im.resize((TILE, TILE), Image.LANCZOS)
        c = (i - 1) % COLS
        r = (i - 1) // COLS
        canvas.paste(im, (c * TILE, r * TILE))
        got += 1
    return canvas, got


def save_jpg(im, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.convert('RGB').save(path, 'JPEG', quality=88, optimize=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    art, custom, cf = parse_lua_tables()
    inv = json.load(io.open(INV, encoding='utf-8'))

    print('ART %d / CUSTOM %d / CUSTOM_FLOOR %d' % (len(art), len(custom), len(cf)))
    made, miss = 0, []

    for did, (adir, layers) in sorted(art.items()):
        cands = inv.get(did) or []
        groups = {}
        for c in cands:
            groups[c['base'].lower()] = c['fids']
        for i, layer in enumerate(layers, 1):
            if cf.get(did, {}).get(i):
                continue
            lp = os.path.join(OUT, '%s_%d.jpg' % (did, i))
            if os.path.exists(lp) and os.path.getsize(lp) > 8000:
                made += 1
                continue
            fids = groups.get(layer.lower())
            if not fids:
                miss.append('%s L%d %s (无瓦片清单)' % (did, i, layer))
                continue
            canvas, got = stitch(fids)
            if got < 6:
                miss.append('%s L%d %s (只导出 %d 块)' % (did, i, layer, got))
                continue
            save_jpg(canvas.crop((0, 0, ART_W, ART_H)), lp)
            made += 1
            print('  %-32s L%d  %s' % (did, i, layer), flush=True)

    for did, lua in sorted(custom.items()):
        src = tga_path(lua)
        if not os.path.exists(src):
            miss.append('%s 自制图缺失 %s' % (did, src))
            continue
        lp = os.path.join(OUT, '%s_1.jpg' % did)
        im = Image.open(src).convert('RGB').resize((ART_W, ART_H), Image.LANCZOS)
        save_jpg(im, lp)
        made += 1
        print('  %-32s L1  自制 %s' % (did, os.path.basename(src)), flush=True)

    for did, rows in sorted(cf.items()):
        for i, lua in sorted(rows.items()):
            src = tga_path(lua)
            if not os.path.exists(src):
                miss.append('%s 自制图缺失 %s' % (did, src))
                continue
            lp = os.path.join(OUT, '%s_%d.jpg' % (did, i))
            im = Image.open(src).convert('RGB').resize((ART_W, ART_H), Image.LANCZOS)
            save_jpg(im, lp)
            made += 1
            print('  %-32s L%d  自制 %s' % (did, i, os.path.basename(src)), flush=True)

    print('\n生成 %d 张' % made)
    if miss:
        print('未生成 %d：' % len(miss))
        for x in miss:
            print('  -', x)


if __name__ == '__main__':
    main()
