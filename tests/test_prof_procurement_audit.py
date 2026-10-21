"""Exercise real localized profession data against independently checked receipts."""
import re
import unittest

from test_prof_vendor import LuaRuntime, MOCKS, ROOT


CRAFTING = {
    "alchemy", "blacksmithing", "enchanting", "engineering", "leatherworking",
    "tailoring", "mining", "cooking", "poisons",
}


def actual_runtime(locale):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCKS)
    lua.globals().auditLocale = locale
    lua.execute("""
      ns.LoadForeverPages=true
      ns.L=setmetatable({}, {__index=function(_,key)return key end})
      GetLocale=function()return auditLocale end
      IsSpellKnown=function()return true end
      C_Item={GetItemInfo=function(id)return 'Item '..id,nil,1,1,1,nil,nil,nil,nil,nil,0,nil,nil,0 end,
        GetItemCount=function()error('full procurement read bag or bank stock')end}
      GetItemInfo=C_Item.GetItemInfo
      function auditPrice(id)return 13+id%17 end
      Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id)return auditPrice(id)end}}}
    """)
    ns = lua.globals().ns
    for raw in (ROOT / "DungeonsForever.toc").read_text(encoding="utf-8-sig").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        path = raw.split(" [", 1)[0].replace("\\", "/")
        if not path.startswith("Core/Data/") or "/Data_Prof" not in path:
            continue
        condition = re.search(r"\[AllowLoadTextLocale (\w+)\]", raw)
        if condition and condition.group(1) != locale:
            continue
        lua.execute((ROOT / path).read_text(encoding="utf-8-sig"), "Audit", ns)
    for name in ("ProfEconomy", "ProfRouteSolver", "ProfRouteAuto", "ProfFishing", "ProfItemPrices"):
        lua.execute((ROOT / "Core" / (name + ".lua")).read_text(encoding="utf-8-sig"), "Audit", ns)
    ns.EnsureProfRecipes()
    lua.execute(AUDIT)
    return lua


AUDIT = r'''
local E=ns.ProfEconomy
E.Known=function()return true end
E.Have=function()error('full procurement read material inventory')end
function auditNonempty(value)
    return value~=nil and (type(value)~='string' or value:find('%S')~=nil)
end
function auditReceipt(result)
    assert(result and result.total~=nil,'route returned no cost result')
    local total,vendor,auction=0,0,0
    for _,m in ipairs(result.mats or {})do
        local id=m.id or m[1];local count=m.count or m[2]
        assert(type(id)=='number' and type(count)=='number' and count>0 and count==math.floor(count))
        assert(type(m.cost)=='number' and m.cost>=0 and not m.unpriced)
        if m.source=='vendor' or m.vendor then
            assert(m.npcID==nil,'ordinary material purchase acquired a supplier identity')
            assert(ns.ProfMaterialSupplyMeta and ns.ProfMaterialSupplyMeta.schemaVersion==1,
                'material purchase has no qualified supply schema')
            local item=assert(ns.ProfMaterialSupply[id],'NPC receipt has no material supply evidence')
            local matched=false
            local roles={profession_supply=true,trade_supply=true,reagent_supply=true,
                general_goods=true,cooking_supply=true,fishing_supply=true}
            for _,offer in pairs(item.offers or {})do
                local side=offer.side
                local eligible=offer.eligible==true and offer.stockState=='unlimited'
                    and offer.costKind=='gold' and offer.access=='unconditional' and roles[offer.role]
                    and (side=='n' or side=='a' and UnitFactionGroup('player')=='Alliance'
                        or side=='h' and UnitFactionGroup('player')=='Horde')
                local packs=offer.quantity and count/offer.quantity
                if eligible and offer.sourceURL and offer.verifiedAt and offer.evidenceHash
                    and packs and packs==math.floor(packs) and m.cost==packs*offer.price
                    and m.bundleSize==offer.quantity and m.unit==offer.price/offer.quantity
                    and m.quoteSource==offer.priceSource then matched=true end
            end
            assert(matched,'material receipt has no matching qualified unlimited gold supply')
            vendor=vendor+m.cost
        else
            assert(m.source=='ah' and m.cost==auditPrice(id)*count,'AH receipt is not an actual AH purchase')
            auction=auction+m.cost
        end
        total=total+m.cost
    end
    for _,f in ipairs(result.formulas or {})do
        if f.source=='vendor' then
            local raw=assert(ns.ProfItems[f.id].offers[f.npcID])
            assert(f.cost==raw.cost_copper)
            for _,key in ipairs({'currency_kind','currency_id','currency_amount'})do
                assert(not auditNonempty(raw[key]),'exchange formula was priced as gold')
            end
            vendor=vendor+f.cost
        else
            assert(f.source=='ah' and f.cost==auditPrice(f.id))
            auction=auction+f.cost
        end
        total=total+f.cost
    end
    assert(result.total==total,'receipt total disagrees with purchases')
    assert(result.vendorTotal==vendor and result.ahTotal==auction,'source subtotals disagree')
    assert(result.total==result.vendorTotal+result.ahTotal)
    local stepCost=0;for _,step in ipairs(result.steps or {})do stepCost=stepCost+(step.cost or 0)end
    assert(math.abs(stepCost-result.total)<1e-7,'step cash disagrees with receipts')
end
function auditCandidates()
    local out={}
    for slug,data in pairs(ns.ProfRecipes)do
        local guide=ns.ProfLeveling and ns.ProfLeveling[slug]
        local choices={}
        for _,kind in ipairs({'rows','crafted','enchants'})do
            for _,row in ipairs(data[kind] or {})do
                local r=E.Normalize(row,slug,kind)
                local legacy=kind=='rows' or guide and guide.rinfo and guide.rinfo[r and r.spell]
                if r and legacy and r.grey>r.learn and r.learn<300 and #r.mats>0
                    and not r.cooldown and not r.cooldownUnknown and not r.outputConflict and not r.clientPending then
                    choices[#choices+1]=r
                end
            end
        end
        table.sort(choices,function(a,b)return a.learn<b.learn or a.learn==b.learn and a.spell<b.spell end)
        if choices[1] then out[slug]=choices[1] end
    end
    return out
end
function auditSmallRoute(slug,selected,scheme)
    local start=selected.learn
    E.Professions=function()return {[slug]={cur=start,max=300,primary=true}}end
    local bans={}
    for _,kind in ipairs({'rows','crafted','enchants'})do
        for _,row in ipairs(ns.ProfRecipes[slug][kind] or {})do
            local r=E.Normalize(row,slug,kind)
            if r and r.spell~=selected.spell then bans[r.key]='ban' end
        end
    end
    local guide=ns.ProfLeveling and ns.ProfLeveling[slug]
    for spell in pairs(guide and guide.rinfo or {})do
        if spell~=selected.spell then bans[slug..':'..spell]='ban' end
    end
    -- An obsolete sold list must never suppress the actual auction market.
    if not guide then guide={};ns.ProfLeveling[slug]=guide end
    local priorSold=guide.sold;guide.sold={}
    for _,m in ipairs(selected.mats)do guide.sold[#guide.sold+1]=m[1]end
    ns.ProfRouteAuto.Invalidate('audit')
    local opts={start=start,target=start+1,scheme=scheme,exclusions=bans,learnedOnly=true,referenceFallback=false}
    local result
    if scheme=='fixed' then result=ns.ProfRouteAuto.SummarizeSteps({{start,start+1,selected.spell,1}},slug)
    else result=ns.ProfRouteAuto.Compute(slug,opts) end
    guide.sold=priorSold
    assert(result and result.completeCost and #(result.steps or {})>0,slug..':'..scheme..' has no priced route')
    if scheme=='cheapest' then assert(result.feasible and result.targetReached) end
    auditReceipt(result)
    return result
end
'''


class ProfessionProcurementAudit(unittest.TestCase):
    def test_all_real_crafting_professions_and_schemes_have_consistent_receipts_in_all_locales(self):
        for locale in ("zhCN", "zhTW", "enUS"):
            lua = actual_runtime(locale)
            candidates = lua.globals().auditCandidates()
            self.assertEqual(set(candidates.keys()), CRAFTING)
            for slug, recipe in candidates.items():
                for scheme in ("cheapest", "matcost", "crafts", "optim", "fixed"):
                    with self.subTest(locale=locale, profession=slug, scheme=scheme):
                        lua.globals().auditSmallRoute(slug, recipe, scheme)

    def test_real_material_quotes_require_supply_evidence_while_formula_quotes_keep_npc_rules(self):
        for locale in ("zhCN", "zhTW", "enUS"):
            with self.subTest(locale=locale):
                lua = actual_runtime(locale)
                rows, priced = lua.execute('''
                  local rows,priced=0,0
                  for id,item in pairs(ns.ProfItems)do
                    for _,raw in pairs(item.offers)do rows=rows+1 end
                    for _,faction in ipairs({'A','H'})do
                      local context={faction=faction}
                      for _,q in ipairs(ns.ProfItemPrices.GetOffers(id,context))do
                        assert(q.npcID==nil and q.name==nil and q.areaID==nil and q.stockStatus==nil)
                        assert(q.materialPrice and q.priceBasis=='Data_ProfMaterialSupply')
                        local supply=assert(ns.ProfMaterialSupply[id],'root price fabricated material supply')
                        local matched=false
                        for _,raw in pairs(supply.offers or {})do
                          if raw.eligible==true and raw.stockState=='unlimited' and raw.costKind=='gold'
                            and raw.access=='unconditional' and raw.price==q.price and raw.quantity==q.quantity
                            and raw.priceSource==q.source and raw.evidenceHash and raw.verifiedAt and raw.sourceURL
                            and (raw.side=='n' or raw.side=='a' and faction=='A' or raw.side=='h' and faction=='H')then
                            matched=true
                          end
                        end
                        assert(matched,'material quote has no matching current supply evidence')
                        priced=priced+1
                      end
                      if not ns.ProfMaterialSupply[id]then
                        assert(#ns.ProfItemPrices.GetOffers(id,context)==0,'root cost proved NPC availability')
                      end
                      for _,q in ipairs(ns.ProfItemPrices.GetFormulaOffers(id,context))do
                        local raw=assert(item.offers[q.npcID])
                        assert(q.stock==nil,'reference refresh cap became live stock')
                        if q.price~=nil then assert(q.price==raw.cost_copper and q.quantity==item.VendorStackCount) end
                        if raw.stock and raw.stock>=0 then assert(q.limited and q.maxStock==raw.stock) end
                        if raw.stock==0 then assert(not q.priceUsable) end
                      end
                    end
                    if not next(item.offers)then
                      assert(#ns.ProfItemPrices.GetFormulaOffers(id)==0,'root base price fabricated an NPC')
                    end
                  end
                  assert(ns.ProfVendorOffers==nil and ns.ProfFormulaOffers==nil,'old catalogue was loaded by the actual TOC')
                  return rows,priced
                ''')
                self.assertGreater(rows, 1000)
                self.assertGreater(priced, 0)

    def test_gathering_and_unresolved_catalogues_do_not_fabricate_purchase_recipes(self):
        for locale in ("zhCN", "zhTW", "enUS"):
            with self.subTest(locale=locale):
                lua = actual_runtime(locale)
                lua.execute('''
          local E=ns.ProfEconomy
          for _,slug in ipairs({'herbalism','skinning','fishing','first-aid','camping'})do
            E.Professions=function()return {[slug]={cur=1,max=300,primary=slug=='herbalism' or slug=='skinning'}}end
            local s=E.Capture(slug,{})
            assert(#s.recipes==0,slug..' unexpectedly gained authoritative crafting inputs')
            local r=ns.ProfRouteSolver.Compute(slug,{snapshot=s,start=1,target=2})
            assert(not r.targetReached and #r.mats==0 and r.vendorTotal==0 and r.ahTotal==0)
          end
          E.Professions=function()return {comprehension={cur=1,max=300}}end
          local s=E.Capture('comprehension',{})
          local r=ns.ProfRouteSolver.Compute('comprehension',{snapshot=s,start=1,target=2})
          assert(not r.targetReached and #r.mats==0,'grey comprehension craft became a leveling recipe')
          r=ns.ProfRouteSolver.Procure(s,277651,1)
          assert(r.feasible and r.costComplete and r.total==auditPrice(17056))
          assert(#r.steps==1 and r.steps[1][3]==1302508,'real comprehension material craft was not exercised')
          auditReceipt(r)
          E.Professions=function()return {cooking={cur=1,max=300},fishing={cur=1,max=300}}end
          local fish=ns.ProfFishing.Compute({start=1,target=2})
          assert(fish.feasible and fish.targetReached and fish.total==0 and #fish.fishMaterials>0)
          assert(fish.vendorTotal==0 and fish.ahTotal==0 and fish.formulasTotal==0)
          for _,m in ipairs(fish.fishMaterials)do assert(m.source=='fishing' and m.count>0) end
                ''')


if __name__ == "__main__":
    unittest.main()
