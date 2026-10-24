"""Integration boundaries between upstream pages and the installed profession package."""
import re
import unittest

from test_prof_runtime import LuaRuntime, MOCKS, ROOT


def toc_entries():
    return [line.strip() for line in (ROOT / "DungeonsForever.toc").read_text(
        encoding="utf-8-sig").splitlines() if line.strip() and not line.startswith("##")]


class MergedProfessionTests(unittest.TestCase):
    def runtime(self, locale):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(MOCKS)
        lua.globals().testLocale = locale
        lua.execute("""
          GetLocale=function() return testLocale end
          ns.DB=function()
            DungeonsForeverDB=DungeonsForeverDB or {prof={}}
            return DungeonsForeverDB
          end
        """)
        load = lua.eval("function(p) assert(loadfile(p))('DungeonsForever',ns) end")
        for lang in ("zhCN", "zhTW", "enUS"):
            load(str(ROOT / "Locales" / (lang + ".lua")))
        return lua, load

    def test_toc_keeps_upstream_pages_and_loads_extensions_after_locale_catalogues(self):
        entries = toc_entries()
        paths = [entry.split(" [", 1)[0].replace("\\", "/") for entry in entries]
        retained = (
            "Core/Data/Data_Route.lua", "Core/Data/Data_QuestStartNpc.lua",
            "Core/Data/Data_QuestStartLoc.lua", "Core/Data/Data_QuestEndNpc.lua",
            "Core/Data/Data_ClassCombat.lua", "Core/Data/Data_ClassQuest.lua",
            "Core/Data/enUS/Data_ClassCombat.lua", "Core/Data/zhTW/Data_ClassCombat.lua",
            "Core/ClassCombatUI.lua", "Core/ClassQuestUI.lua",
        )
        for path in retained:
            self.assertEqual(paths.count(path), 1, path)
        extensions = ["Core/Data/" + name + ".lua" for name in (
            "Data_ProfItems", "Data_ProfFormulaQuests", "Data_ProfMining",
            "Data_ProfFishingRoutes")]
        last_overlay = max(i for i, path in enumerate(paths)
                           if path.startswith(("Core/Data/enUS/", "Core/Data/zhTW/")))
        positions = [paths.index(path) for path in extensions]
        self.assertTrue(all(i > last_overlay for i in positions))
        modules = ["Core/" + name + ".lua" for name in (
            "ProfEconomy", "ProfFishing", "ProfRouteSolver", "ProfRouteAuto",
            "ProfessionUI", "AuctionatorBridge", "ProfFollow", "ProfItemPrices")]
        module_positions = [paths.index(path) for path in modules]
        self.assertEqual(module_positions, sorted(module_positions))
        self.assertLess(max(positions), min(module_positions))
        toc = (ROOT / "DungeonsForever.toc").read_text(encoding="utf-8-sig")
        self.assertRegex(toc, r"(?m)^## OptionalDeps:.*\bAuctionator\b")

    def test_locales_keep_upstream_words_and_add_profession_translations(self):
        expected = {
            "zhCN": {"副本内": "副本内", "结束：": "结束："},
            "zhTW": {"副本内": "副本內", "等级范围": "等級範圍",
                     "职业任务": "職業任務", "输出循环": "輸出循環"},
            "enUS": {"副本内": "In dungeon", "等级范围": "Level range",
                     "职业任务": "Class quest", "输出循环": "Rotation"},
        }
        for locale, words in expected.items():
            with self.subTest(locale=locale):
                lua, _ = self.runtime(locale)
                for key, value in words.items():
                    self.assertEqual(lua.globals().ns.L[key], value)
                for key in ("搭配专业", "当前限制下没有可行路线", "已比较 %d 个状态",
                            "NPC购买价格尚未配置。"):
                    self.assertIsNotNone(lua.eval("rawget")(lua.globals().ns.L, key), key)

    def test_real_localized_catalogues_load_prof_items_prices_and_preserve_fishing_sources(self):
        for locale in ("zhCN", "zhTW", "enUS"):
            with self.subTest(locale=locale):
                lua, load = self.runtime(locale)
                for entry in toc_entries():
                    path = entry.split(" [", 1)[0].replace("\\", "/")
                    if not path.startswith("Core/Data/") or "/Data_Prof" not in path:
                        continue
                    match = re.search(r"\[AllowLoadTextLocale (\w+)\]", entry)
                    if match and match.group(1) != locale:
                        continue
                    load(str(ROOT / path))
                for name in ("ProfEconomy", "ProfFishing", "ProfRouteSolver",
                             "ProfRouteAuto", "ProfItemPrices"):
                    load(str(ROOT / "Core" / (name + ".lua")))
                lua.execute("""
                  assert(#ns.ProfRecipes.mining.rows==15,'locale erased mining extension')
                  assert(ns.ProfFormulaMeta[4597].source.questOnly)
                  assert(ns.ProfFishingRoutes)
                  assert(ns.ProfVendorOffers==nil and ns.ProfFormulaOffers==nil,
                    'obsolete merchant catalogues are still loaded')
                  assert(ns.ProfItemsMeta.schemaVersion==2 and ns.ProfItemsMeta.sources.csv.sha256)
                  assert(ns.ProfItems[6325].item_id==6325 and ns.ProfItems[6325].offers[66].cost_copper==40,
                    'TOC did not load the generated schema2 NPC quotations')
                  -- Cached 6325 sold-by JSON: Nyalah Brightfire has react=[1,1]
                  -- and cost=[[38]], so this explicit neutral seller serves both factions.
                  local neutral=ns.ProfItems[6325].offers[257006]
                  assert(neutral and neutral.side=='n' and neutral.cost_copper==38 and neutral.stock==-1,
                    'neutral seller differs from the verified sold-by JSON snapshot')
                  for _,meta in pairs(ns.ProfFormulaMeta) do
                    assert(meta.source.questOnly and not meta.source.vendors,
                      'independent quest metadata contains obsolete merchant sources')
                  end
                  for _,faction in ipairs({'Alliance','Horde'}) do
                    UnitFactionGroup=function() return faction end
                    local e=ns.ProfEconomy
                    local recipe=e.FindRecipe('cooking',7751)
                    local formula=e.FormulaFor(recipe,{known={},prices={},faction=faction=='Alliance' and 'A' or 'H'})
                    local expected=38
                    assert(formula and formula.id==6325 and formula.source=='vendor' and formula.usable)
                    assert(formula.cost==expected and formula.npcID==257006 and not formula.unpriced,
                      'formula did not use faction-appropriate cost_copper from ProfItems')
                    assert(#formula.vendorOffers>0,'supplier metadata disappeared')
                    local mapped,linked=false,false
                    for _,offer in ipairs(formula.vendorOffers) do
                      assert(offer.npcID)
                      local raw=ns.ProfItems[6325].offers[offer.npcID]
                      assert(raw and (raw.side=='n' or raw.side==(faction=='Alliance' and 'a' or 'h')),
                        'opposing-faction seller entered formula purchase candidates')
                      if offer.priceUsable then
                        assert(raw and offer.price==raw.cost_copper and not raw.currency_kind
                          and not raw.currency_id and not raw.currency_amount,
                          'formula offer did not come from a pure copper ProfItems row')
                      end
                      if offer.url then linked=true end
                      if offer.unlimited then assert((offer.quantity or offer.bundleSize)==1) end
                      local loc=ns.ProfVendors[offer.npcID]
                      if loc and loc[2] then
                        if offer.mapID then assert(offer.mapID==loc[2]) end
                        mapped=true
                      end
                    end
                    assert(mapped and linked,'NPC location or shelf evidence disappeared')
                    local r=ns.ProfFishing.Compute({start=1,target=50})
                    assert(r.targetReached and r.feasible and #r.steps==1)
                    assert(r.total==expected and r.formulaVendorTotal==expected and r.formulasTotal==expected)
                    assert(r.formulas[1].id==6325 and r.formulas[1].source=='vendor')
                    -- Already learned recipes still support the geographical
                    -- guide without buying an already learned formula.
                    e.Professions=function() return {
                      cooking={cur=1,max=300,primary=false},
                      fishing={cur=300,max=300,primary=false}} end
                    e.Known=function()return true end
                    r=ns.ProfFishing.Compute({start=1,target=50})
                    assert(r.targetReached and r.feasible and #r.steps==1,
                      testLocale..' '..faction..' '..tostring(r.status))
                    assert(r.vendorTotal==0 and r.ahTotal==0 and r.formulasTotal==0 and r.matTotal==0)
                    for _,fish in ipairs(r.fishMaterials) do
                      assert(fish.source=='fishing' and fish.count>0 and #fish.areas>0)
                    end
                    local total=0
                    for _,step in ipairs(r.steps) do total=total+step.cost end
                    assert(total==r.total,'formula procurement cost counted twice')
                    e.Known=function()return false end
                  end
                """)


if __name__ == "__main__":
    unittest.main()
