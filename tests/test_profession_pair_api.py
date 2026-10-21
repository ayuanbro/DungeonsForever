"""API profession identity agrees across route inputs and the profession page."""
import unittest

from test_prof_runtime import MOCKS, LuaRuntime, ROOT


class ProfessionPairAPITests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCKS)
        load = self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        for name in ('Data/Data_Professions.lua', 'ProfEconomy.lua',
                     'ProfRouteSolver.lua', 'ProfRouteAuto.lua'):
            load(str(ROOT / 'Core' / name))
        source = (ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        begin = source.index('local NAV_SKILL_SLUG =')
        end = source.index('local function NavAccent()', begin)
        self.lua.execute('PD={};ns.ProfModule=PD')
        self.lua.execute(source[begin:end])

    def test_only_first_aid_in_last_api_slot_is_recognized_as_learned(self):
        self.lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")(
            str(ROOT / 'Core/Data/Data_ProfLeveling.lua'))
        self.lua.execute(r'''
          GetProfessions=function()return nil,nil,nil,nil,nil,6 end
          GetProfessionInfo=function(index)
            assert(index==6,'an empty profession slot was queried')
            return 'First Aid',1,95,150,nil,nil,129
          end
          local e=ns.ProfEconomy
          local api,page=e.Professions(),PD.ProfLearned()
          assert(ns.ProfData.pro['first-aid'])
          assert(api['first-aid'].cur==95 and not api['first-aid'].primary)
          assert(page['first-aid'].cur==api['first-aid'].cur)
          assert(not api.firstaid and not page.firstaid)
          local context=e.RouteContext('first-aid',{allowSecondaryLeveling=true})
          assert(not context.unlearned and not context.requiresPartner)
          local result=ns.ProfRouteAuto.Compute('first-aid',{
            snapshot={recipes={{profession='first-aid',spell=101,item=10,
              count=1,learn=1,yellow=200,green=250,grey=300,mats={{11,1}},cooldown=false}},
              professions=api,known={},prices={[11]=7}},
            start=95,target=96,learnedOnly=true,allowSecondaryLeveling=true})
          assert(result.mode=='fixed' and result.scheme=='fixed')
          assert(result.status~='selection_required' and not result.secondaryProfession)
          assert(#result.steps>0 and #result.mats>0)
          assert(result.steps[1][3]==ns.ProfLeveling['first-aid'].steps[1][3])
          assert(result.steps[#result.steps][2]==96)
          for _,step in ipairs(result.steps) do
            assert(step[3]~=101,'First Aid reused an automatic candidate instead of its fixed guide')
          end
          for _,d in ipairs(result.diagnostics or {}) do assert(d.code~='secondaryRequired') end
        ''')

    def test_sparse_api_preserves_primary_partner_and_secondary_identity(self):
        self.lua.execute(r'''
          GetProfessions=function()return nil,2,nil,nil,nil,6 end
          GetProfessionInfo=function(index)
            if index==2 then return 'Mining',1,125,150,nil,nil,186 end
            if index==6 then return 'First Aid',1,95,150,nil,nil,129 end
            error('unexpected profession slot')
          end
          local e=ns.ProfEconomy
          local api=e.Professions()
          assert(api.mining.primary and not api['first-aid'].primary)
          local context=e.RouteContext('alchemy',{
            allowSecondaryLeveling=true,secondaryProfession='mining'})
          assert(context.unlearned and context.requiresPartner and context.partnerValid)
          local snapshot=e.Capture('alchemy',{snapshot={professions=api},
            allowSecondaryLeveling=true,secondaryProfession='mining'})
          assert(snapshot.professions.alchemy.unlearned)
          assert(snapshot.professions.mining.cur==125 and not snapshot.professions.mining.unlearned)
          assert(not snapshot.professions['first-aid'])
        ''')


if __name__ == '__main__':
    unittest.main()
