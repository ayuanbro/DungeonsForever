# -*- coding: utf-8 -*-
"""从 Data_DungeonQuests 补 GearSrcQLv / GearSrcQ / GearQuestRace 缺口。

背景：定制副本（达拉然城等）的任务不在 QuestieDB / GQF 事实源里，
gen_gear_src.py 推不出接取等级 ⇒ GearSrcQLv 缺条 ⇒ BIS/装备库的等级门控
放行了 req0/1 的达拉然任务奖励（15 级池出现 28 级本内容）。

口径：
  GearSrcQLv[id] = 任务接取等级（可多任务奖励同一物品，取最小 minLv）
  GearSrcQ[id]   = 奖励该物品的任务 ID（取 minLv 最小的那条）
  GearQuestRace[qid] = "a"/"h"（任务限阵营才写）

三份 Core/Data{,/zhTW,/enUS}/Data_Gear.lua 的三张表行整行重写为同一份合并结果。
幂等：已存在的键一律不动（setdefault 语义）。
用法：python gen_qlv_from_quests.py [--check]
"""
import os
import re
import shutil
import sys
from lupa import lua51

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "Core", "Data")
FILES = [
    os.path.join(DATA, "Data_Gear.lua"),
    os.path.join(DATA, "zhTW", "Data_Gear.lua"),
    os.path.join(DATA, "enUS", "Data_Gear.lua"),
]
BAK_DIR = os.path.join(HERE, "_bak_gen_qlv")

CHECK_ONLY = "--check" in sys.argv


def load_lua_varargs(path, holder):
    L = lua51.LuaRuntime()
    t = L.table()
    L.globals()[holder] = t
    src = open(path, "rb").read().decode("utf-8", "replace")
    f = L.eval(
        "function(src, name, holder) "
        " local f, err = loadstring(src, name) "
        " if not f then error(err) end "
        " return f(holder, holder) end")(
        src, os.path.basename(path), t)
    return L, t


def parse_kv_line(line):
    out = {}
    for m in re.finditer(r"\[(\d+)\]=(\d+)", line):
        out[int(m.group(1))] = int(m.group(2))
    return out


def parse_ah_line(line):
    out = {}
    for m in re.finditer(r'\[(\d+)\]="([ah])"', line):
        out[int(m.group(1))] = m.group(2)
    return out


def render_kv(title, tab):
    parts = ["[%d]=%d" % (k, tab[k]) for k in sorted(tab)]
    return title + " { " + ", ".join(parts) + " }"


def render_ah(title, tab):
    parts = ['[%d]="%s"' % (k, tab[k]) for k in sorted(tab)]
    return title + " { " + ", ".join(parts) + " }"


def collect_rw_bis(rw):
    Lb, nsb = load_lua_varargs(os.path.join(DATA, "Data_BIS.lua"), "NSB")
    ltype = Lb.eval("type")
    bis = nsb.EnsureBISData()
    n = [0]

    def walk(t):
        if t is None:
            return
        for _, v in t.items():
            if ltype(v) != "table":
                continue
            sv = v["src"]
            if sv is not None and str(sv["t"]) == "quest" \
                    and sv["q"] is not None and v["item"] is not None:
                qid = int(str(sv["q"]))
                note = sv["note"]
                minlv = None
                if note is not None:
                    m = re.search(r"(\d+)级起", str(note))
                    if m:
                        minlv = int(m.group(1))
                if minlv is None:
                    minlv = 60
                iid = int(v["item"])
                side = v["side"]
                cur = rw.get(iid)
                if cur is None or minlv < cur[0]:
                    rw[iid] = (minlv, qid, side)
                n[0] += 1
            walk(v)

    walk(bis)
    print("Data_BIS 任务行并入：%d 条引用" % n[0])


def main():
    Lq, nsq = load_lua_varargs(
        os.path.join(DATA, "Data_DungeonQuests.lua"), "NSQ")
    DQ = nsq["DungeonQuests"]
    Lg, nsg = load_lua_varargs(FILES[0], "NSG")
    nsg.EnsureGearData()
    src = nsg["GearData"]["src"]
    qlv = dict(parse_kv_line(find_line(FILES[0], "ns.GearSrcQLv = {")))
    srcq = dict(parse_kv_line(find_line(FILES[0], "ns.GearSrcQ = {")))
    race = parse_ah_line(find_line(FILES[0], "ns.GearQuestRace = {"))

    rw = {}
    ndung = 0
    for dk in DQ.keys():
        rows = DQ[dk]
        if rows is None:
            continue
        ndung += 1
        for ri in rows.keys():
            row = rows[ri]
            qid = int(row[1])
            side = row[2]
            if row[3] is None:
                continue
            minlv = int(row[3])
            rewards = row[10]
            if rewards is None:
                continue
            for ii in rewards.keys():
                iid = int(rewards[ii])
                cur = rw.get(iid)
                if cur is None or minlv < cur[0]:
                    rw[iid] = (minlv, qid, side)

    collect_rw_bis(rw)
    add_q = add_s = add_r = 0
    samples = {}
    for iid in sorted(rw):
        s = src[iid] if src[iid] is not None else None
        if s is None or not str(s).startswith("任务奖励"):
            continue
        minlv, qid, side = rw[iid]
        if iid not in qlv:
            qlv[iid] = minlv
            add_q += 1
            samples.setdefault(str(s), []).append(iid)
        if iid not in srcq:
            srcq[iid] = qid
            add_s += 1
        if side is not None and str(side) in ("A", "H") and qid not in race:
            race[qid] = str(side).lower()
            add_r += 1

    print("副本 %d 个；任务奖励物品 %d 个有归属" % (ndung, len(rw)))
    print("新增 GearSrcQLv %d / GearSrcQ %d / GearQuestRace %d"
          % (add_q, add_s, add_r))
    for k in sorted(samples):
        print("  %s: +%d" % (k, len(samples[k])))
    if CHECK_ONLY or add_q + add_s + add_r == 0:
        print("check 模式或无差异，不写文件")
        return

    if not os.path.isdir(BAK_DIR):
        os.makedirs(BAK_DIR)
    q_line = render_kv("ns.GearSrcQLv =", qlv)
    s_line = render_kv("ns.GearSrcQ =", srcq)
    r_line = render_ah("ns.GearQuestRace =", race)
    for p in FILES:
        shutil.copyfile(p, os.path.join(BAK_DIR, os.path.basename(
            os.path.dirname(p)) + "_" + os.path.basename(p)))
        lines = open(p, "rb").read().decode("utf-8").split("\n")
        for i, ln in enumerate(lines):
            if ln.startswith("ns.GearSrcQLv = {"):
                lines[i] = q_line
            elif ln.startswith("ns.GearSrcQ = {"):
                lines[i] = s_line
            elif ln.startswith("ns.GearQuestRace = {"):
                lines[i] = r_line
        open(p, "wb").write("\n".join(lines).encode("utf-8"))
        print("written", p)


def find_line(path, prefix):
    for ln in open(path, "rb").read().decode("utf-8").split("\n"):
        if ln.startswith(prefix):
            return ln
    raise SystemExit("line not found: " + prefix)


if __name__ == "__main__":
    main()
