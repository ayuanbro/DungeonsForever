"""Explicit release benchmark; wall-clock thresholds are not flaky unit tests.

Run from the repository root after building the source supplement:
python data_pipeline/professions/tests/benchmark_delivery.py --output <report.json>
Pass --baseline to the pre-change file snapshot for paired capture and complete
TOC profession/locale/UI code cold-memory measurements. --memory-only skips
capture timing; it never turns an unmeasured timing gate into a pass.
"""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / '.pipeline-runtime/lib'))
from lupa.lua51 import LuaRuntime

SLUGS = ('alchemy', 'blacksmithing', 'enchanting', 'engineering', 'leatherworking',
         'tailoring', 'mining', 'herbalism', 'skinning', 'cooking', 'fishing', 'poisons')
FILES = ('Data_Professions.lua', 'Data_ProfRecipes.lua', 'Data_ProfLeveling.lua',
         'Data_ProfSpecializations.lua', 'Data_ProfSpecializationQuests.lua', 'Data_ProfTools.lua',
         'Data_ProfMaterialSupply.lua', 'Data_ProfFormulaOffers.lua', 'Data_ProfVendors.lua',
         'Data_ProfVendorNames.lua', 'Data_ProfMining.lua')
DOMAIN = ('ProfPolicies.lua', 'ProfSupply.lua', 'VendorPriceDB.lua', 'ProfGates.lua',
          'ProfSolverCapture.lua', 'ProfLearning.lua', 'ProfClientScan.lua', 'ProfEssences.lua',
          'ProfRecovery.lua', 'ProfRouteSolver.lua')

SUPPLEMENT = Path('Core/Data/Data_ProfLearningSources.lua')
BOOTSTRAP = {'Core/Core.lua', 'Core/Hui.lua', 'Core/DungeonUI.lua', 'Core/LootFilter.lua',
             'Core/AuctionatorBridge.lua', 'Core/VendorPriceDB.lua'}


def toc_entries(text, locale):
    """Follow the real TOC order, including only the selected text locale."""
    result = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([^\[]+?)(?:\s*\[AllowLoadTextLocale (\w+)\])?', line)
        if not match or (match[2] and match[2] != locale):
            continue
        path = Path(match[1].strip().replace('\\', '/'))
        name = path.as_posix()
        if path.suffix == '.lua' and (name.startswith(('Locales/', 'Core/Data/'))
                                     or name in BOOTSTRAP
                                     or name.startswith('Core/Prof')):
            result.append(path)
    return result


def native_recipe_ids(lua):
    identities = lua.execute("""
      local result={}
      for _,slug in ipairs({...}) do
        local ids,seen={},{}
        local group=ns.ProfRecipes and ns.ProfRecipes[slug]
        for _,kind in ipairs({'rows','crafted','enchants'}) do
          for _,row in ipairs(group and group[kind] or {}) do
            local id=kind=='enchants' and row[14] or row[1]
            if type(id)=='number' and id>0 and not seen[id] then ids[#ids+1]=id;seen[id]=true end
          end
        end
        local leveling=ns.ProfLeveling and ns.ProfLeveling[slug]
        for id in pairs(leveling and leveling.rinfo or {}) do
          if type(id)=='number' and id>0 and not seen[id] then ids[#ids+1]=id;seen[id]=true end
        end
        result[slug]=ids
      end
      return result
    """, *SLUGS)
    return {slug: list(identities[slug].values()) for slug in SLUGS}


def retain_profession(lua, slug, identities):
    provider = lua.globals().ns['ProfLearningSources']
    provider['ForProfession'](slug)
    selected = lua.table()
    for spell in identities[slug]:
        record = provider['Get'](slug, spell)
        if record is not None:
            selected[spell] = record
    return selected


def full_native_vm(locale='zhCN'):
    """Reuse the complete current TOC/mocks without running a memory comparison."""
    return full_native_cold(None, locale, _vm_only=True)[0]


def full_native_cold(baseline_path, locale, *, _vm_only=False):
    """Compare resident Lua allocations with every changed profession chunk loaded.

    The snapshot preserves dirty pre-implementation files. Clean files absent
    from that snapshot come from its recorded HEAD, rather than from today's
    working tree (notably ProfRecovery and ProfSolverRun changed afterwards).
    Both VMs use identical @repository/path chunk names and explicit mocks.
    """
    manifest = (json.loads((baseline_path / 'manifest.json').read_text(encoding='utf8'))
                if not _vm_only else {})
    baseline_sources = {}
    origins = {}

    def before_source(path):
        name = path.as_posix()
        if name not in baseline_sources:
            saved = baseline_path / 'files' / path
            if saved.is_file():
                baseline_sources[name] = saved.read_text(encoding='utf8')
                origins[name] = 'pre-implementation snapshot'
            else:
                baseline_sources[name] = subprocess.check_output(
                    ['git', 'show', f'{manifest["head"]}:{name}'], cwd=ROOT).decode('utf8')
                origins[name] = 'recorded clean HEAD'
        return baseline_sources[name]

    # The small frame mock retains scripts/events just as an event-frame owner
    # would. No fabricated method fallback is used: an unsupported API fails.
    setup = r"""
      ns={__inits={}}; DungeonsForeverDB={prof={}}; MOCK_FRAMES={}; MOCK_TIMERS={}; MOCK_HOOKS={}
      format=string.format; unpack=unpack
      function wipe(t) for k in pairs(t) do t[k]=nil end return t end
      function UnitName()return 'Benchmark'end
      function GetRealmName()return 'Realm'end
      function UnitLevel()return 60 end
      function UnitRace()return 'Human','Human',1 end
      function UnitClass()return 'Rogue','ROGUE',4 end
      function UnitFactionGroup()return 'Alliance'end
      function GetLocale()return MOCK_LOCALE end
      function IsPlayerSpell(id)return type(id)=='number' and id>0 end
      function time()return 1000 end
      function GetTime()return 1000 end
      function GetBuildInfo()return '1.60.1','70658','Oct 28 2026',16001 end
      local frameMethods={}
      function frameMethods:RegisterEvent(event) self.events[event]=true end
      function frameMethods:UnregisterEvent(event) self.events[event]=nil end
      function frameMethods:SetScript(event,fn) self.scripts[event]=fn end
      function frameMethods:HookScript(event,fn) self.scripts[event]=fn end
      function frameMethods:Hide() self.shown=false end
      function frameMethods:SetText(text) self.text=text end
      function frameMethods:GetStringHeight() return self.font and self.font[2] or 15 end
      function frameMethods:SetFont(font,size,flags) self.font={font,size,flags};return true end
      function frameMethods:GetFont() return unpack(self.font or {'Fonts/FRIZQT__.TTF',15,''}) end
      function frameMethods:CreateFontString() return CreateFrame('FontString') end
      function CreateFrame(kind,name,parent)
        local frame=setmetatable({kind=kind,name=name,parent=parent,events={},scripts={}},
                                  {__index=frameMethods})
        MOCK_FRAMES[#MOCK_FRAMES+1]=frame;return frame
      end
      UIParent=CreateFrame('Frame','UIParent')
      C_Timer={After=function(delay,fn) MOCK_TIMERS[#MOCK_TIMERS+1]={delay,fn} end}
      function hooksecurefunc(...) MOCK_HOOKS[#MOCK_HOOKS+1]={...} end
      SlashCmdList={}
    """

    def measure(toc, source):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().MOCK_LOCALE = locale
        lua.execute(setup)
        start = memory(lua)
        paths = toc_entries(toc, locale)
        for path in paths:
            lua.execute("local text,name=...; assert(loadstring(text,name))('DungeonsForever',ns)",
                        source(path), '@' + path.as_posix())
        checks = lua.execute("""
          local checks={}
          for _,name in ipairs({'ProfHost','ProfModule','ProfFollow','ProfEconomy',
            'ProfExecution','ProfRouteAuto','ProfRouteSolver','ProfSolverRun'}) do
            checks[name]=type(ns[name])=='table'
          end
          checks.ClientScan=type(ns.ProfEconomy and ns.ProfEconomy.RefreshClientData)=='function'
          return checks,#MOCK_FRAMES,#MOCK_TIMERS,#ns.__inits
        """)
        exports = dict(checks[0].items())
        frames, timers, inits = checks[1:]
        checks = None  # Do not count the temporary verification table as residency.
        return lua, start, {'residentKiB': memory(lua) - start,
                'loadedFiles': [p.as_posix() for p in paths],
                'exports': exports, 'mockFrameCount': frames,
                'deferredTimerCount': timers, 'queuedInitializationCount': inits}

    current_toc = (ROOT / 'DungeonsForever.toc').read_text(encoding='utf8')
    current_sources = {p: (ROOT / p).read_text(encoding='utf8')
                       for p in toc_entries(current_toc, locale)}
    if _vm_only:
        return measure(current_toc, current_sources.__getitem__)
    _, _, before = measure(manifest['toc'], before_source)
    current, start, after = measure(current_toc, current_sources.__getitem__)
    # Discover identities in a separate VM. Walking ns.ProfRecipes in only the
    # measured current VM would also materialize original lazy Data, incorrectly
    # charging pre-existing native tables to this feature's retained-record delta.
    identities = native_recipe_ids(native())
    delta = after['residentKiB'] - before['residentKiB']
    retained = current.table()
    for slug in SLUGS:
        retained[slug] = retain_profession(current, slug, identities)
    all_delta = memory(current) - start - before['residentKiB']
    individual = {}
    for slug in SLUGS:
        vm, base, _ = measure(current_toc, current_sources.__getitem__)
        records = retain_profession(vm, slug, identities)
        individual[slug] = memory(vm) - base - before['residentKiB']
    exports_verified = all(before['exports'].values()) and all(after['exports'].values())
    return {'locale': locale, 'baseline': before, 'current': after,
            'additionalColdKiB': delta, 'budgetKiB': 256, 'withinBudget': delta <= 256,
            'singleProfessionAdditionalKiB': individual, 'allProfessionAdditionalKiB': all_delta,
            'nativeRecipeCounts': {slug: len(ids) for slug, ids in identities.items()},
            'singleProfessionBudgetKiB': 512, 'allProfessionBudgetKiB': 2048,
            'retentionScenario': 'strongly retain generated facts for every existing native recipe ID; '
                                 'each single-profession sample starts in a fresh complete current VM',
            'exportsVerified': exports_verified,
            'memoryPassed': exports_verified and delta <= 256
                            and max(individual.values()) <= 512 and all_delta <= 2048,
            'baselineHead': manifest['head'], 'baselineFileOrigins': origins,
            'scope': 'TOC-selected locales, every TOC Data Lua file, Core/Hui/DungeonUI/LootFilter, '
                     'all TOC Core/Prof* chunks, AuctionatorBridge and VendorPriceDB; pre-ADDON_LOADED',
            'limitations': ['Offline Lua5.1 allocations only; no actual client/frame engine memory.',
                            'ADDON_LOADED/PLAYER_LOGIN and queued initialization/timers are not dispatched; '
                            'UI pages, HUD widgets, active plans and opened-profession caches are not created.',
                            'Unrelated addon UI chunks and external libraries are excluded.']}


def memory(lua):
    return lua.eval("function() collectgarbage('collect'); return collectgarbage('count') end")()


def load(lua, path, overlay=None):
    source = overlay / path if overlay and (overlay / path).is_file() else ROOT / path
    lua.execute("local text,name=...; assert(loadstring(text,name))('DungeonsForever',ns)",
                source.read_text(encoding='utf8'), '@' + path.as_posix())


def native(overlay=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
      ns={IsForever=true,LoadForeverPages=true,L=setmetatable({}, {__index=function(_,k)return k end})}
      DungeonsForeverDB={prof={}}
      ns.DB=function()return DungeonsForeverDB end
      function UnitName()return 'Benchmark'end
      function GetRealmName()return 'Realm'end
      function UnitLevel()return 60 end
      function UnitRace()return 'Human','Human',1 end
      function UnitClass()return 'Rogue','ROGUE',4 end
      function UnitFactionGroup()return 'Alliance'end
      function GetLocale()return 'zhCN'end
      function IsPlayerSpell(id)return type(id)=='number' and id>0 end
      function time()return 1000 end
      function GetBuildInfo()return '1.60.1',70658 end
      ns.ProfRouteAuto={AHPriceOf=function()return 1 end}
      ns.ProfModule={ProfLearned=function()return {alchemy={cur=1,max=75}}end}
    """)
    for name in FILES:
        load(lua, Path('Core/Data') / name)
    if overlay is None:
        load(lua, Path('Core/Data/Data_ProfLearningSources.lua'))
    for name in DOMAIN:
        load(lua, Path('Core') / name, overlay)
    return lua


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--iterations', type=int, default=100)
    parser.add_argument('--memory-only', action='store_true',
                        help='Skip paired capture wall-clock timing; requires --baseline.')
    args = parser.parse_args()
    if args.memory_only and not args.baseline:
        parser.error('--memory-only requires --baseline')
    if args.memory_only:
        samples = {locale: full_native_cold(args.baseline, locale)
                   for locale in ('zhCN', 'zhTW', 'enUS')}
        report = {'environment': 'offline Lua5.1; identical named chunks and explicit client mocks',
                  'measurement': 'full-native-cold-and-retained-learning-records',
                  'locales': samples,
                  'memoryPassed': all(s['memoryPassed'] for s in samples.values()),
                  'captureMeasured': False,
                  'clientAcceptance': 'not measured; initialization/events/widgets excluded as detailed per locale'}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
        print(json.dumps({k: {field: sample[field] for field in (
            'additionalColdKiB', 'singleProfessionAdditionalKiB', 'allProfessionAdditionalKiB',
            'exportsVerified', 'memoryPassed')} for k, sample in samples.items()}, indent=2))
        return 0 if report['memoryPassed'] else 1
    # The addon consumes its existing native recipe IDs, not every discovered
    # reference entry. Keep those selected records alive to model real views;
    # a weak cache alone must not make the memory benchmark pass.
    identities = native_recipe_ids(native())
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('ns={IsForever=true}')
    before = memory(lua)
    started = time.perf_counter()
    load(lua, Path('Core/Data/Data_ProfLearningSources.lua'))
    cold_ms = (time.perf_counter() - started) * 1000
    cold = memory(lua) - before
    expanded, expansion_ms = {}, {}
    retained = lua.table()
    for slug in SLUGS:
        started = time.perf_counter()
        lua.globals().ns['ProfLearningSources']['ForProfession'](slug)
        selected = lua.table()
        for spell in identities[slug]:
            record = lua.globals().ns['ProfLearningSources']['Get'](slug, spell)
            if record is not None:
                selected[spell] = record
        retained[slug] = selected
        expansion_ms[slug] = (time.perf_counter() - started) * 1000
        expanded[slug] = memory(lua) - before
    individual = {}
    for slug in SLUGS:
        vm = LuaRuntime(unpack_returned_tuples=True)
        vm.execute('ns={IsForever=true}')
        base = memory(vm)
        load(vm, Path('Core/Data/Data_ProfLearningSources.lua'))
        vm.globals().ns['ProfLearningSources']['ForProfession'](slug)
        selected = vm.table()
        for spell in identities[slug]:
            record = vm.globals().ns['ProfLearningSources']['Get'](slug, spell)
            if record is not None:
                selected[spell] = record
        individual[slug] = memory(vm) - base
    report = {'environment': 'offline Lua5.1, mocked client, positively learned native recipes',
              'memoryScope': 'provider-only; total runtime/locale/UI increments require --memory-only --baseline',
              'coldKiB': cold, 'coldLoadMs': cold_ms, 'singleProfessionKiB': individual,
              'retentionScenario': 'strongly retain generated facts for every existing native recipe ID',
              'nativeRecipeCounts': {slug: len(ids) for slug, ids in identities.items()},
              'allProfessionKiB': max(expanded.values()), 'expansionMs': expansion_ms,
              'budgets': {'coldKiB': 256, 'singleProfessionKiB': 512, 'allProfessionKiB': 2048,
                          'captureP95RegressionPercent': 10}}
    if args.baseline:
        baseline, current = native(args.baseline / 'files'), native()
        call = "function() return ns.ProfEconomy.Capture('alchemy',{start=1,target=75}) end"
        functions = [baseline.eval(call), current.eval(call)]
        samples = [[], []]
        for fn in functions:
            for _ in range(10):
                fn()
        for i in range(args.iterations):
            for index in ((0, 1) if i % 2 == 0 else (1, 0)):
                gc.collect()
                started = time.perf_counter()
                functions[index]()
                samples[index].append((time.perf_counter() - started) * 1000)
        def p95(values):
            return sorted(values)[int(.95 * (len(values) - 1))]
        old, new = map(p95, samples)
        report['capture'] = {'iterations': args.iterations, 'baselineP95Ms': old, 'currentP95Ms': new,
                             'regressionPercent': (new / old - 1) * 100,
                             'baselineMedianMs': statistics.median(samples[0]),
                             'currentMedianMs': statistics.median(samples[1])}
    report['providerMemoryPassed'] = cold <= 256 and max(individual.values()) <= 512 and max(expanded.values()) <= 2048
    report['memoryPassed'] = report['providerMemoryPassed']
    report['capturePassed'] = report.get('capture', {}).get('regressionPercent', 0) <= 10
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, indent=2))
    return 0 if report['memoryPassed'] and report['capturePassed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
