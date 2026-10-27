"""Preserved dev Data, lazy views and UI/solver integration without supplements."""
import subprocess
import unittest

from test_prof_solver_fusion import LuaRuntime, ROOT
from test_prof_native_data import native_runtime
import test_prof_recipe_data_first_aid as first_aid
import test_prof_ui_fusion as ui_fixture


class NativeRecipeDataBoundaryTests(unittest.TestCase):
    def test_main_toc_does_not_load_a_supplement_or_replacement_catalogue(self):
        toc=(ROOT/'DungeonsForever.toc').read_text(encoding='utf-8-sig')
        for forbidden in ('Data_ProfRecipeSupplements','Data_ProfLearningConditions','ProfRecipeData.lua'):
            self.assertNotIn(forbidden,toc)
        lua=native_runtime()
        lua.execute("assert(ns.ProfRecipeData==nil and ns.ProfRecipeSupplements==nil)")

    def test_original_tuple_sources_still_match_the_current_dev_revision(self):
        for relative in ('Core/Data/Data_ProfRecipes.lua','Core/Data/Data_ProfLeveling.lua',
                         'Core/Data/enUS/Data_ProfRecipes.lua','Core/Data/zhTW/Data_ProfRecipes.lua'):
            with self.subTest(path=relative):
                committed=subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)
                # Git stores LF while the Windows checkout can use CRLF.
                self.assertEqual((ROOT/relative).read_text(encoding='utf-8-sig'),
                                 committed.decode('utf-8-sig').replace('\r\n','\n'))

    def test_native_lazy_loader_only_opens_requested_original_professions(self):
        lua=native_runtime()
        lua.execute("""
          local data=ns.ProfRecipes;local originalIndex=getmetatable(data).__index
          assert(rawget(data,'alchemy')==nil and rawget(data,'tailoring')==nil)
          assert(rawget(data,'first-aid')==nil)
          ns.EnsureProfRecipes({'alchemy'})
          local group=data.alchemy;local count=#group.rows
          assert(count>0 and rawget(data,'tailoring')==nil and data['first-aid']==nil)
          ns.EnsureProfRecipes({'alchemy'});assert(data.alchemy==group and #group.rows==count)
          assert(getmetatable(data).__index==originalIndex)
          assert(ns.ProfRecipeData==nil and ns.ProfRecipeSupplements==nil)
        """)

    def test_runtime_correction_changes_normalized_views_without_rewriting_original_tuples(self):
        lua=native_runtime()
        lua.execute("""
          local E=ns.ProfEconomy;local group=ns.ProfRecipes.alchemy;local row
          for _,value in ipairs(group.rows)do if value[1]==7183 then row=value;break end end
          assert(row and row[12][1][1]==765)
          local index=getmetatable(ns.ProfRecipes).__index
          E.EnsureClientRuntime()
          ns.ProfRecipeRuntime[7183]={learned=true,validated=true,learn=2,item=5997,count=2,mats={{765,2}},
            cooldown=false,cooldownVerified=true}
          observedKnown[7183]=true
          local recipe=E.FindRecipe('alchemy',7183)
          assert(recipe.learn==2 and recipe.count==2 and recipe.mats[1][2]==2)
          assert(group.rows and row[3]==1 and row[7]==1 and row[12][1][2]==1)
          assert(getmetatable(ns.ProfRecipes).__index==index)
          assert(rawget(ns.ProfRecipes,'tailoring')==nil)
        """)

    def test_enchanting_keeps_original_enchant_and_crafted_lists_in_all_locales(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                lua=native_runtime(locale)
                lua.execute("""
                  local group=ns.ProfRecipes.enchanting
                  assert(group.rows==nil and type(group.enchants)=='table' and type(group.crafted)=='table')
                  local generic
                  for _,row in ipairs(group.enchants)do if row[14]==7418 then generic=row;break end end
                  assert(generic and generic[5]==20)
                  assert(ns.ProfLeveling.enchanting.rinfo[7418].learn==1)
                  local recipe=ns.ProfEconomy.FindRecipe('enchanting',7418)
                  assert(recipe.learn==1 and recipe.mats[1][1]==247786)
                  assert(ns.ProfRecipes['first-aid']==nil)
                  assert(ns.ProfRecipeData==nil and ns.ProfRecipeSupplements==nil)
                """)

    def test_original_alchemy_still_solves_a_real_section_without_a_supplement(self):
        for locale in ('zhCN','zhTW','enUS'):
            lua=native_runtime(locale)
            lua.execute("""
              selected='alchemy';observedKnown[7183]=true
              local recipe=ns.ProfEconomy.FindRecipe('alchemy',7183)
              assert(recipe.item==5997 and recipe.mats[1][1]==765)
              local result=ns.ProfRouteSolver.Compute('alchemy',{start=1,target=2,learnedOnly=true,
                autoCraftTools=false,recoveryEnabled=false,cpuLimitMs=1000})
              assert(result.feasible and result.targetReached and result.steps[1][3]==7183)
              assert(ns.ProfRecipeData==nil and ns.ProfRecipeSupplements==nil)
            """)

    def test_original_recipe_and_enchant_ui_renderers_accept_original_native_lists(self):
        for locale in ('zhCN','zhTW','enUS'):
            with self.subTest(locale=locale):
                lua=first_aid.runtime(locale)
                first_aid.add_route_and_execution(lua)
                lua.execute('actualData={ns.ProfData,ns.ProfRecipes,ns.ProfLeveling}')
                lua.execute(ui_fixture.UI_MOCKS)
                lua.execute('ns.ProfData,ns.ProfRecipes,ns.ProfLeveling=unpack(actualData)')
                first_aid.load(lua,'ProfessionUI')
                lua.execute("""
                  local PD=ns.ProfModule
                  PD.ItemName=function(id)assert(type(id)=='number'and id>0);return 'Item'..id,true end
                  PD.MatCol=function()return '',0,0,{}end
                  PD.MatText=function()return ''end
                  PD.PriceTipLines=function()return {}end
                  PD.KitEffectOf=function()end
                  ns.EnsureProfFormulaOffers=function()return {}end
                  PD.cur='alchemy';local native=ns.ProfRecipes.alchemy.rows[1]
                  assert(PD.RecipeSpec(native).text)
                  PD.cur='enchanting';PD.toolKey='all'
                  local group=ns.ProfRecipes.enchanting
                  local tools=PD.RecipeTool(group)
                  assert(tools[1].key=='all'and tools[1].text:find(tostring(#group.enchants),1,true))
                  assert(PD.EnchantSpec(group.enchants[1]).text)
                  assert(PD.CraftedSpec(group.crafted[1]).text)
                  assert(ns.ProfRecipes['first-aid']==nil)
                  assert(ns.ProfRecipeData==nil and ns.ProfRecipeSupplements==nil)
                """)


class NativeRecipeLifecycleTests(unittest.TestCase):
    setUp=ui_fixture.ProfessionUIFusionTests.setUp
    boot=ui_fixture.ProfessionUIFusionTests.boot

    def test_recipe_event_marks_a_candidate_stale_without_replacing_execution(self):
        self.lua.execute("""
          ns.ProfEconomy.Capture=function()return ns.ProfEconomy.Index(fixture())end
          local ra,xp=ns.ProfRouteAuto,ns.ProfExecution
          local result=finish('alchemy',{start=1,target=3})
          local run=assert(xp.Bind('alchemy',result));local original=run.plan
          ra.Invalidate('recipes')
          local shown=ra.Get('alchemy',{start=1,target=3})
          assert(shown==original and shown.stale)
          assert(run.plan==original and run.status=='active')
          assert(not ra.HasWork('alchemy'))
          assert(ns.ProfRecipeData==nil and ns.ProfRecipeSupplements==nil)
        """)


if __name__=='__main__':unittest.main()
