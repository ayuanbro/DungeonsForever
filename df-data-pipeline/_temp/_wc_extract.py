"""提取「哀嚎洞穴」地图 → PNG，落桌面，两条来源对比：

A. 我们插件（DungeonsForever）：运行时引用客户端 CASC 的
   Interface\\WorldMap\\WailingCaverns\\WailingCaverns1_1..12（经 lycheedev 导出）。
B. 参考插件（Lootified）：自带 Media/Maps/WailingCaverns/WailingCaverns1_1..12.blp
   （BLP2 无压缩调色板，128x128）。

各按 4 列 x 3 行拼 1024x768 / 512x384，再按插件同口径裁掉装饰边
（右 22 / 底 100 → 1002x668）；另做一次逐瓦片像素比对，回答
「参考插件是不是直接从客户端抠图」。
"""
import json
import os
import re
import struct
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
INSTALL = r"D:/Game/World of Warcraft/_classic_beta_"
LOOT = os.path.join(INSTALL, "Interface", "AddOns", "Lootified",
                    "Media", "Maps", "WailingCaverns")
DESKTOP = r"C:/Users/Administrator/Desktop"
WORK = os.path.join(HERE, "_wc_tiles")

# 与 _mapprobe_fetch.py 同一套 lycheedev 环境
LYCHEEDEV = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-6/lycheedev.cmd"
HOME = r"D:\workspace\project-021-lycheedev\data\lycheedev-home"
PIN = "PIN-843be35b75b0b2d37579a38fcee3dbfa8826b2983016871008ba931f91302655"  # 2026-10-10 重解析

CROP = (1002, 668)          # 插件实裁的有效画面
GRID = (4, 3)               # 12 块 = 4 列 x 3 行，行优先


def lychee(args):
    env = dict(os.environ)
    env["LYCHEEDEV_HOME"] = HOME
    p = subprocess.run([LYCHEEDEV] + args, capture_output=True, text=True, env=env)
    try:
        return json.loads(p.stdout)
    except Exception:
        print("RAW STDOUT:", p.stdout[:1500])
        print("RAW STDERR:", p.stderr[:1500])
        raise


def blp2pil(path):
    """Lootified 的「BLP2」（compression=1/encoding=2 实为 DXT1 数据）→ PIL RGB"""
    import _wc_dxt
    return _wc_dxt.lootified_blp(path)


def export_client_tiles():
    os.makedirs(WORK, exist_ok=True)
    d = lychee(["asset", "search", "--snapshot", PIN, "--listfile", "community-csv",
                "--query", "interface/worldmap/wailingcaverns/", "--limit", "60",
                "--format", "json"])
    assert d.get("ok"), d.get("error")
    rx = re.compile(r"^interface/worldmap/wailingcaverns/wailingcaverns1_(\d+)\.blp$")
    tiles = {}
    for f in d["result"].get("files") or []:
        m = rx.match(f["fileName"])
        if m:
            tiles[int(m.group(1))] = f["fileDataID"]
    idxs = sorted(tiles)
    print("客户端 CASC：哀嚎瓦片 %d 块 %s" % (len(idxs), idxs))
    out = []
    for i in idxs:
        p = os.path.join(WORK, "client_%02d.png" % i)
        if not os.path.exists(p):
            r = lychee(["asset", "export", "--snapshot", PIN, "--installation", INSTALL,
                        "--file-id", str(tiles[i]), "--encoding", "png",
                        "--output", p, "--format", "json"])
            assert r.get("ok"), "export %d: %s" % (tiles[i], r.get("error"))
        out.append(Image.open(p).convert("RGBA"))
    return out


def stitch(imgs, grid):
    cols, rows = grid
    w, h = imgs[0].size
    canvas = Image.new("RGBA", (cols * w, rows * h), (0, 0, 0, 255))
    for n, im in enumerate(imgs):
        canvas.paste(im.convert("RGBA"), ((n % cols) * w, (n // cols) * h))
    return canvas


def main():
    print("== A. 我们插件口径（客户端 CASC 官方瓦片）==")
    client = export_client_tiles()

    print("== B. 参考插件自带 BLP ==")
    loot = []
    for i in range(1, 13):
        p = os.path.join(LOOT, "WailingCaverns1_%d.blp" % i)
        loot.append(blp2pil(p))
    print("Lootified：12 块，单块 %s" % (loot[0].size,))

    # 拼图 + 按插件口径裁边（比例随画布缩放：参考图整图 512x384 = 客户端一半）
    for tag, name, imgs in (("client", "我们插件_客户端原图", client),
                            ("lootified", "参考插件_自带图", loot)):
        full = stitch(imgs, GRID)
        cw = round(full.size[0] * CROP[0] / (GRID[0] * 256))
        ch = round(full.size[1] * CROP[1] / (GRID[1] * 256))
        full.save(os.path.join(DESKTOP, "哀嚎洞穴_%s_整图.png" % name))
        full.crop((0, 0, cw, ch)).save(
            os.path.join(DESKTOP, "哀嚎洞穴_%s_插件实显.png" % name))
        print("  %s：整图 %s → 实显 %dx%d 已落桌面" % (name, full.size, cw, ch))

    # 逐瓦片比对：参考插件是否 = 客户端原图
    print("== 像素比对（参考 vs 客户端原版）==")
    same = 0
    for i, (a, b) in enumerate(zip(client, loot), 1):
        ca = np.asarray(a.convert("RGB").resize(b.size)).astype(np.int16)
        cb = np.asarray(b.convert("RGB")).astype(np.int16)
        diff = np.abs(ca - cb)
        pct = (diff.max(axis=2) <= 8).mean() * 100
        print("  瓦片 %02d：接近像素 %.1f%%（均值差 %.1f）" % (i, pct, diff.mean()))
        if pct > 95:
            same += 1
    print("结论：%d/12 块基本一致" % same)


if __name__ == "__main__":
    sys.exit(main())
