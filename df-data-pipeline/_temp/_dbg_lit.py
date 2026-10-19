# -*- coding: utf-8 -*-
import io, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
src = io.open("../Core/Data/Data_DungeonQuests.lua", encoding="utf-8").read()
for m in re.finditer(r'^.*爱与家庭.*$', src, re.M):
    line = m.group(0)
    for lit in re.findall(r'"([^"]*爱与家庭[^"]*)"', line):
        print(repr(lit))
