#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""把 _temp 下所有脚本里写死的「作者本机路径」批量改成本机路径。

只做字符串替换，不改任何逻辑。默认只统计，加 --apply 才写盘。

覆盖的路径（正斜杠 / 单反斜杠 / 双反斜杠三种写法都处理）：
    D:\workspace\DungeonsForever                     -> --root（默认本包目录）
    ...\_cn_beta_\...\ClassQuestsForever\Data         -> --cqf（默认 samples）
    D:\Game\World of Warcraft                         -> --wow
    D:\workspace\project-024-wuxian-workshop          -> --wuxian-root
    C:\...\QQBrowser\QQBrowser.exe                    -> --qb

用法:
    python fix_paths.py                       # 只统计
    python fix_paths.py --apply               # 改项目根 + 客户端根
    python fix_paths.py --apply --wow "D:/Games/WoW"
    python fix_paths.py --apply --qb "C:/Program Files/Google/Chrome/Application/chrome.exe"
"""
import argparse
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)

# 作者本机路径（反斜杠形式作为基准）
# 顺序即替换顺序：更长的前缀必须排在前面的短前缀之前（cqf 先于 wow）
AUTHOR = [
    ("cqf", "D:\\Game\\World of Warcraft\\_cn_beta_\\Interface\\AddOns\\ClassQuestsForever\\Data"),
    ("root", "D:\\workspace\\DungeonsForever"),
    ("wow", "D:\\Game\\World of Warcraft"),
    ("wuxian_root", "D:\\workspace\\project-024-wuxian-workshop"),
    ("qb", "C:\\Program Files (x86)\\Tencent\\QQBrowser\\QQBrowser.exe"),
]


def variants(p):
    """同一条路径的三种文本写法，按「先长后短」排列避免互相吃掉。"""
    return [p.replace("\\", "\\\\"), p, p.replace("\\", "/")]


def main():
    ap = argparse.ArgumentParser(description="批量修正脚本里的本机绝对路径")
    ap.add_argument("--apply", action="store_true", help="真正写回（默认只统计）")
    ap.add_argument("--root", help="项目根（含 Core/Data 那层），默认本包目录")
    ap.add_argument("--cqf", help="ClassQuestsForever 的 Data 目录，默认用包内 samples")
    ap.add_argument("--wow", help="WoW 安装目录，如 D:/Games/WoW")
    ap.add_argument("--wuxian-root", help="wuxian 工程目录")
    ap.add_argument("--qb", help="Chromium 内核浏览器 exe")
    a = ap.parse_args()

    targets = {
        "cqf": a.cqf or os.path.join(PKG, "samples", "ClassQuestsForever"),
        "root": a.root or PKG,
        "wow": a.wow,
        "wuxian_root": a.wuxian_root,
        "qb": a.qb,
    }

    pairs = []
    for key, old in AUTHOR:
        new = targets.get(key)
        if not new:
            continue
        for ov, nv in zip(variants(old), variants(new)):
            pairs.append((ov, nv))

    print("包目录: %s\n" % PKG)
    for key, new in targets.items():
        if new:
            print("  %-12s %s" % (key, new))
    print()

    changed = 0
    skipped = 0
    per_file = []
    for name in sorted(os.listdir(HERE)):
        if not name.endswith(".py") or name == "fix_paths.py":
            continue
        path = os.path.join(HERE, name)
        try:
            src = io.open(path, encoding="utf-8", errors="ignore").read()
        except Exception:
            skipped += 1
            continue
        out = src
        n = 0
        for ov, nv in pairs:
            c = out.count(ov)
            if c:
                out = out.replace(ov, nv)
                n += c
        if n:
            changed += 1
            per_file.append((name, n))
            if a.apply:
                io.open(path, "w", encoding="utf-8", newline="\n").write(out)

    print("含可替换路径的脚本: %d 个，共 %d 处" % (changed, sum(x[1] for x in per_file)))
    for name, n in per_file[:15]:
        print("    %-42s %d" % (name, n))
    if len(per_file) > 15:
        print("    ... 其余 %d 个" % (len(per_file) - 15))

    if changed == 0:
        print("\n没有可替换的内容（可能已经改过）。")
    elif a.apply:
        print("\n已写回。")
    else:
        print("\n以上只是统计。加 --apply 执行。")

    if not a.wow:
        print("\n提示：客户端根目录仍是作者路径。用 --wow 指定你的，例如")
        print('  python fix_paths.py --apply --wow "D:/Games/WoW"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
