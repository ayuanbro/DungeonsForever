import io
import sys

SRC = r"D:\workspace\DungeonsForever\Core\DungeonUI.lua"
DST = r"D:\Game\World of Warcraft\_cn_beta_\Interface\AddOns\DungeonsForever\_hot_qsim.lua"

lines = io.open(SRC, "r", encoding="utf-8", newline="").read().split("\n")

start = next(i for i, ln in enumerate(lines) if ln.startswith("function DG.QuestDone(id)"))
gate = next(i for i in range(start, len(lines)) if lines[i] == 'if type(SlashCmdList) == "table" then')
closer = next(i for i in range(gate + 1, len(lines)) if lines[i] == "end")

block = "\n".join(lines[start:closer + 1])
head = ("local nsG = _G.DF_NS\n"
        "local ns = nsG\n"
        "local DG = nsG and nsG.ProfHost and nsG.ProfHost.DG\n"
        "local U = nsG and nsG.DungeonUI\n"
        "if not (DG and U) then return end\n")
io.open(DST, "w", encoding="utf-8", newline="\n").write(head + block + "\n")
print("lines %d-%d  ->  %d lines written" % (start + 1, closer + 1, block.count("\n") + 1))
print("head:", head.split("\n")[1])
print("tail:", lines[closer])
