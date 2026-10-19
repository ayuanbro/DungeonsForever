# -*- coding: utf-8 -*-
import io, os, re, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import enus_data_prose as DP
import gen_enus_data as G

src = io.open("../Core/Data/Data_DungeonQuests.lua", encoding="utf-8").read()
data_lit = re.findall(r'"([^"]*爱与家庭[^"]*)"', src)[1]
key = data_lit
print("in FREE:", key in DP.FREE)
if key not in DP.FREE:
    # 找最像的键
    for k in DP.FREE:
        if "爱与家庭" in k and len(k) > 10:
            print("prose key:", repr(k))
            for i, (a, b) in enumerate(zip(k, key)):
                if a != b:
                    print("first diff at", i, repr(a), hex(ord(a)), "vs", repr(b), hex(ord(b)))
                    break
            print("len:", len(k), len(key))
print("translate:", G.translate(key)[:60])
