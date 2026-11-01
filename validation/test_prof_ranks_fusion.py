"""Rank guidance uses live caps and preserves reference-data uncertainty."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.pipeline-runtime'/'lib'))
from lupa.lua51 import LuaRuntime

class RankFusionTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
          ns={LoadForeverPages=true}
          function GetLocale()return 'zhCN' end
          function UnitLevel()return 60 end
          function UnitFactionGroup()return 'Alliance' end
          function GetProfessions()return 1 end
          function GetProfessionInfo()return 'Alchemy',nil,60,75,nil,nil,171 end
        """)
        for f in ['Core/Data/Data_ProfTrainers.lua','Core/ProfRanks.lua']:
            self.lua.execute("assert(loadstring(...))('DF',ns)",(ROOT/f).read_text(encoding='utf-8'))

    def test_real_cap_marks_completed_rank_without_using_planned_skill(self):
        self.lua.execute("""
          ns.ProfEconomy={Professions=function()return {alchemy={cur=300,max=300}} end}
          local step=ns.ProfRanks.NextStep('alchemy',300)
          assert(step.rank==2 and step.cap==150 and not step.complete)
          assert(step.available and step.state.maxSkill==75)
        """)

    def test_missing_api_stays_unknown_even_with_solver_assumed_cap(self):
        self.lua.execute("""
          GetProfessions=nil
          ns.ProfEconomy={Professions=function()return {alchemy={cur=300,max=300}} end}
          local step=ns.ProfRanks.NextStep('alchemy',300)
          assert(not step.complete and step.status=='unknown')
        """)

    def test_target_inside_live_cap_does_not_block_on_next_rank(self):
        self.lua.execute("assert(ns.ProfRanks.NextStep('alchemy',70)==nil)")

    def test_book_and_quest_guidance_retains_unknown_missing_level(self):
        self.lua.execute("""
          function GetProfessionInfo()return 'Cooking',nil,200,150,nil,nil,185 end
          local steps=ns.ProfRanks.RouteSteps('cooking',300)
          assert(steps[3].method=='book' and steps[3].status=='unknown' and not steps[3].available)
          assert(steps[4].method=='quest' and steps[4].reminderSkill==200)
          assert(steps[3].levelRequired==nil)
        """)

    def test_sources_follow_current_faction_and_include_coordinates(self):
        self.lua.execute("""
          local step=ns.ProfRanks.NextStep('alchemy',300)
          assert(#step.sources>0)
          for _,s in ipairs(step.sources)do assert(s.faction~='H' and s.map and s.x and s.y)end
          local lines=ns.ProfRanks.Lines(step)
          assert(#lines>1 and ns.ProfRanks.Title(step):find('150',1,true))
        """)

    def test_real_cap_completion_overrides_skill_points(self):
        self.lua.execute("""
          function GetProfessionInfo()return 'Alchemy',nil,1,300,nil,nil,171 end
          assert(ns.ProfRanks.NextStep('alchemy',300)==nil)
          local steps=ns.ProfRanks.RouteSteps('alchemy',300)
          for _,s in ipairs(steps)do assert(s.complete)end
        """)

if __name__=='__main__':unittest.main()
