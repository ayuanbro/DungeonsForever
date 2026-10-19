# -*- coding: utf-8 -*-
"""给 gen_enus.py 补两个新键（显示已完成 / 可共享）。保持原行尾。"""
import io
import sys

PATH = r"D:\workspace\DungeonsForever\_temp\gen_enus.py"


def main():
    raw = io.open(PATH, "rb").read()
    text = raw.decode("utf-8")

    pairs = [
        ("    '已完成': 'Completed', '已完成 %d / %d': 'Completed %d / %d',",
         "    '已完成': 'Completed', '已完成 %d / %d': 'Completed %d / %d',\n"
         "    '显示已完成': 'Show completed',"),
        ("    '前置': 'Pre-quests', '前置：': 'Pre-quests: ', '无前置': 'No pre-quests',",
         "    '前置': 'Pre-quests', '前置：': 'Pre-quests: ', '无前置': 'No pre-quests',\n"
         "    '可共享': 'Sharable',"),
    ]
    for old, new in pairs:
        n = text.count(old)
        if n != 1:
            print("命中 %d 次: %r" % (n, old))
            sys.exit(1)
        text = text.replace(old, new)

    io.open(PATH, "wb").write(text.encode("utf-8"))
    print("OK")


if __name__ == "__main__":
    main()
