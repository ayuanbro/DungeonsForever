# -*- coding: utf-8 -*-
"""一次性校验：装备过滤 v3（保留档，供复查）。
断言见任务自检 3：33 套名称可查 / 无限服词缀 17 项 / 过滤后无悬空名 /
盗贼含力量+攻击强度 / 主属性维度彻底移除 / 三源文件 0 命中禁用词。
"""
import os
import re
import sys

import lupa.lua51 as lua51

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "Core", "Data", "Data_LootFilter.lua")
LF = os.path.join(ROOT, "Core", "LootFilter.lua")
LFUI = os.path.join(ROOT, "Core", "LootFilterUI.lua")

LOADER = "function(src) local f, e = loadstring(src); if not f then error(tostring(e)) end; return f end"

VERIFY_LUA = r"""
function(ns)
  local D = ns.LootFilterData
  local out = {}
  local function ck(name, ok) out[#out + 1] = (ok and "PASS  " or "FAIL  ") .. name end

  local classes = { "WARRIOR", "PALADIN", "DEATHKNIGHT", "HUNTER", "SHAMAN", "DRUID",
                    "ROGUE", "MONK", "PRIEST", "MAGE", "WARLOCK" }
  local total = 0
  for _, c in ipairs(classes) do
    local lst = D.Presets[c]
    ck("预设存在 " .. c, type(lst) == "table" and #lst > 0)
    if type(lst) == "table" then total = total + #lst end
  end
  ck("预设总数 = 33", total == 33)

  local missW, missA = {}, {}
  for _, c in ipairs(classes) do
    for _, p in ipairs(D.Presets[c] or {}) do
      for _, nm in ipairs(p.useWeapon or {}) do
        if D.WeaponIdByName[nm] == nil then missW[#missW + 1] = c .. "/" .. p.name .. ":" .. nm end
      end
      for _, nm in ipairs(p.useArmor or {}) do
        if D.ArmorIdByName[nm] == nil then missA[#missA + 1] = c .. "/" .. p.name .. ":" .. nm end
      end
    end
  end
  ck("useWeapon 0 漏名", #missW == 0)
  ck("useArmor  0 漏名", #missA == 0)
  if #missW > 0 then out[#out + 1] = "  漏武器: " .. table.concat(missW, ", ") end
  if #missA > 0 then out[#out + 1] = "  漏护甲: " .. table.concat(missA, ", ") end

  local n, nilpat = 0, 0
  for _, v in pairs(D.ShuXing) do n = n + 1; if type(v) ~= "string" or v == "" then nilpat = nilpat + 1 end end
  ck("D.ShuXing 项数 = 17", n == 17)
  ck("D.ShuXing 模式均非 nil", nilpat == 0)
  ck("D.ShuXingOrder 项数 = 17", #(D.ShuXingOrder or {}) == 17)

  local dangling = {}
  for _, c in ipairs(classes) do
    for _, p in ipairs(D.Presets[c] or {}) do
      for _, nm in ipairs(p.useShuXing or {}) do
        if D.ShuXing[nm] == nil then dangling[#dangling + 1] = c .. "/" .. p.name .. ":" .. nm end
      end
    end
  end
  ck("过滤后 useShuXing 0 悬空名", #dangling == 0)
  if #dangling > 0 then out[#out + 1] = "  悬空: " .. table.concat(dangling, ", ") end

  local function has(list, want)
    for _, v in ipairs(list or {}) do if v == want then return true end end
    return false
  end
  local rogue = D.Presets.ROGUE[1]
  ck("盗贼含「力量」", has(rogue.useShuXing, "力量"))
  ck("盗贼含「攻击强度」", has(rogue.useShuXing, "攻击强度"))

  ck("D.MainAttr == nil", D.MainAttr == nil)
  ck("D.MainAttrOrder == nil", D.MainAttrOrder == nil)

  local function dump(p)
    return table.concat(p.useWeapon or {}, "/") .. " | " .. table.concat(p.useArmor or {}, "/")
       .. " | " .. table.concat(p.useShuXing or {}, "/")
  end
  out[#out + 1] = "== 盗贼 ==" .. dump(rogue)
  out[#out + 1] = "== 战士-武器 ==" .. dump(D.Presets.WARRIOR[1])
  out[#out + 1] = "== 牧师-神圣 ==" .. dump(D.Presets.PRIEST[4])

  out[#out + 1] = "== 各职业套数 =="
  for _, c in ipairs(classes) do out[#out + 1] = "   " .. c .. " = " .. #(D.Presets[c] or {}) end

  out[#out + 1] = "== 33 套全量清单（过滤后）=="
  for _, c in ipairs(classes) do
    for _, p in ipairs(D.Presets[c] or {}) do
      out[#out + 1] = string.format("%-12s %-14s W[%s] A[%s] S[%s]",
        c, p.name, table.concat(p.useWeapon or {}, ","), table.concat(p.useArmor or {}, ","),
        table.concat(p.useShuXing or {}, ","))
    end
  end
  return out
end
"""


def new_rt():
    return lua51.LuaRuntime(unpack_returned_tuples=True)


def load_data(rt, is_forever):
    loader = rt.eval(LOADER)
    ns = rt.table()
    ns["IsForever"] = is_forever
    ns["L"] = rt.table()
    with open(DATA, "rb") as fh:
        loader(fh.read())("DungeonsForever", ns)
    return ns


def to_list(lua_tbl):
    return [lua_tbl[i] for i in range(1, len(lua_tbl) + 1)]


def tbl_keys_value(t):
    """字符串键表：返回 {key: value}（不经 len()，因为无数组部分时 len 为 0）。"""
    return {k: v for k, v in t.items()}


def main():
    fails = 0

    # ---- 无限服分支 ----
    print("### 无限服分支（ns.IsForever = true） ###")
    rt = new_rt()
    ns = load_data(rt, True)
    for line in to_list(rt.eval(VERIFY_LUA)(ns)):
        if line.startswith("FAIL"):
            fails += 1
        print("  " + line)

    # ---- 非无限服分支（同一 runtime 另载一份，防回归）----
    print()
    print("### 非无限服分支（ns.IsForever = false，防回归） ###")
    ns2 = load_data(rt, False)
    D2 = ns2["LootFilterData"]
    sx2 = tbl_keys_value(D2["ShuXing"])
    keep15 = ["力量", "敏捷", "智力", "精神", "耐力", "急速", "暴击", "精通", "全能",
              "命中", "精准", "招架", "躲闪", "格挡", "护甲穿透"]
    add9 = ["攻击强度", "防御", "武器技能", "击中时可能", "5回法力值",
            "法术强度", "治疗强度", "特定法术强度", "移动速度"]
    missing15 = [k for k in keep15 if not sx2.get(k)]
    missing9 = [k for k in add9 if not sx2.get(k)]
    print("  D.ShuXing 键数 = %d（期望 24 = 15 旧 + 9 追加）" % len(sx2))
    print("  旧 15 项缺失 = %s" % (missing15 or "无"))
    print("  追加 9 项缺失 = %s" % (missing9 or "无"))
    if len(sx2) != 24:
        fails += 1
        print("  FAIL  非无限服键数 != 24")
    if missing15:
        fails += 1
        print("  FAIL  非无限服旧 15 项有缺")
    if missing9:
        fails += 1
        print("  FAIL  非无限服追加 9 项有缺")

    # ---- LootFilter.lua 常量（同一 runtime）----
    print()
    print("### LootFilter.lua 常量 ###")
    nslf = rt.table()
    nslf["IsTitan"] = True
    nslf["L"] = rt.table()
    nslf["LootFilterData"] = ns["LootFilterData"]
    nslf["Init"] = rt.eval("function() end")
    with open(LF, "rb") as fh:
        rt.eval(LOADER)(fh.read())("DungeonsForever", nslf)
    LFM = nslf["LootFilter"]
    ver = LFM["VER"]
    dims = to_list(LFM["DIMENSIONS"])
    print("  LF.VER = %s" % ver)
    print("  LF.DIMENSIONS = %s" % dims)
    if ver != 3:
        fails += 1
        print("  FAIL  LF.VER != 3")
    if "MainAttribute" in dims:
        fails += 1
        print("  FAIL  DIMENSIONS 仍含 MainAttribute")

    # ---- 禁用词扫描（三源文件）----
    print()
    print("### 禁用词扫描（三源文件） ###")
    pat = re.compile(r"notUseWeapon|notUseArmor|MainAttribute|MainAttr")
    for path in (DATA, LF, LFUI):
        with open(path, "rb") as fh:
            hits = pat.findall(fh.read().decode("utf-8"))
        rel = os.path.relpath(path, ROOT)
        print("  %-40s 命中 %d" % (rel, len(hits)))
        if hits:
            fails += 1
            print("  FAIL  %s 仍含禁用词 %s" % (rel, sorted(set(hits))))

    print()
    print("=== 结果：%s ===" % ("全部通过" if fails == 0 else ("%d 项失败" % fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
