local learned={ [20219]=true, [20222]=false }
C_SpellBook={IsSpellKnown=function(id) return false end}
IsPlayerSpell=function(id) return learned[id] end
UnitFactionGroup=function() return "Alliance" end
UnitLevel=function() return 40 end
C_QuestLog={IsQuestFlaggedCompleted=function() return false end}
local revisions={}
local ns={LoadForeverPages=true,
  L=setmetatable({}, {__index=function(_,k) return k end}),
  ProfRouteAuto={Invalidate=function(reason) revisions[#revisions+1]=reason end},
  ProfModule={SettingRaw=function(k,slug) if k=="autoCraftTools" then return slug~="engineering" end end},
  ProfSpecializations={ [1001]={0,20219}, [1002]={0,20222}, [1003]={0,0}},
  ProfSpecializationsMeta={}, ProfSpecializationQuestMeta={},
  ProfSpecializationQuests={
    gnomish={id="g",questID=3641,abilityID=20219,minSkill=200,profession="engineering",inputs={{111,1}}},
    goblin={id="b",questID=3642,abilityID=20222,minSkill=200,profession="engineering",inputs={{222,1}}},
  }
}
local path=__GATES_PATH or "Core/ProfGates.lua"
assert(loadfile(path))("DungeonsForever",ns)
local G=ns.ProfGates
local check=function(ok,msg) if not ok then error(msg or "test assertion failed") end end
check(G.RequiredAbility(1001)==20219,"PR original RequiredAbility removed")
check(G.GetChoiceSetting()=="none","new installation should show no manual setting")
check(G.EngineeringChoice()=="gnomish","positive detection across namespace/legacy APIs failed")
check(G.EffectiveChoice()=="gnomish","learned Gnomish not auto-included")
check(G.GetPlannedChoice()=="gnomish","effective planned branch wrong")
check(G.Allowed("engineering",1001) and not G.Allowed("engineering",1002),"learned specialization recipe admission wrong")
check(G.LearningEligibility(1001),"known specialization blocked at gate")
check(G.SpecGoal("engineering",300)==nil,"learned specialization quest repeated")
check(not G.SetPlannedChoice("auto"),"removed dropdown mode still accepted")
check(G.AutoCraftTools("engineering")==false and G.AutoCraftTools("alchemy")==true,"per profession tool toggle broken")
check(G.SetPlannedChoice("none") and G.GetChoiceSetting()=="none","unspecified setter failed")
check(G.EffectiveChoice()=="gnomish","manual none must not suppress a learned branch")
check(G.SetPlannedChoice("goblin"),"manual Goblin setting rejected")
check(G.EffectiveChoice()=="goblin" and G.GetChoiceSetting()=="goblin","manual selection not applied")
local ctx=G.SpecializationContext({profession="engineering",target=300})
check(ctx.selectionConflict,"should not allow changing already-learned specialization silently")
check(not G.Allowed("engineering",1001) and G.Allowed("engineering",1002),"manual alternative branch filtering wrong")
learned[20219]=false
learned[20222]=false
G.Invalidate()
check(G.EngineeringChoice()=="none","unlearned state not recognized")
check(G.GetPlannedChoice()=="goblin","manual target should remain after skill loss")
local goal=G.SpecGoal("engineering",300)
check(goal and goal.abilityID==20222,"manually requested Goblin quest not planned")
local before=G.SpecFingerprint(G.GetPlannedChoice())
learned[20222]=true
G.Invalidate()
local after=G.SpecFingerprint(G.GetPlannedChoice())
check(before~=after,"learning selected specialization failed to change cache fingerprint")
check(G.SpecGoal("engineering",300)==nil,"learned quest planned twice")
G.SetPlannedChoice("none")
check(G.GetChoiceSetting()=="none","none setting not normalized")
check(DungeonsForeverDB.prof.engChoice==nil,"none must not persist extra value")
check(G.GetPlannedChoice()=="goblin","learned Goblin not auto detected in unspecified state")
learned[20222]=false
G.Invalidate()
check(G.GetPlannedChoice()=="none","no learned branch should remain none")
check(not G.Allowed("engineering",1001) and not G.Allowed("engineering",1002),"none without abilities should exclude both specialized recipe groups")
check(G.SpecGoal("engineering",300)==nil,"random engineering quest generated when none learned/selected")
check(G.SetPlannedChoice("gnomish"),"manual Gnomish selection rejected")
C_QuestLog.IsQuestFlaggedCompleted=function(id) return id==3641 end
check(G.SpecGoal("engineering",300)==nil,"completed specialization introduction planned again")
local done=G.SpecializationContext({profession="engineering",target=300})
check(#(done.goals or {})==0 and #(done.unresolvedGoals or {})==1,"completed intro regression")
check(#revisions >=3,"specialization choices did not invalidate planner")
print("PASS: PR interfaces, automatic known branch, three menu options, quests, fingerprints, scoped tools")
