"""从 beta 客户端 CASC 导出「湿地 / 怒焰裂谷」世界地图瓦片并拼成整图。

用法: python _mapprobe_fetch.py [--grid 4x3]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

LYCHEEDEV = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-3/lycheedev.cmd"
HOME = r"D:\workspace\project-021-lycheedev\data\lycheedev-home"
INSTALL = r"D:/Game/World of Warcraft/_classic_beta_"
PIN = "PIN-b4d284e3188d08779c84dd1537b28e34a57e2ff609b67a423c0204bd1d43bbeb"
OUT = r"D:/workspace/DungeonsForever/_temp/_mapprobe_png"

TARGETS = [
    {
        "key": "wetlands",
        "label": "湿地",
        "query": "interface/worldmap/wetlands/wetlands",
        "re": r"^interface/worldmap/wetlands/wetlands(\d+)\.blp$",
    },
    {
        "key": "wetlands_c60",
        "label": "湿地 · 1.60 重制",
        "query": "wetlands_c60",
        "re": r"^interface/worldmap/wetlands_c60/wetlands_c60(\d+)\.blp$",
    },
    {
        "key": "ragefire",
        "label": "怒焰裂谷",
        "query": "interface/worldmap/ragefire/",
        "re": r"^interface/worldmap/ragefire/ragefire1_(\d+)\.blp$",
    },
]


def run(args):
    env = dict(os.environ)
    env["LYCHEEDEV_HOME"] = HOME
    p = subprocess.run([LYCHEEDEV] + args, capture_output=True, text=True, env=env)
    try:
        return json.loads(p.stdout)
    except Exception:
        print("RAW STDOUT:", p.stdout[:2000])
        print("RAW STDERR:", p.stderr[:2000])
        raise


def search(query):
    d = run(["asset", "search", "--snapshot", PIN, "--listfile", "community-csv",
             "--query", query, "--limit", "200", "--format", "json"])
    if not d.get("ok"):
        raise SystemExit("search failed: %s" % d.get("error"))
    return d["result"].get("files") or []


def export(fid, path):
    if os.path.exists(path):
        return
    d = run(["asset", "export", "--snapshot", PIN, "--installation", INSTALL,
             "--file-id", str(fid), "--encoding", "png", "--output", path,
             "--format", "json"])
    if not d.get("ok"):
        raise SystemExit("export %s failed: %s" % (fid, d.get("error")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", default="")
    ap.add_argument("--no-stitch", action="store_true")
    args = ap.parse_args()

    from PIL import Image

    for t in TARGETS:
        files = search(t["query"])
        rx = re.compile(t["re"])
        tiles = {}
        for f in files:
            m = rx.match(f["fileName"])
            if m:
                tiles[int(m.group(1))] = f["fileDataID"]
        idxs = sorted(tiles)
        print("[%s] %s -> %d 块: %s" % (t["key"], t["label"], len(idxs), idxs))
        d = os.path.join(OUT, t["key"])
        os.makedirs(d, exist_ok=True)
        paths = {}
        for i in idxs:
            p = os.path.join(d, "%s_%02d.png" % (t["key"], i))
            export(tiles[i], p)
            paths[i] = p

        if args.no_stitch:
            continue

        im0 = Image.open(paths[idxs[0]])
        w, h = im0.size
        print("    单块尺寸 %dx%d" % (w, h))

        grid = args.grid
        if not grid:
            # 12 块最常见是 4 列 x 3 行（1024x768）
            cols = 4 if len(idxs) == 12 else len(idxs)
            rows = (len(idxs) + cols - 1) // cols
        else:
            c, r = grid.lower().split("x")
            cols, rows = int(c), int(r)
        print("    拼图 %d 列 x %d 行 -> %dx%d" % (cols, rows, cols * w, rows * h))

        canvas = Image.new("RGBA", (cols * w, rows * h), (0, 0, 0, 0))
        for n, i in enumerate(idxs):
            col, row = n % cols, n // cols
            canvas.paste(Image.open(paths[i]).convert("RGBA"), (col * w, row * h))
        out = os.path.join(OUT, "%s_%dx%d.png" % (t["key"], cols, rows))
        canvas.save(out)
        canvas.convert("RGB").save(os.path.join(OUT, "%s_full.jpg" % t["key"]), quality=92)
        print("    -> %s" % out)


if __name__ == "__main__":
    main()
