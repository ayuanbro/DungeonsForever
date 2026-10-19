# -*- coding: utf-8 -*-
"""同步 df_dungeon_check.py 第二批：删剩余两处任务行 r.bar 断言。"""
import io
import sys

PATH = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"

OLD = (
    '    ck("★ 已完成行：色条转绿 + 状态字「已完成」",\n'
    '       r1.bar.__ct ~= nil and math.abs(r1.bar.__ct[2] - 0.85) < 1e-6\n'
    '       and tostring(r1.meta.__text):find("已完成", 1, true) ~= nil,\n'
    '       tostring(r1.meta.__text))\n'
    '    ck("★ 进行中行：色条转金 + 状态字「进行中」",\n'
    '       r2.bar.__ct ~= nil and math.abs(r2.bar.__ct[2] - 0.82) < 1e-6\n'
    '       and tostring(r2.meta.__text):find("进行中", 1, true) ~= nil,\n'
    '       tostring(r2.meta.__text))\n'
)
NEW = (
    '    ck("★ 已完成行：状态字「已完成」（强调条已删，状态只走名字色 + 状态字）",\n'
    '       tostring(r1.meta.__text):find("已完成", 1, true) ~= nil,\n'
    '       tostring(r1.meta.__text))\n'
    '    ck("★ 进行中行：状态字「进行中」",\n'
    '       tostring(r2.meta.__text):find("进行中", 1, true) ~= nil,\n'
    '       tostring(r2.meta.__text))\n'
)


def main():
    text = io.open(PATH, encoding="utf-8").read()
    n = text.count(OLD)
    if n != 1:
        print("命中 %d 次" % n)
        sys.exit(1)
    io.open(PATH, "w", encoding="utf-8", newline="\n").write(text.replace(OLD, NEW))
    print("OK")


if __name__ == "__main__":
    main()
