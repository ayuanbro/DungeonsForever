# -*- coding: utf-8 -*-
"""修两个 bug：①切页残留 = PaintLvTiles 隐藏列表漏 scheme；②点击不切换 = PD.Setting 布尔化吃掉字符串方案。
加 PD.SettingRaw（原始值，nil 回落默认），autoScheme 三处读取全部换掉。"""
import io, sys

def patch(path, pairs, note):
    d = open(path, "rb").read()
    cr = d.count(b"\r\n"); lf = d.count(b"\n") - cr
    e = b"\r\n" if cr > lf else b"\n"
    for old, new in pairs:
        o = old.encode("utf-8").replace(b"\n", e)
        n = new.encode("utf-8").replace(b"\n", e)
        c = d.count(o)
        assert c == 1, (note, c, old[:60])
        d = d.replace(o, n)
    open(path, "wb").write(d)
    print(note, "OK")

# ── 1) ProfessionUI.lua：残留 + SettingRaw + 两处读取 ──
patch(r"D:/workspace/DungeonsForever/Core/ProfessionUI.lua", [
    # 残留：Hide 列表补 scheme（其它签/设置面板也要收掉方案卡）
    ("""    if PD.tab ~= "leveling" or PD.setOpen then
        for _, k in ipairs({ "mode", "cost", "target", "snap" }) do tiles[k]:Hide() end
        return 0
    end""",
     """    if PD.tab ~= "leveling" or PD.setOpen then
        for _, k in ipairs({ "mode", "scheme", "cost", "target", "snap" }) do tiles[k]:Hide() end
        return 0
    end"""),
    # SettingRaw：非布尔设置（autoScheme）专用；Setting 保持布尔口径不动（老调用方零波及）
    ("""function PD.Setting(k)
    local v = ProfDB()[k]
    if v == nil then return PD.SETTING_DEF[k] and true or false end
    return v and true or false
end
""",
     """function PD.Setting(k)
    local v = ProfDB()[k]
    if v == nil then return PD.SETTING_DEF[k] and true or false end
    return v and true or false
end

-- 原始值读取（2026-10-11）：字符串型设置（autoScheme）必须走这里——
-- PD.Setting 是布尔口径（v and true or false），会把 "optim" 吃成 true，
-- 方案点击循环永远匹配不上、每次写回第一个方案（截图实锤 bug）。
function PD.SettingRaw(k)
    local v = ProfDB()[k]
    if v == nil then return PD.SETTING_DEF[k] end
    return v
end
"""),
    # 点击 handler：cur 读原始值
    ("""        local cur = PD.Setting("autoScheme")""",
     """        local cur = PD.SettingRaw("autoScheme")"""),
    # 主链路：scheme 读原始值（否则 optim 门槛永远不生效）
    ("""    local scheme = PD.Setting("autoScheme")
    local autoOn = (PD.Setting("autoRoute") and RA""",
     """    local scheme = PD.SettingRaw("autoScheme")
    local autoOn = (PD.Setting("autoRoute") and RA"""),
], "ProfessionUI")

# ── 2) ProfFollow.lua：HUD 同源读取 ──
patch(r"D:/workspace/DungeonsForever/Core/ProfFollow.lua", [
    ("""    local scheme = PD and PD.Setting and PD.Setting("autoScheme") or "cheapest\"""",
     """    local scheme = PD and PD.SettingRaw and PD.SettingRaw("autoScheme") or "cheapest\""""),
], "ProfFollow")

# ── 3) harness：同步 ProfFollow 断言 + 防回潮三条 ──
patch(r"D:/workspace/DungeonsForever/_temp/df_dungeon_check.py", [
    ("""       and 'PD.Setting("autoScheme")' in pfhud)""",
     """       and 'PD.SettingRaw("autoScheme")' in pfhud)"""),
], "check-follow")

print("all patched")
