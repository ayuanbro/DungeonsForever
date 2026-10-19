import json
import os
import re
import subprocess
import sys

LYCHEEDEV = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-6/lycheedev.cmd"
HOME = r"D:\workspace\project-021-lycheedev\data\lycheedev-home"
INSTALL = r"D:/Game/World of Warcraft/_classic_beta_"
PIN = "PIN-e1b150d1f6e9c2658a90ee87b326d352ef99b3b93331516c53aca16595a1a37e"
OUT = r"D:/workspace/DungeonsForever/_temp/_route_preview_png"


def run(args):
    env = dict(os.environ)
    env["LYCHEEDEV_HOME"] = HOME
    p = subprocess.run([LYCHEEDEV] + args, capture_output=True, text=True, env=env)
    try:
        return json.loads(p.stdout)
    except Exception:
        print("RAW STDOUT:", p.stdout[:3000])
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
    from PIL import Image

    q = sys.argv[1] if len(sys.argv) > 1 else "interface/worldmap/blackfathomdeeps/"
    prefix = sys.argv[2] if len(sys.argv) > 2 else "BlackfathomDeeps"
    files = search(q)
    rx = re.compile(r"^interface/worldmap/[^/]+/%s(\d+)_(\d+)\.blp$" % prefix.lower())
    layers = {}
    for f in files:
        m = rx.match(f["fileName"])
        if m:
            layers.setdefault(int(m.group(1)), {})[int(m.group(2))] = f["fileDataID"]
    if not layers:
        print("no tiles; sample files:")
        for f in files[:20]:
            print("  ", f["fileName"])
        raise SystemExit(1)
    os.makedirs(OUT, exist_ok=True)
    for lay in sorted(layers):
        tiles = layers[lay]
        idxs = sorted(tiles)
        print("layer %d -> %d tiles" % (lay, len(idxs)))
        d = os.path.join(OUT, "%s_L%d" % (prefix, lay))
        os.makedirs(d, exist_ok=True)
        paths = {}
        for i in idxs:
            p = os.path.join(d, "t%02d.png" % i)
            export(tiles[i], p)
            paths[i] = p
        im0 = Image.open(paths[idxs[0]])
        w, h = im0.size
        cols = 4 if len(idxs) == 12 else len(idxs)
        rows = (len(idxs) + cols - 1) // cols
        canvas = Image.new("RGBA", (cols * w, rows * h), (0, 0, 0, 0))
        for n, i in enumerate(idxs):
            canvas.paste(Image.open(paths[i]).convert("RGBA"), ((n % cols) * w, (n // cols) * h))
        out = os.path.join(OUT, "%s_L%d.png" % (prefix, lay))
        canvas.save(out)
        print("   %dx%d tiles -> %s" % (w, h, out))


if __name__ == "__main__":
    main()
