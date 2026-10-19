from lupa import lua51
lua = lua51.LuaRuntime()
r = lua.execute("return loadfile(\"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/DungeonsForever/Locales/zhTW.lua\")")
print("loadfile:", r)
