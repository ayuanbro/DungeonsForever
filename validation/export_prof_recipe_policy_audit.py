"""Explain native recipe exclusions without claiming current auction stock.

Run from the project: python validation/export_prof_recipe_policy_audit.py
The fixture uses real shipped recipes and NPC offers, with synthetic positive
AH prices. This separates source-policy restrictions from missing quotations.
"""
import json
import sys

from test_prof_native_data import native_runtime


PROFESSIONS = (
    "alchemy", "blacksmithing", "enchanting", "engineering",
    "leatherworking", "tailoring", "cooking", "mining", "poisons",
)

AUDIT = r'''
selected=auditProfession
local E,G=ns.ProfEconomy,ns.ProfGates
ns.ProfModule.ProfLearned=function()return {[selected]={cur=1,max=300}}end
local snapshot=E.Capture(selected,{start=1,target=300,noFormula=true,
  allowLimitedFormulas=false,autoCraftTools=false,recoveryEnabled=false})
local state={skill={[selected]=300},learned={},specializationAbilities=snapshot.specializationAbilities}
local modes={
  {key='vendor_unlimited',noFormula=true,allowLimitedFormulas=false},
  {key='vendor_with_limited',noFormula=true,allowLimitedFormulas=true},
  {key='vendor_or_auction_with_limited',noFormula=false,allowLimitedFormulas=true},
}
local result={profession=selected,recipes=#snapshot.recipes,learning={},policies={},patterns={},
  trainerOrNoPattern=0}
for _,mode in ipairs(modes)do result.policies[mode.key]={}end
local function count(map,key)map[key]=(map[key]or 0)+1 end
for _,recipe in ipairs(snapshot.recipes)do
  local allowed,reason=E.RouteRecipeEligibility(recipe,snapshot,state)
  local learning=allowed and 'allowed' or reason or 'blocked'
  count(result.learning,learning)
  local row={spell=recipe.spell,item=recipe.item,formula=recipe.formula,learning=learning,
    requiredAbility=G.RequiredAbility(recipe.spell),policies={}}
  local pattern=false
  for _,mode in ipairs(modes)do
    snapshot.noFormula=mode.noFormula;snapshot.allowLimitedFormulas=mode.allowLimitedFormulas
    local entry=E.FormulaFor(recipe,snapshot)
    local policy
    if entry then
      pattern=true
      policy=entry.usable and entry.source or entry.reason or 'unavailable'
      row.policies[mode.key]={source=entry.source,reason=entry.reason,usable=entry.usable,
        cost=entry.cost,npcID=entry.npcID,unlimited=entry.unlimited,limited=entry.limited,
        stockUnknown=entry.stockUnknown}
    else policy='trainer_or_no_pattern' end
    count(result.policies[mode.key],allowed and policy or learning)
  end
  if pattern then result.patterns[#result.patterns+1]=row
  else result.trainerOrNoPattern=result.trainerOrNoPattern+1 end
end
return result
'''


def plain(value):
    if hasattr(value, "items"):
        keys=list(value.keys())
        if keys and all(isinstance(k, int) and k>0 for k in keys):
            return [plain(value[k]) for k in sorted(keys)]
        return {str(k): plain(v) for k, v in value.items()}
    return value


def audit():
    result={
        "scope": "offline native recipe eligibility and purchasing policy",
        "assumptions": {
            "faction": "Alliance", "characterLevel": 60,
            "simulatedProfessionSkillForEligibility": 300,
            "knownRecipes": "none", "specializationAbilities": "false",
            "npcQuotes": "shipped verified supplier records",
            "auctionQuotes": "synthetic 1 copper, quantity unknown",
            "gameDirectoryAccess": False,
        },
        "notes": [
            "A route chooses recipes for its goal; inclusion does not promise every recipe appears in the cheapest route.",
            "Vendor-only pattern and limited-stock switches intentionally affect unlearned patterns; learned/trainer paths are exempt.",
            "These counts are source/policy diagnostics, not live content or purchasing acceptance.",
            "First aid and gathering/fishing are audited separately through their fixed/reference flows.",
        ],
        "professions": [],
    }
    for profession in PROFESSIONS:
        lua=native_runtime()
        lua.globals().auditProfession=profession
        result["professions"].append(plain(lua.execute(AUDIT)))
    return result


if __name__=="__main__":
    json.dump(audit(),sys.stdout,ensure_ascii=False,indent=2)
    sys.stdout.write("\n")
