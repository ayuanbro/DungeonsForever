# -*- coding: utf-8 -*-
"""MapProbe 离线冒烟测试：用 tf_dryrun 的 lupa 桩环境把探针真跑一遍。

测的是「行为」：能不能按 4 列 x 3 行拼出 12 块、贴的 FileDataID 顺序对不对、
每条命令会不会崩。夹具用的就是实测到的真数据（湿地 / 怒焰裂谷）。

用法：python _mapprobe_check.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

PROBE = (os.environ.get('MAPPROBE_LUA')
         or r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\MapProbe\MapProbe.lua')

PRELUDE = r'''
-- ── 补桩 ─────────────────────────────────────────────────────────────
CHAT = {}
DEFAULT_CHAT_FRAME = { AddMessage = function(self, m) CHAT[#CHAT + 1] = tostring(m) end }

TIMERS = {}
C_Timer = { After = function(_, fn) TIMERS[#TIMERS + 1] = fn end,
            NewTicker = function() return { Cancel = function() end } end }

function GetBuildInfo() return "1", "1", "1", 16001 end

-- ── 夹具：实测到的真 FileDataID ───────────────────────────────────────
WET = { 273157, 273162, 273168, 273170, 273154, 273176,
        273182, 273183, 273158, 273175, 273153, 273169 }
RFC = { 449736, 449740, 449741, 449742, 449743, 449744,
        449745, 449746, 449747, 449737, 449738, 449739 }

C60 = { 8068406, 8068410, 8068411, 8068412, 8068413, 8068414,
        8068415, 8068416, 8068417, 8068407, 8068408, 8068409 }

-- 旧铁炉堡（领主大厅）：fid 顺序与编号不一致，按 listfile 名核对过
OIF = { 2470313, 2470317, 2470318, 2470319, 2470320, 2470321,
        2470322, 2470323, 2470324, 2470314, 2470315, 2470316 }

local FIX = {}
for i = 1, 12 do
  FIX["interface\\worldmap\\wetlands\\wetlands" .. i .. ".blp"] = WET[i]
  FIX["interface\\worldmap\\wetlands_c60\\wetlands_c60" .. i .. ".blp"] = C60[i]
  FIX["interface\\worldmap\\ragefire\\ragefire1_" .. i .. ".blp"] = RFC[i]
  FIX["interface\\worldmap\\oldironforge\\oldironforge" .. i .. ".blp"] = OIF[i]
end

function GetFileIDFromPath(p)
  if type(p) ~= "string" then return 0 end
  local k = string.lower(p)
  k = string.gsub(k, "/", "\\")
  return FIX[k] or 0
end

-- ── C_Map 夹具 ───────────────────────────────────────────────────────
local INFO = {
  [11]  = { name = "湿地",     mapType = 3, parentMapID = 1415 },
  [243] = { name = "怒焰裂谷", mapType = 4, parentMapID = 1414 },
  [1]   = { name = "东部王国", mapType = 2, parentMapID = 0 },
}
C_Map = {
  GetMapInfo = function(id) return INFO[id] end,
  GetMapBest = nil,
  GetBestMapForUnit = function() return 11 end,
  GetMapArtID = function() return 900 + id end,
  GetMapArtBackgroundAtlas = function() return "wetlands-atlas" end,
  GetMapArtLayers = function(id)
    if id ~= 11 then return nil end
    return { { layerWidth = 1024, layerHeight = 768, tileWidth = 256, tileHeight = 256,
               minScale = 1, maxScale = 2, additionalZoomSteps = 0 } }
  end,
  MapHasArt = function(id) return id == 11 end,
  GetMapArtLayerTextures = function(id, layer)
    if id ~= 11 or layer ~= 1 then return nil end
    local t = {}
    for i = 1, 12 do t[i] = WET[i] end
    return t
  end,
  OpenWorldMap = function() return true end,
  GetPlayerMapPosition = function(id, unit)
    if id ~= 11 then return nil end
    return { GetXY = function() return 0.25, 0.75 end }
  end,
}

function GetInstanceInfo() return "湿地", "party", 1, "普通", 5, false, false, 1234 end
function GetRealZoneText() return "湿地" end
function GetSubZoneText() return "" end

-- ── 记录建帧（探针把帧放在 local 里，只能从建帧口捞） ──────────────────
ALLF = {}
local _cf = CreateFrame
CreateFrame = function(t, n, p)
  local o = _cf(t, n, p)
  o.__name = n
  ALLF[#ALLF + 1] = o
  return o
end

function FindFrame(name)
  for i = #ALLF, 1, -1 do
    if rawget(ALLF[i], "__name") == name then return ALLF[i] end
  end
  return nil
end

-- 取画布上「最近一次」画上去的 n 块贴图
function LastTiles(n)
  local c = FindFrame("MapProbeCanvas")
  if not c then return nil end
  local kids = rawget(c, "__children")
  if not kids then return nil end
  local out = {}
  for i = #kids - n + 1, #kids do out[#out + 1] = kids[i] end
  return out
end

function TileCount()
  local c = FindFrame("MapProbeCanvas")
  if not c then return 0 end
  local kids = rawget(c, "__children")
  return kids and #kids or 0
end

function Say()
  return table.concat(CHAT, "\n")
end

function ClearChat() for i = #CHAT, 1, -1 do CHAT[i] = nil end end

-- 期望：4 列 x 3 行，行优先，x=(col-1)*256，y=-(row-1)*256
function CheckGrid(name, tiles, wantIds, cell)
  cell = cell or 256
  Check(name .. " · 12 块", tiles and #tiles == 12)
  if not tiles or #tiles ~= 12 then return end
  local posOK, idOK, sizeOK = true, true, true
  for n = 1, 12 do
    local t = tiles[n]
    local col = (n - 1) % 4 + 1
    local row = math.floor((n - 1) / 4) + 1
    local p = rawget(t, "__pts")
    if not p or tonumber(p[4]) ~= (col - 1) * cell or tonumber(p[5]) ~= -(row - 1) * cell then
      posOK = false
    end
    if rawget(t, "__tex") ~= wantIds[n] then idOK = false end
    if t.GetWidth ~= nil and (tonumber(t.__w) or 0) ~= cell then sizeOK = false end
  end
  Check(name .. " · 4 列 x 3 行位置", posOK)
  Check(name .. " · 贴图 ID 顺序", idOK)
  Check(name .. " · 单块 " .. cell .. "x" .. cell, sizeOK)
end

-- 命令要等探针加载完才有，测试里现取
function GetCmd() return SlashCmdList["MAPPROBE"] end
'''

TEST = r'''
local CMD = GetCmd()
Check("斜杠命令已注册", CMD ~= nil)
if not CMD then Summary() return end

-- ① 中文关键词：湿地（走实测路径）
local base = TileCount()
CMD("湿地")
local tiles = LastTiles(12)
Check("① 湿地 建了 12 块", TileCount() - base == 12)
CheckGrid("① 湿地", tiles, WET)
Check("① 走 API（客户端实际那套）", string.find(Say(), "uiMapID 11", 1, true) ~= nil)
Check("① 打印了地名", string.find(Say(), "湿地", 1, true) ~= nil)
ClearChat()

-- ② 中文关键词：怒焰裂谷（API 拿不到 → 回落实测路径）
base = TileCount()
CMD("怒焰裂谷")
CheckGrid("② 怒焰裂谷", LastTiles(12), RFC)
Check("② API 无数据时回落实测路径", string.find(Say(), "改走已实测路径", 1, true) ~= nil)
Check("② 打印了路径", string.find(Say(), "路径：", 1, true) ~= nil)
ClearChat()

-- ②b raw 别名：1.60 重制版湿地
base = TileCount()
CMD("raw wet60")
Check("②b raw wet60 建了 12 块", TileCount() - base == 12)
CheckGrid("②b raw wet60", LastTiles(12), C60)
Check("②b 认出别名", string.find(Say(), "1.60 重制", 1, true) ~= nil)
ClearChat()

-- ②c raw 不带参数：只列不画
base = TileCount()
local okRaw = pcall(CMD, "raw")
Check("②c raw 不带参数不崩", okRaw and TileCount() == base and #CHAT > 0)
ClearChat()

-- ②d 领主大厅（= 旧铁炉堡）：名字对不上任何 uiMap → 按别名回落实测路径
base = TileCount()
CMD("领主大厅")
Check("②d 领主大厅 建了 12 块", TileCount() - base == 12)
CheckGrid("②d 领主大厅", LastTiles(12), OIF)
Check("②d 认出别名", string.find(Say(), "旧铁炉堡", 1, true) ~= nil)
ClearChat()

-- ②e raw oif：按别名直画
base = TileCount()
CMD("raw oif")
Check("②e raw oif 建了 12 块", TileCount() - base == 12)
CheckGrid("②e raw oif", LastTiles(12), OIF)
ClearChat()

-- ③ 按 uiMapID 走 API
base = TileCount()
CMD("id 11")
Check("③ id 11 建了 12 块", TileCount() - base == 12)
CheckGrid("③ id 11", LastTiles(12), WET)
Check("③ 打印了层尺寸", string.find(Say(), "layer 1024x768 / tile 256x256", 1, true) ~= nil)
Check("③ 打印了层号", string.find(Say(), "第 1/1 层", 1, true) ~= nil)
ClearChat()

-- ④ paths 核对
CMD("paths")
local s = Say()
Check("④ paths 列出三张", string.find(s, "湿地", 1, true) ~= nil
      and string.find(s, "怒焰裂谷", 1, true) ~= nil
      and string.find(s, "旧铁炉堡", 1, true) ~= nil)
Check("④ 命中 12/12（湿地）", string.find(s, "12/12", 1, true) ~= nil)
ClearChat()

-- ④b dump 关键词只落到路径素材时，也打印每块 fid
CMD("dump 领主大厅")
s = Say()
Check("④b dump 领主大厅 走到路径素材", string.find(s, "旧铁炉堡", 1, true) ~= nil)
Check("④b 打出旧铁炉堡首块 id", string.find(s, tostring(OIF[1]), 1, true) ~= nil)
ClearChat()

-- ⑤ dump 打印 FileDataID
CMD("dump 11")
s = Say()
Check("⑤ dump 有层信息", string.find(s, "层 1", 1, true) ~= nil)
Check("⑤ dump 打出首块 id", string.find(s, tostring(WET[1]), 1, true) ~= nil)
Check("⑤ dump 打出末块 id", string.find(s, tostring(WET[12]), 1, true) ~= nil)
ClearChat()

-- ⑥ list 只列不画
base = TileCount()
CMD("list 湿地")
Check("⑥ list 不画图", TileCount() == base)
Check("⑥ list 有输出", #CHAT > 0)
ClearChat()

-- ⑦ 找不到的图名：不崩、不画
base = TileCount()
local okErr = pcall(CMD, "zzz不存在的图zzz")
Check("⑦ 未知名不报错", okErr)
Check("⑦ 未知名不画图", TileCount() == base)
Check("⑦ 有提示", string.find(Say(), "没找到", 1, true) ~= nil)
ClearChat()

-- ⑧ 图层/缩放/隐藏：换层（层 2 不存在 → 提示，不崩）
okErr = pcall(CMD, "id 11")
Check("⑧a 重画 id 11", okErr)
okErr = pcall(CMD, "layer 2")
Check("⑧b layer 2 不存在时不崩", okErr)
Check("⑧b 有提示", #CHAT > 0)
ClearChat()
okErr = pcall(CMD, "scale 0.5")
Check("⑧c scale 不崩", okErr)
okErr = pcall(CMD, "hide")
Check("⑧d hide 不崩", okErr)
okErr = pcall(CMD, "")
Check("⑧e 空命令 = 帮助", okErr and #CHAT >= 8)
ClearChat()

-- ⑨ 贴图真实尺寸与预设不同时，自动按实测重排
CMD("id 11")
tiles = LastTiles(12)
for i = 1, 12 do
  local t = tiles[i]
  t.GetWidth = function() return 512 end
  t.GetHeight = function() return 512 end
end
local nBefore = #TIMERS
for i = 1, #TIMERS do TIMERS[i]() end
Check("⑨ 触发了延时校正", #TIMERS > 0)
tiles = LastTiles(12)
local posOK = true
for n = 1, 12 do
  local col = (n - 1) % 4 + 1
  local row = math.floor((n - 1) / 4) + 1
  local p = rawget(tiles[n], "__pts")
  if not p or tonumber(p[4]) ~= (col - 1) * 512 or tonumber(p[5]) ~= -(row - 1) * 512 then posOK = false end
end
Check("⑨ 按 512 重排", posOK)
Check("⑨ 有重排提示", string.find(Say(), "按实测重排", 1, true) ~= nil)
ClearChat()

-- ⑩ tile 命令（手输路径）
base = TileCount()
CMD("tile Interface\\WorldMap\\Ragefire\\Ragefire1_")
Check("⑩ tile 建了 12 块", TileCount() - base == 12)
CheckGrid("⑩ tile", LastTiles(12), RFC)
ClearChat()

-- ⑪ 拿不到 FileDataID（老客户端 / API 缺失）时退回按路径贴图
local oldFID = GetFileIDFromPath
GetFileIDFromPath = function() return 0 end
base = TileCount()
CMD("领主大厅")
Check("⑪ 无 ID 也建了 12 块", TileCount() - base == 12)
local t11 = LastTiles(12)
Check("⑪ 退回按路径贴图", t11 ~= nil and type(rawget(t11[1], "__tex")) == "string")
Check("⑪ 有提示", string.find(Say(), "直接按路径贴图", 1, true) ~= nil)
ClearChat()
GetFileIDFromPath = oldFID

-- ⑫ me：人物坐标自测
ClearChat()
okErr = pcall(CMD, "me")
local sMe = Say()
Check("⑫ me 不崩且有输出", okErr and #sMe > 0)
Check("⑫ me 打印当前地图 ID", string.find(sMe, "GetBestMapForUnit", 1, true) ~= nil)
Check("⑫ me 打印坐标", string.find(sMe, "x=0.2500 y=0.7500", 1, true) ~= nil)
Check("⑫ me 认出区域名对应已实测路径", string.find(sMe, "[wet]", 1, true) ~= nil)
Check("⑫ me 打印显示链", string.find(sMe, "显示链 1", 1, true) ~= nil)
Check("⑫ me 显示链认出有美术", string.find(sMe, "有美术=true", 1, true) ~= nil)
ClearChat()

-- ⑬ inv：34 副本实机盘点
ClearChat()
okErr = pcall(CMD, "inv")
local sInv = Say()
Check("⑬ inv 不崩且有输出", okErr and #sInv > 0)
Check("⑬ inv 领主大厅 12/12", string.find(sInv, "领主大厅  12/12", 1, true) ~= nil)
Check("⑬ inv 怒焰裂谷 12/12", string.find(sInv, "怒焰裂谷  12/12", 1, true) ~= nil)
Check("⑬ inv 无候选副本标红", string.find(sInv, "|cffff8080", 1, true) ~= nil)
Check("⑬ inv 有小计行", string.find(sInv, "小计：有图", 1, true) ~= nil)
ClearChat()
'''


def main():
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(T.STUB)
    lua.execute(PRELUDE)
    lua.globals().LoadFile(PROBE, "MAPPROBE")
    print("已加载探针：%s\n" % PROBE)
    lua.execute(TEST)
    ok = lua.globals().Summary()
    print("\n结论：" + ("全部通过" if ok else "存在失败项"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
