"""Scan a Lua addon tree for writes to globals / Blizzard-owned tables.

Heuristic (no parser): report
  A) _G.foo = ... , _G["foo"] = ...
  B) column-0   Foo = ...        (top-level global assignment)
  C) BlizzTable.field = ...      (field write on a known Blizzard global)
  D) hooksecurefunc(...) calls
and filter out the addon's own namespace.
"""
import os, re, sys, collections

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"D:/workspace/DungeonsForever"

OWN = {
    "ns", "DF_NS", "L", "DungeonsForeverDB", "DF", "U",
}

BLIZZ = {
    "GameTooltip", "ItemRefTooltip", "ItemRefShoppingTooltip1", "ItemRefShoppingTooltip2",
    "ShoppingTooltip1", "ShoppingTooltip2", "QuestFrame", "QuestLogFrame", "QuestLogPopupDetailFrame",
    "UIParent", "UISpecialFrames", "StaticPopupDialogs", "StaticPopup1",
    "SlashCmdList", "UIDropDownMenu", "GameTooltip_SetTitle",
    "PTR_IssueReporter", "C_UserFeedback", "C_QuestLog", "C_Map", "C_UnitAuras",
    "C_QuestSession", "C_ChromieTime", "C_SpecializationInfo", "C_Soulbinds",
    "UnitFactionGroup", "UnitRace", "UnitSex", "UnitEffectiveLevel", "UnitClass",
    "GetAverageItemLevel", "GetInstanceInfo", "GetBuildInfo", "GetQuestID",
    "SetItemRef", "CloseMenus", "SharedTooltip_SetBackdropStyle", "SharedTooltip_SetBackdropStyle",
    "HideUIPanel", "ShowUIPanel", "CloseSpecialWindows", "ContainerFrame_GenerateFrame",
    "_G",
}

re_Gdot = re.compile(r"_G\s*\.\s*([A-Za-z_]\w*)\s*=(?!=)")
re_Gbr  = re.compile(r"_G\s*\[\s*['\"]([A-Za-z_][\w]*)['\"]\s*\]\s*=(?!=)")
re_top  = re.compile(r"^([A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)*)\s*=(?!=)")
re_bliz = re.compile(r"\b([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\s*=(?!=)")
re_hook = re.compile(r"hooksecurefunc\s*\(")

hits = collections.defaultdict(list)

def scan(path):
    rel = os.path.relpath(path, ROOT).replace("\\", "/")
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        src = raw.decode("utf-8")
    except UnicodeDecodeError:
        src = raw.decode("latin-1")
    for i, line in enumerate(src.splitlines(), 1):
        code = line.split("--", 1)[0]
        for m in re_Gdot.finditer(code):
            hits[("_G.dot", m.group(1))].append((rel, i))
        for m in re_Gbr.finditer(code):
            hits[("_G.br", m.group(1))].append((rel, i))
        # column-0 global assignment (top level)
        if line[:1].strip():
            m = re_top.match(line)
            if m:
                name = m.group(1)
                head = name.split(".")[0]
                if head not in OWN:
                    hits[("top", name)].append((rel, i))
        for m in re_bliz.finditer(code):
            head, field = m.group(1), m.group(2)
            if head in BLIZZ:
                hits[("blizz", "%s.%s" % (head, field))].append((rel, i))
        if re_hook.search(code):
            hits[("hooksecurefunc", code.strip()[:110])].append((rel, i))

for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in
                   (".git", ".workbuddy", "_temp", ".trae", "node_modules")]
    for fn in filenames:
        if fn.endswith(".lua"):
            scan(os.path.join(dirpath, fn))

ORDER = {"_G.dot": 0, "_G.br": 0, "blizz": 1, "top": 2, "hooksecurefunc": 3}
for kind in sorted(hits, key=lambda k: (ORDER.get(k[0], 9), k[1])):
    locs = hits[kind]
    head = "%s :: %s" % (kind[0], kind[1])
    print("%-58s x%d" % (head, len(locs)))
    for rel, ln in locs[:6]:
        print("      %s:%d" % (rel, ln))
    if len(locs) > 6:
        print("      ... +%d" % (len(locs) - 6))
