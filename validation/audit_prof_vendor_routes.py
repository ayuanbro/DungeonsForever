"""Read-only native profession procurement audit; JSON evidence on explicit run.

NPC records and recipe quantities are shipped data. Auction prices, character
faction and learned recipes are controlled inputs, never live-game claims.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

from test_prof_native_data import ROOT, native_runtime


def plain(value):
    if not hasattr(value, 'items'):
        return value
    values = dict(value.items())
    if values and set(values) == set(range(1, len(values) + 1)):
        return [plain(values[i]) for i in range(1, len(values) + 1)]
    return {key: plain(item) for key, item in values.items()}


def runtime(locale='zhCN', faction='A'):
    lua = native_runtime(locale)
    lua.globals().auditFaction = faction
    lua.execute('''
      function UnitFactionGroup()return auditFaction=='A' and 'Alliance' or 'Horde'end
      ns.ProfHost={DG={},Unpack=unpack};C_Item={GetItemCount=function()return 0 end}
      ns.ProfModule.ProfLearned=function()return {[selected]={cur=1,max=300}}end
      ns.Init=function()end
      function CreateFrame()
        return {RegisterEvent=function()end,UnregisterEvent=function()end,SetScript=function()end}
      end
    ''')
    for path in ('Core/Data/Data_ProfItemNames.lua', 'Core/Data/Data_VendorPrices.lua',
                 'Core/Data/Data_ProfGathering.lua', 'Core/Data/Data_ProfFishingRoutes.lua',
                 'Core/ProfRouteAuto.lua', 'Core/ProfTrack.lua', 'Core/ProfExecution.lua',
                 'Core/ProfSolverRun.lua', 'Core/ProfRoutePlans.lua', 'Core/ProfFollow.lua',
                 'Core/ProfGathering.lua', 'Core/ProfFishing.lua'):
        lua.execute("assert(loadstring(...))('DungeonsForever',ns)",
                    (ROOT / path).read_text(encoding='utf-8-sig'))
    lua.execute('''
      function auditPrice(id)
        local best
        for _,o in ipairs(ns.VendorPriceDB.GetOffers(id))do
          if o.unlimited and not o.priceOnly and o.purchasable~=false then
            best=math.min(best or math.huge,o.price/o.quantity)
          end
        end
        return best and math.max(1,math.ceil(best*1.25)) or 10000
      end
      Auctionator={API={v1={GetAuctionPriceByItemID=function(_,id)return auditPrice(id)end,
        GetAuctionAgeByItemID=function()return 0 end}}}
      ns.ProfRouteAuto.AHPriceOf=auditPrice
      function auditSnapshot(slug)
        selected=slug
        local s=ns.ProfEconomy.Capture(slug,{start=1,target=300,
          autoCraftTools=false,recoveryEnabled=false,considerAuctionSupply=false})
        for _,r in ipairs(s.recipes)do s.known[r.key]=true end
        s.professions={[slug]={cur=1,max=300}}
        return s
      end
      function auditInventory()
        local rows={};local supply=ns.EnsureProfMaterialSupply()
        for _,slug in ipairs(ns.ProfData.order)do
          local s=auditSnapshot(slug);local lv=ns.ProfLeveling[slug] or {}
          local ids,used,spells={},{},{}
          for _,id in ipairs(lv.sold or {})do ids[id]=true end
          for _,r in ipairs(s.byProfession[slug] or {})do
            for _,m in ipairs(r.mats)do
              used[m[1]]=true;spells[m[1]]=spells[m[1]] or {};table.insert(spells[m[1]],r.spell)
              if supply[m[1]] then ids[m[1]]=true end
            end
          end
          local materials={}
          for id in pairs(ids)do
            local offers=ns.VendorPriceDB.GetOffers(id);local eligible={}
            for _,o in ipairs(offers)do
              if o.unlimited and not o.priceOnly and o.available~=false and o.purchasable~=false then
                eligible[#eligible+1]=o
              end
            end
            materials[#materials+1]={id=id,name=ns.ProfItemNames[id] or ('#'..id),
              used=used[id] or false,recipes=spells[id] or {},offers=eligible,
              supplierCount=#eligible,listed=not not ids[id],referenceOnly=#eligible==0,
              catalogueHasOffer=type(supply[id])=='table'}
          end
          table.sort(materials,function(a,b)return a.id<b.id end)
          rows[#rows+1]={slug=slug,recipes=#(s.byProfession[slug] or {}),
            steps=#(lv.steps or {}),gathering=ns.ProfGatheringRoutes.HasRoute(slug),materials=materials}
        end
        return rows
      end
    ''')
    return lua


def oracle(offers, need, auction=None, stock=None):
    """Enumerate NPC pack counts/AH tails, independently of Lua's quantity DP.

    Native material records use one pack size per item. Assert that fact rather
    than silently approximate mixed sizes; those have separate synthetic tests.
    """
    if not offers:
        return need * auction if auction is not None and (stock is None or stock >= need) else None
    sizes = {o['quantity'] for o in offers}
    assert len(sizes) == 1, ('native mixed pack sizes need an expanded oracle', sizes)
    size = sizes.pop()
    price = min(o['price'] for o in offers)
    best = math.inf
    for packs in range(math.ceil(need / size) + 1):
        tail = max(0, need - packs * size)
        if tail and (auction is None or stock is not None and tail > stock):
            continue
        best = min(best, packs * price + tail * (auction or 0))
    return best if best != math.inf else None


def material_matrix(locale='zhCN', faction='A'):
    lua = runtime(locale, faction)
    inventory = plain(lua.execute('return auditInventory()'))
    unique = {m['id']: m for p in inventory for m in p['materials']}
    checks, failures, gaps = 0, [], []
    quote = lua.eval('''function(id,need,auction,stock,blocked,bound)
      local offers=ns.VendorPriceDB.GetOffers(id)
      if blocked then for _,o in ipairs(offers)do o.available=false end end
      local snap={prices={[id]=auction},offers={[id]=offers},faction=auditFaction,
        nonAuctionable={[id]=bound}}
      return ns.ProfRouteAuto.MaterialPurchases(id,need,{snapshot=snap,auctionRemaining={[id]=stock}})
    end''')
    for item in unique.values():
        offers = item['offers']
        if not offers:
            gaps.append({'id': item['id'], 'name': item['name'],
                         'reason': 'no-eligible-faction-offer' if item['catalogueHasOffer'] else 'missing-supplier-record'})
            scenarios = [(17, 100, None, False, False), (17, None, None, False, False)]
        else:
            pack = offers[0]['quantity']
            unit = min(o['price'] / o['quantity'] for o in offers)
            cheap, dear = max(1, math.floor(unit / 2)), max(1, math.ceil(unit * 1.25))
            scenarios = [(need, price, None, False, False)
                         for need in sorted({1, max(1, pack - 1), pack, pack + 1, 11 * pack + 2})
                         for price in (None, cheap, dear)]
            scenarios += [(11 * pack + 2, cheap, stock, False, False) for stock in (0, 2)]
            scenarios += [(13, dear, None, True, False), (13, None, None, True, False),
                          (13, cheap, None, False, True)]
        for need, price, stock, blocked, bound in scenarios:
            checks += 1
            answer = quote(item['id'], need, price, stock, blocked, bound)
            rows, total, complete = plain(answer[0]), answer[1], answer[2]
            expected = oracle([] if blocked else offers, need, None if bound else price, stock)
            valid = complete == (expected is not None)
            if expected is not None:
                valid = valid and abs(total - expected) < 1e-6 and sum(r['count'] for r in rows) >= need
                valid = valid and abs(sum(r['cost'] for r in rows) - total) < 1e-6
                for row in rows:
                    if row['source'] == 'vendor':
                        valid = valid and row.get('npcID') and row['count'] % row['bundleSize'] == 0
                        valid = valid and not blocked and row['unlimited']
            if not valid:
                failures.append({'item': item['id'], 'need': need, 'auction': price,
                                 'stock': stock, 'blocked': blocked, 'bound': bound,
                                 'expected': expected, 'actual': total, 'complete': complete})
    return {'locale': locale, 'faction': faction, 'checks': checks,
            'inventory': inventory, 'gaps': gaps, 'failures': failures}


def check_plan(lua, plan, snapshot, slug):
    failures = []
    mats = plain(plan['mats']) or []
    total = sum(m['cost'] for m in mats)
    if abs(total + (plan['formulasTotal'] or 0) - (plan['total'] or 0)) > 1e-5:
        failures.append({'code': 'invoiceTotal'})
    if plan['legacyPoisonGuide']:
        # User explicitly restored master's sold-list guide for Poisons.
        sold = set(lua.execute("return ns.ProfLeveling.poisons.sold").values())
        for row in mats:
            if (row.get('source') == 'vendor') != (row.get('id', row.get(1)) in sold):
                failures.append({'code': 'poisonGuideSource', 'item': row.get('id', row.get(1))})
        return failures
    purchased, spent, npc = defaultdict(int), defaultdict(float), defaultdict(int)
    for row in mats:
        item = row.get('id', row.get(1))
        purchased[item] += row['count']
        spent[item] += row['cost']
        if row.get('source') == 'vendor':
            npc[item] += row['count']
            offers = plain(snapshot['offers'][item]) or []
            matches = [o for o in offers if o.get('npcID') == row.get('npcID')
                       and o.get('unlimited') and o.get('purchasable') is not False]
            if not matches or row['count'] % row['bundleSize']:
                failures.append({'code': 'invalidNPC', 'item': item})
    # Only external leaves are compared: intermediate crafting/retained tools
    # have their own timing and recovery obligations, not a flat shopping list.
    used, made, formula_stock = defaultdict(int), set(), defaultdict(int)
    for action in plain(plan['actions']) or []:
        if action['type'] in ('craft', 'convert', 'specialization_quest'):
            for item, quantity in action.get('inputs', []):
                used[item] += quantity
            for item, quantity in action.get('outputs', []):
                made.add(item)
        elif action['type'] == 'formula' and action['source'] == 'ah':
            formula_stock[action['item']] += action['count']
    for item, need in used.items():
        offers = [o for o in (plain(snapshot['offers'][item]) or [])
                  if o.get('unlimited') and o.get('available') is not False
                  and o.get('purchasable') is not False and not o.get('priceOnly')]
        if item in made or not offers or not purchased[item]:
            continue
        expected = oracle(offers, need, snapshot['prices'][item])
        if expected is not None and spent[item] > expected + 1e-5:
            failures.append({'code': 'avoidableLeafCost', 'item': item,
                             'need': need, 'actual': spent[item], 'expected': expected})
    if npc and plan['feasible'] is not False:
        hud = plain(lua.eval('''function(slug,plan)
          local run=ns.ProfExecution.Bind(slug,plan,{force=true})
          return ns.ProfFollow.VendorPurchases(slug,run and run.plan or plan)
        end''')(slug, plan))
        found = defaultdict(int)
        for row in hud:
            found[row['id']] += row['missing']
        if dict(found) != dict(npc):
            failures.append({'code': 'hudNPCQuantity', 'planned': dict(npc), 'hud': dict(found)})
    return failures


def route_matrix(faction='A'):
    lua = runtime('zhCN', faction)
    inventory = plain(lua.execute('return auditInventory()'))
    rows = []
    for profession in inventory:
        slug = profession['slug']
        snapshot = lua.eval('auditSnapshot')(slug)
        lua.globals().auditSnap = snapshot
        lua.execute('observedKnown={};for _,r in ipairs(auditSnap.recipes)do observedKnown[r.spell]=true end')
        modes = ['fixed'] if profession['steps'] else []
        if profession['recipes'] and profession['steps'] and slug not in ('first-aid', 'poisons'):
            modes += ['cheapest', 'matcost', 'crafts', 'optim']
        if slug == 'cooking':
            modes += ['fishing']
        for mode in modes:
            row = {'profession': slug, 'mode': mode, 'faction': faction}
            try:
                plan = lua.execute('''
                  local slug,mode=...
                  local opts={snapshot=auditSnap,start=1,target=300,scheme=mode,
                    autoCraftTools=false,recoveryEnabled=false,considerAuctionSupply=false,
                    maxNodes=1}
                  if mode=='fixed' then return ns.ProfRouteAuto.FixedPlan(slug,opts) end
                  local result=ns.ProfRouteAuto.Compute(slug,opts);return result
                ''', slug, mode)
                row.update({key: plan[key] for key in ('status', 'feasible', 'targetReached',
                           'plannedTo', 'total', 'vendorTotal', 'ahTotal', 'crafts', 'budgetLimited',
                           'searchTermination', 'referenceOnly', 'clientPending')})
                row['stepCount'] = len(plan['steps'] or [])
                row['materials'] = plain(plan['mats'])
                row['blockers'] = plain(plan['blockingDiagnostics'])
                row['failures'] = check_plan(lua, plan, snapshot, slug)
            except Exception as error:
                row['failures'] = [{'code': 'auditException', 'detail': str(error)}]
            rows.append(row)
            print(slug, mode, faction, row.get('plannedTo'), row.get('status'),
                  'failures', len(row['failures']), flush=True)
        if profession['gathering']:
            steps = plain(lua.execute('return ns.ProfGatheringRoutes.Steps(...,300,{maxSkill=300})', slug))
            failures = []
            for step in steps or []:
                if step[3] != 0 or step[4] != 0 or not step.get('navigationOnly'):
                    failures.append({'code': 'gatheringFabricatedCraft'})
            rows.append({'profession': slug, 'mode': 'gathering', 'faction': faction,
                         'steps': len(steps or []), 'failures': failures})
        if not modes and not profession['gathering']:
            rows.append({'profession': slug, 'mode': 'no-leveling-route', 'faction': faction,
                         'failures': []})
    return rows


def input_hashes():
    paths = sorted((ROOT / 'Core').rglob('*.lua'))
    return {str(p.relative_to(ROOT)).replace('\\', '/'):
            hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--routes', action='store_true')
    parser.add_argument('--faction', choices=('A', 'H'), help='Limit both matrices to one faction')
    args = parser.parse_args()
    before = input_hashes()
    factions = (args.faction,) if args.faction else ('A', 'H')
    report = {'evidence': 'native NPC/recipe data; simulated prices and learned recipes; no live game',
              'routeOptions': {'start': 1, 'target': 300, 'maxNodes': 1, 'cpuLimitMs': 8000,
                               'autoCraftTools': False, 'recoveryEnabled': False,
                               'considerAuctionSupply': False},
              'materials': []}
    for locale in ('zhCN', 'zhTW', 'enUS'):
        for faction in factions:
            row = material_matrix(locale, faction)
            report['materials'].append(row)
            print(locale, faction, row['checks'], 'checks;', len(row['failures']), 'failures', flush=True)
    if args.routes:
        report['routes'] = [row for faction in factions for row in route_matrix(faction)]
    report['inputHashes'] = before
    after = input_hashes()
    report['changedInputsDuringAudit'] = sorted(p for p in before.keys() | after.keys()
                                               if before.get(p) != after.get(p))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return int(bool(report['changedInputsDuringAudit']) or
               any(row['failures'] for row in report['materials'] + report.get('routes', [])))


if __name__ == '__main__':
    raise SystemExit(main())
