import os
import re
import shutil

REPO = r"D:/workspace/DungeonsForever"
CUR = os.path.join(REPO, "Core", "Core.lua")
OUT = os.path.join(REPO, "_temp", "_core_prev.lua")

src = open(CUR, "r", encoding="utf-8", newline="").read()

new_cand = (
    '    local candidates = {\r\n'
    '        "ARKai_T.ttf", "ARHei.TTF", "ARKai_C.ttf",\r\n'
    '        "bLEI00D.TTF", "bHEI00M.TTF", "bKAI00M.TTF", "arheiuhk_bd.TTF",\r\n'
    '    }'
)
old_cand = '    local candidates = { "ARKai_T.ttf", "ARHei.TTF", "FRIZQT__.TTF" }'
assert new_cand in src, "new candidates block not found"

fallback = (
    '    local game = _G.GameFontNormal\r\n'
    '    if not ns.FONT and type(game) == "table" and type(game.GetFont) == "function" then\r\n'
    '        local p = game:GetFont()\r\n'
    '        if type(p) == "string" then ns.FONT = p end\r\n'
    '    end\r\n'
    '    if not ns.FONT and type(STANDARD_TEXT_FONT) == "string" then\r\n'
    '        ns.FONT = STANDARD_TEXT_FONT\r\n'
    '    end\r\n'
)
assert fallback in src, "fallback block not found"

prev = src.replace(new_cand, old_cand).replace(fallback, "")
assert "GameFontNormal" not in prev, "GameFontNormal still present"

open(OUT, "w", encoding="utf-8", newline="").write(prev)
print("pre-edit written:", OUT, len(prev), "bytes")

for cli in (r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/DungeonsForever",
            r"D:/Game/World of Warcraft/_cn_beta_/Interface/AddOns/DungeonsForever"):
    dst = os.path.join(cli, "Core", "Core.lua")
    if os.path.isdir(cli):
        shutil.copyfile(OUT, dst)
        print("staged pre-edit ->", dst)
