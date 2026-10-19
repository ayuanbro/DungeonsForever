# -*- coding: utf-8 -*-
"""MapProbe 变异测试（非恒真证明）：改行为的变异必须被判红。

用法：python _mapprobe_mut.py
锚点一律选 ASCII 安全 / 无反斜杠的代码段，避免 shell+JSON 双重转义吃掉字符。
"""
import io
import os
import subprocess
import sys

PY = r"C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/MapProbe/MapProbe.lua"
MUTDIR = os.path.join(HERE, "_mapprobe_mut")

# (说明, [(old, new), ...])；每对 old 必须字节精确命中 1 次
MUTS = [
    ("领主大厅/旧铁炉堡别名整条失效", [
        ('zh = "旧铁炉堡 · 领主大厅"', 'zh = "X"'),
        ('"领主大厅", "oldironforge", "thanes", "hallofthanes" }',
         '"oldironforge", "thanes", "hallofthanes" }'),
    ]),
    ("旧铁炉堡路径前缀写错", [
        (r'prefix = "Interface\\WorldMap\\OldIronforge\\OldIronforge"',
         r'prefix = "Interface\\WorldMap\\OldIronforgeX\\OldIronforge"'),
    ]),
    ("别名 oif 写错", [
        ('alias = "oif"', 'alias = "oifX"'),
    ]),
    ("网格 4x3 换成 3x4", [
        ("local GRID_COLS, GRID_ROWS = 4, 3", "local GRID_COLS, GRID_ROWS = 3, 4"),
    ]),
    ("拿不到 ID 时不再退回路径", [
        ("local use = (item.fid and item.fid > 0) and item.fid or item.path", "local use = item.fid"),
    ]),
    ("me 不报坐标（改用块号）", [
        ('Print(string.format("  坐标 → x=%.4f y=%.4f   （%.1f%%, %.1f%%）", px, py, px * 100, py * 100))',
         'Print("  坐标 → 0")'),
    ]),
    ("inv 里领主大厅路径写错", [
        (r'{ "领主大厅",      "Interface\\WorldMap\\OldIronforge\\OldIronforge" }',
         r'{ "领主大厅",      "Interface\\WorldMap\\OldIronforgeX\\OldIronforge" }'),
    ]),
    ("inv 逐块循环只数 11 块", [
        ("local function CountPrefix(prefix)\n    local hit = 0\n    for n = 1, NB_TILES do",
         "local function CountPrefix(prefix)\n    local hit = 0\n    for n = 1, NB_TILES - 1 do"),
    ]),
]


def run(probe):
    env = dict(os.environ, MAPPROBE_LUA=os.path.abspath(probe))
    r = subprocess.run([PY, os.path.join(HERE, "_mapprobe_check.py")],
                       capture_output=True, text=True, env=env, cwd=HERE)
    lines = [l for l in r.stdout.splitlines() if "通过" in l and "失败" in l]
    return r.returncode, (lines[-1] if lines else "(无统计)")


def main():
    base = io.open(PROBE, encoding="utf-8").read()
    if not os.path.isdir(MUTDIR):
        os.makedirs(MUTDIR)
    rc, stat = run(PROBE)
    print("基线           exit=%d  %s" % (rc, stat))
    bad = 0
    for name, pairs in MUTS:
        txt = base
        for old, new in pairs:
            n = txt.count(old)
            if n != 1:
                print("%-24s 锚点命中 %d 次（跳过）" % (name, n))
                bad += 1
                txt = None
                break
            txt = txt.replace(old, new)
        if txt is None:
            continue
        p = os.path.join(MUTDIR, "mutant.lua")
        io.open(p, "w", encoding="utf-8").write(txt)
        rc, stat = run(p)
        killed = rc != 0
        print("%-24s exit=%d %-18s %s" % (name, rc, stat, "已判红 ✓" if killed else "★漏检★"))
        if not killed:
            bad += 1
    print("\n变异体全部被杀" if bad == 0 else "\n有 %d 条没被杀/没生效" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
