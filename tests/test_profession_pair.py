"""Unlearned profession simulations use an explicit, feasible profession pair."""
import unittest

from test_prof_runtime import MOCKS, LuaRuntime, ROOT


PAIR_FIXTURES = r'''
actualProfessions={
  mining={cur=2,max=75,primary=true},
  engineering={cur=60,max=75,primary=true},
  cooking={cur=40,max=75,primary=false}}
characterName='Test'; realmName='Realm'
function UnitName() return characterName end
function GetRealmName() return realmName end
function professionCopy()
  local out={}; for k,v in pairs(actualProfessions) do
    out[k]={};for a,b in pairs(v) do out[k][a]=b end
  end; return out
end
function flat(prof,spell,item,mats,learn,grey)
  return {profession=prof,spell=spell,item=item,count=1,mats=mats,
    learn=learn or 1,yellow=grey or 10,green=grey or 10,grey=grey or 10,
    cooldown=false,catalogue=true}
end
function pairFixture()
  return {recipes={
      flat('alchemy',101,20,{{10,1}},1,3),
      flat('mining',201,10,{{11,1}},2,2),
      flat('engineering',301,10,{{12,1}},1,1),
      flat('tailoring',401,10,{{13,1}},1,1)},
    prices={[10]=30,[11]=3,[12]=1,[13]=4},
    professions={alchemy={cur=1,max=75,unlearned=true},
      mining={cur=2,max=75,primary=true},engineering={cur=60,max=75,primary=true}},
    known={['mining:201']=true,['engineering:301']=true}}
end
function craftsOf(result,prof)
  local total=0;for _,a in ipairs(result.actions or {}) do
    if a.type=='craft' and a.profession==prof then total=total+a.count end
  end;return total
end
function onlyPair(result,target,partner)
  for _,a in ipairs(result.actions or {}) do
    if a.type=='craft' then
      assert(a.profession==target or a.profession==partner,
        'unexpected profession '..tostring(a.profession))
    end
  end
end
function noExecutablePlan(r)
  assert(not r.feasible and #(r.steps or {})==0 and #(r.executionSteps or {})==0)
  assert(#(r.actions or {})==0 and #(r.mats or {})==0)
end
function hasDiagnostic(r,code)
  for _,d in ipairs(r.diagnostics or {}) do if d.code==code then return true end end
  return false
end
function livePairFixture()
  ns.ProfEconomy.Professions=professionCopy
  ns.ProfRecipes={}
  local s=pairFixture()
  for _,r in ipairs(s.recipes) do
    ns.ProfRecipes[r.profession]={rows={{r.spell,r.item,r.count,'','','',
      r.learn,r.yellow,r.green,r.grey,false,r.mats,nil,{skill=r.learn}}}}
  end
  ns.EnsureProfRecipes=function()return ns.ProfRecipes end
  ns.ProfRouteAuto.AHPriceOf=function(id)return s.prices[id] end
  ns.ProfEconomy.Known=function(spell)return s.known['mining:'..spell] or s.known['engineering:'..spell] or false end
end
'''


class ProfessionPairTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        self.load = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        for name in ('ProfEconomy.lua', 'ProfRouteSolver.lua', 'ProfRouteAuto.lua'):
            self.load(str(ROOT / 'Core' / name))
        self.lua.execute(PAIR_FIXTURES)
        self.lua.execute('ns.ProfEconomy.Professions=professionCopy')

    def test_unlearned_target_requires_explicit_different_primary_profession(self):
        self.lua.execute(r'''
          local e=ns.ProfEconomy
          local c=e.RouteContext('alchemy',{allowSecondaryLeveling=true},actualProfessions)
          assert(c.unlearned and c.requiresPartner and not c.partnerValid and not c.partner)
          for _,partner in ipairs({'alchemy','cooking','bogus'}) do
            c=e.RouteContext('alchemy',{allowSecondaryLeveling=true,secondaryProfession=partner},actualProfessions)
            assert(c.requiresPartner and not c.partnerValid)
          end
          c=e.RouteContext('alchemy',{allowSecondaryLeveling=true,secondaryProfession='mining'},actualProfessions)
          assert(c.unlearned and c.requiresPartner and c.partnerValid and c.partner=='mining')
          c=e.RouteContext('alchemy',{allowSecondaryLeveling=true,secondaryProfession='tailoring'},actualProfessions)
          assert(c.partnerValid and c.partner=='tailoring','unlearned primary partner unavailable')
        ''')

    def test_candidate_list_contains_all_other_main_professions_only(self):
        self.lua.execute(r'''
          local e=ns.ProfEconomy;local found={}
          for _,slug in ipairs(e.PartnerCandidates('alchemy')) do
            assert(type(slug)=='string' and not found[slug]);found[slug]=true
          end
          assert(found.mining and found.engineering and found.tailoring)
          assert(not found.alchemy and not found.cooking and not found.fishing and not found['first-aid'])
        ''')

    def test_saved_selection_is_scoped_by_character_realm_and_target(self):
        self.lua.execute(r'''
          local e=ns.ProfEconomy
          assert(not e.GetRoutePartner('alchemy'))
          e.SetRoutePartner('alchemy','mining')
          assert(e.GetRoutePartner('alchemy')=='mining' and not e.GetRoutePartner('tailoring'))
          characterName='Other';assert(not e.GetRoutePartner('alchemy'))
          e.SetRoutePartner('alchemy','engineering')
          characterName='Test';realmName='OtherRealm';assert(not e.GetRoutePartner('alchemy'))
          realmName='Realm';assert(e.GetRoutePartner('alchemy')=='mining')
        ''')
        self.load(str(ROOT / 'Core' / 'ProfEconomy.lua'))
        self.lua.execute("assert(ns.ProfEconomy.GetRoutePartner('alchemy')=='mining')")

    def test_options_for_exposes_saved_partner_without_disabling_learned_only_globally(self):
        self.lua.execute(r'''
          ns.ProfEconomy.SetRoutePartner('alchemy','mining')
          ns.ProfModule={Setting=function(key)
            if key=='autoSecondaryLeveling' or key=='autoLearnedOnly' then return true end
          end}
          local o=ns.ProfRouteAuto.OptionsFor('alchemy',1)
          assert(o.secondaryProfession=='mining' and o.allowSecondaryLeveling and o.learnedOnly)
        ''')

    def test_all_route_facade_entrypoints_block_unselected_pair_without_scheduling(self):
        self.lua.execute(r'''
          local ra=ns.ProfRouteAuto
          for _,entry in ipairs({'Get','Compute','Recalculate'}) do
            local r=ra[entry]('alchemy',{snapshot=pairFixture(),start=1,target=2,allowSecondaryLeveling=true})
            assert(r.status=='selection_required',entry..' did not request selection')
            noExecutablePlan(r)
          end
          assert(#queue==0,'selection-only request scheduled a solver')
        ''')

    def test_solver_cannot_be_used_to_bypass_selection_requirement(self):
        self.lua.execute(r'''
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=pairFixture(),start=1,target=2,allowSecondaryLeveling=true})
          assert(not j.error);noExecutablePlan(r)
          local required=r.status=='selection_required'
          for _,d in ipairs(r.diagnostics or {}) do if d.code=='secondaryRequired' then required=true end end
          assert(required,'solver did not explain missing partner')
        ''')

    def test_unlearned_target_without_joint_upgrade_cannot_use_current_two_main_professions(self):
        self.lua.execute(r'''
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=pairFixture(),start=1,target=2,allowSecondaryLeveling=false})
          assert(not j.error and r.feasible and r.targetReached and r.total==30,tostring(r.total))
          onlyPair(r,'alchemy',nil)
          assert(craftsOf(r,'mining')==0 and craftsOf(r,'engineering')==0)
        ''')

    def test_selected_learned_partner_uses_current_skill_and_excludes_other_learned_profession(self):
        self.lua.execute(r'''
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=pairFixture(),start=1,target=2,allowSecondaryLeveling=true,secondaryProfession='mining'})
          assert(not j.error and r.feasible and r.targetReached and r.total==3,tostring(r.total))
          assert(craftsOf(r,'mining')==1 and craftsOf(r,'engineering')==0)
          assert(r.finalSkills.mining==2,'existing partner reset to skill one')
          onlyPair(r,'alchemy','mining')
        ''')

    def test_selected_unlearned_partner_starts_at_one_and_counts_its_required_leveling(self):
        self.lua.execute(r'''
          local s=pairFixture()
          s.recipes[#s.recipes+1]=flat('tailoring',402,30,{{14,1}},1,2)
          s.recipes[4].learn=2;s.recipes[4].yellow=2;s.recipes[4].green=2;s.recipes[4].grey=2
          s.prices[14]=2
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=s,start=1,target=2,learnedOnly=true,allowSecondaryLeveling=true,secondaryProfession='tailoring'})
          assert(not j.error and r.feasible and r.targetReached and r.total==6,tostring(r.total))
          assert(craftsOf(r,'tailoring')==2 and r.finalSkills.tailoring==2)
          assert(craftsOf(r,'mining')==0 and craftsOf(r,'engineering')==0)
          onlyPair(r,'alchemy','tailoring')
        ''')

    def test_learned_only_is_ignored_for_unlearned_target_but_not_learned_partner(self):
        self.lua.execute(r'''
          local s=pairFixture();s.known['mining:201']=false
          local o={snapshot=s,start=1,target=2,learnedOnly=true,
            allowSecondaryLeveling=true,secondaryProfession='mining'}
          local r,j=ns.ProfRouteSolver.Compute('alchemy',o)
          assert(not j.error and r.feasible and r.targetReached and r.total==30,tostring(r.total))
          assert(craftsOf(r,'alchemy')==1 and craftsOf(r,'mining')==0)
          assert(o.learnedOnly==true,'simulation changed the global learned-only preference')
        ''')

    def test_learned_only_still_applies_to_learned_target(self):
        self.lua.execute(r'''
          local s=pairFixture();s.professions.alchemy.unlearned=nil;s.professions.alchemy.primary=true
          local r,j=ns.ProfRouteSolver.Compute('alchemy',{
            snapshot=s,start=1,target=2,learnedOnly=true,allowSecondaryLeveling=false})
          assert(not j.error and not r.feasible and #r.steps==0)
        ''')

    def test_live_capture_limits_simulated_pair_and_preserves_current_profession_state(self):
        self.lua.execute(r'''
          livePairFixture()
          local s=ns.ProfEconomy.Capture('alchemy',{
            start=1,allowSecondaryLeveling=true,secondaryProfession='tailoring'})
          assert(s.professions.alchemy.unlearned and s.professions.tailoring.unlearned)
          assert(s.professions.alchemy.cur==1 and s.professions.tailoring.cur==1)
          assert(not s.professions.mining and not s.professions.engineering)
          assert(not s.byProfession.mining and not s.byProfession.engineering)
          assert(s.byProfession.alchemy and s.byProfession.tailoring)
          assert(actualProfessions.mining.cur==2 and actualProfessions.engineering.cur==60)
          assert(not actualProfessions.alchemy and not actualProfessions.tailoring,'capture changed actual professions')
        ''')

    def test_live_capture_without_joint_upgrade_does_not_import_current_main_professions(self):
        self.lua.execute(r'''
          livePairFixture()
          local s=ns.ProfEconomy.Capture('alchemy',{start=1,allowSecondaryLeveling=false})
          assert(s.byProfession.alchemy and not s.byProfession.mining and not s.byProfession.engineering)
          assert(not s.professions.mining and not s.professions.engineering)
        ''')

    def test_pairing_change_hides_old_execution_and_waits_for_manual_recalculation(self):
        self.lua.execute(r'''
          livePairFixture()
          local ra=ns.ProfRouteAuto
          local a={start=1,target=2,allowSecondaryLeveling=true,secondaryProfession='mining'}
          local b={start=1,target=2,allowSecondaryLeveling=true,secondaryProfession='tailoring'}
          local old=finish('alchemy',a);assert(old.targetReached and old.total==3)
          local scheduled=#queue
          local changed=ra.Get('alchemy',b)
          assert(changed.status=='recalculate_required' and hasDiagnostic(changed,'pairingChanged'))
          noExecutablePlan(changed)
          assert(#queue==scheduled,'partner change automatically ran the new pair')
          ra.Recalculate('alchemy',b)
          local fresh=finish('alchemy',b);assert(fresh.targetReached and fresh.total==4)
          onlyPair(fresh,'alchemy','tailoring')
        ''')

    def test_unselected_partner_never_exposes_previously_cached_selected_pair(self):
        self.lua.execute(r'''
          livePairFixture()
          local ra=ns.ProfRouteAuto
          local old=finish('alchemy',{start=1,target=2,allowSecondaryLeveling=true,secondaryProfession='mining'})
          assert(old.feasible)
          local r=ra.Get('alchemy',{start=1,target=2,allowSecondaryLeveling=true})
          assert(r.status=='selection_required');noExecutablePlan(r)
        ''')

    def test_reload_restores_only_same_explicit_pair(self):
        self.lua.execute(r'''
          livePairFixture()
          local r=finish('alchemy',{start=1,target=2,allowSecondaryLeveling=true,secondaryProfession='mining'})
          assert(r.targetReached and r.total==3)
          beforeReload=#queue
        ''')
        self.load(str(ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute(r'''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2,
            allowSecondaryLeveling=true,secondaryProfession='mining'})
          assert(r.cached and r.total==3 and #queue==beforeReload)
          local other=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2,
            allowSecondaryLeveling=true,secondaryProfession='tailoring'})
          assert(other.status=='recalculate_required' and hasDiagnostic(other,'pairingChanged'))
          noExecutablePlan(other)
        ''')

    def test_legacy_three_profession_cached_plan_is_not_executable(self):
        self.lua.execute(r'''
          livePairFixture()
          local r=finish('alchemy',{start=1,target=2,allowSecondaryLeveling=true,secondaryProfession='mining'})
          local c=DungeonsForeverDB.prof.routeCache['Test-Realm']
          local record=c.routes[c.active.alchemy]
          record.result.professionPolicy=nil
          record.result.targetUnlearned=nil
          record.result.secondaryProfession=nil
          record.options.secondaryProfession=nil
          record.result.steps[#record.result.steps+1]={1,2,301,1,profession='engineering'}
          record.result.actions[#record.result.actions+1]={type='craft',profession='engineering',spell=301,count=1}
        ''')
        self.load(str(ROOT / 'Core' / 'ProfRouteAuto.lua'))
        self.lua.execute(r'''
          local r=ns.ProfRouteAuto.Get('alchemy',{start=1,target=2,
            allowSecondaryLeveling=true,secondaryProfession='mining'})
          assert(not r.cached,'legacy three-profession result restored')
          noExecutablePlan(r)
        ''')

    def test_cancelled_inflight_pair_cannot_publish_or_leave_dead_searching_cache(self):
        self.lua.execute(r'''
          livePairFixture()
          local ra=ns.ProfRouteAuto
          local a={start=1,target=2,allowSecondaryLeveling=true,secondaryProfession='mining'}
          local pending=ra.Get('alchemy',a)
          assert(pending.status=='searching')
          local oldPump=queue[#queue];local publications=0
          ra.OnPlanChanged(function()publications=publications+1 end)
          local blocked=ra.Get('alchemy',{start=1,target=2,allowSecondaryLeveling=true})
          assert(blocked.status=='selection_required');noExecutablePlan(blocked)
          oldPump();assert(publications==0,'cancelled pair published')
          local before=#queue
          local restored=ra.Get('alchemy',a)
          assert(restored.status~='searching' or #queue>before,
            'returning to a cancelled pair restored a searching snapshot with no live task')
        ''')


if __name__ == '__main__':
    unittest.main()
