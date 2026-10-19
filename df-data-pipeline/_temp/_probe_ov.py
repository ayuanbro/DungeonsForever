# -*- coding: utf-8 -*-
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'
sys.path.insert(0, TOOLS); sys.path.insert(0, HERE)
import tf_dryrun as T
from lupa import lua51

ADDON = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
TOC = os.path.join(ADDON, 'DungeonsForever.toc')
lua = lua51.LuaRuntime(unpack_returned_tuples=True)
lua.execute(T.STUB)
lua.execute(r'''
C_Timer = { After = function(t, fn) if t == 0 then fn(); return end end }
ALLF = {}
do local orig = CreateFrame
   CreateFrame = function(...) local f = orig(...)
     if type(f) == "table" then ALLF[#ALLF + 1] = f end; return f end end''')
lua.execute('os = nil')
lua.execute('time = function() return 1796850000 end')
lua.execute('GetCursorPosition = function() return 400, 300 end')
lua.execute('BG.hui.OnThemeChange = function(fn) end')
lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
lua.execute('BG.hui = nil')
lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
lua.execute('TF_NS = TF_NS or {}')
lua.execute('do local o = GetBuildInfo; GetBuildInfo = function(...) local a,b,c,d = o(...); return a,b,c,16001,e end end')
lua.execute('UIErrorsFrame = { AddMessage = function() end }')
files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
         for l in open(TOC, encoding='utf-8').read().splitlines()
         if l.strip() and not l.strip().startswith('##')]
loadfile = lua.eval('function(rel) local c = loadfile(ADDON_ROOT .. "/" .. rel) '
                    'if not c then return nil end return function() return c("DungeonsForever", TF_NS) end end')
for rel in files:
    if rel.lower().endswith('.xml'):
        continue
    ch = loadfile(rel)
    if ch is None:
        print('LOADFAIL', rel)
        break
    ch()
lua.execute('if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end')
lua.execute('PLAYER_LEVEL = 16; UnitLevel = function() return PLAYER_LEVEL end')
print(lua.eval(r'''(function()
  local R = {}
  local U = TF_NS.DungeonUI
  local DG = TF_NS.DungeonModule
  local ok, err = pcall(function()
    if not U.built then U:Build() end
    U:SwitchSub("Dungeons")
    R[#R+1] = "built=" .. tostring(U.built) .. " dungeonBuilt=" .. tostring(U.dungeonBuilt)
    R[#R+1] = "ov=" .. type(U.dungeonQOverviewF) .. " canvas=" .. type(U.dungeonQOVCanvas)
            .. " pool=" .. type(U.dungeonQOVPool) .. " chromeOnly=" .. tostring(DG.__chromeOnly)
    DG.EnsureCardPool(); DG.EnsureOverviewBuilt(); DG.EnsureDetailBuilt(); DG.EnsureQuestLane()
    R[#R+1] = "after ensure ov=" .. type(rawget(U, "dungeonQOverviewF"))
            .. " canvas=" .. type(rawget(U, "dungeonQOVCanvas"))
            .. " pool=" .. type(rawget(U, "dungeonQOVPool"))
    local pick
    for _, dg in ipairs(TF_NS.DungeonData.dungeons) do
      if dg.id == "blackrock_depths" then pick = dg end
    end
    R[#R+1] = "pick=" .. tostring(pick and pick.id or "nil")
    U.dungeonQSide = "H"; U.dungeonQView = "overview"; U.dungeonQuestSel = nil; U.dungeonQDetExt = nil
    U:ShowDungeonDetail(pick)
    R[#R+1] = "detailCur=" .. tostring(U.dungeonDetailCur and U.dungeonDetailCur.id)
    U:RenderDungeonQuests()
    R[#R+1] = "view=" .. tostring(U.dungeonQView)
    local nPosB, nShown, nAny = 0, 0, 0
    for _, f in ipairs(ALLF) do
      if type(rawget(f, "posB")) == "table" then
        nPosB = nPosB + 1
        if rawget(f, "__shown") then nShown = nShown + 1 end
      end
    end
    R[#R+1] = "frames=" .. #ALLF .. " posB=" .. nPosB .. " posBshown=" .. nShown
    R[#R+1] = "ovShown=" .. tostring(rawget(rawget(U, "dungeonQOverviewF") or {}, "__shown"))
  end)
  if not ok then R[#R+1] = "ERR " .. tostring(err) end
  return table.concat(R, "\n")
end)()'''))
