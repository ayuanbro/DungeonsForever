# -*- coding: utf-8 -*-
"""MEMORY.md 数据链路备忘追加：副本任务可共享标志来源。"""
import io

PATH = r"D:\workspace\DungeonsForever\.workbuddy\memory\MEMORY.md"
OLD = "- 地图入口保持原石门 MapDoor。\n"
NEW = (OLD +
       "- ★ 副本任务「可共享」标志 = `ns.DungeonQuestShare`（`Core/Data/Data_DungeonQuests.lua` 尾部，"
       "生成器 `_temp/gen_quest_share.py`）：源 = QuestieDB-Forever Quest 标量行 "
       "**字段 23 = questFlags & 0x08**（字段缺失按 0）；纯 ID 段（无文案）⇒ 三语覆盖层只整表替换 "
       "ns.DungeonQuests/Alias/PreExtra/PreNote，不冲它。本表 344 任务 / 190 可共享。\n")


def main():
    text = io.open(PATH, encoding="utf-8").read()
    n = text.count(OLD)
    if n != 1:
        print("命中 %d 次" % n)
        raise SystemExit(1)
    io.open(PATH, "w", encoding="utf-8", newline="\n").write(text.replace(OLD, NEW))
    print("OK")


if __name__ == "__main__":
    main()
