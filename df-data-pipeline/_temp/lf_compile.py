import lupa.lua51 as lua51

files = [
    "Core/LootFilter.lua", "Core/LootFilterUI.lua", "Core/Data/Data_LootFilter.lua",
    "Core/DungeonUI.lua", "Core/MainFrame.lua", "Core/Data/zhTW/Data_LootFilter.lua",
    "Core/Data/enUS/Data_LootFilter.lua",
]
rt = lua51.LuaRuntime()
load = rt.eval("function(src) local f,e = loadstring(src) if f then return 'OK' else return 'ERR: '..tostring(e) end end")
bad = 0
for f in files:
    src = open(f, "rb").read()
    r = load(src)
    print("  %-42s %s" % (f, r))
    if r != "OK":
        bad += 1
print("\n=== %d/%d OK, %d FAIL ===" % (len(files) - bad, len(files), bad))
