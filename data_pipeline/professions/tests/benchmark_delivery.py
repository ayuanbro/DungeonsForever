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
import hashlib
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


class BaselineSources:
    """Read an immutable recorded baseline; never mix in today's source files."""

    def __init__(self, snapshot, repository=None):
        self.snapshot = Path(snapshot).resolve()
        if self.snapshot.name == 'files' and (self.snapshot.parent / 'manifest.json').is_file():
            self.snapshot = self.snapshot.parent
        self.manifest = json.loads((self.snapshot / 'manifest.json').read_text(encoding='utf8'))
        self.head = self.manifest.get('head')
        if not isinstance(self.head, str) or not re.fullmatch(r'[0-9a-fA-F]{40,64}', self.head):
            raise ValueError('baseline manifest must record a full Git commit hash')
        self.repository = Path(repository or ROOT).resolve()
        self.sources, self.origins, self.hashes = {}, {}, {}

    def read(self, path):
        path = Path(path)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('baseline source must be repository-relative')
        name = path.as_posix()
        if name not in self.sources:
            saved = self.snapshot / 'files' / path
            if saved.is_file():
                data = saved.read_bytes()
                self.origins[name] = 'pre-implementation snapshot'
            else:
                # A missing historical file is an error, including when a new
                # file happens to exist in the current or isolated source tree.
                data = subprocess.check_output(
                    ['git', 'show', f'{self.head}:{name}'], cwd=self.repository,
                    stderr=subprocess.PIPE)
                self.origins[name] = 'recorded clean HEAD'
            self.hashes[name] = hashlib.sha256(data).hexdigest()
            self.sources[name] = data.decode('utf8')
        return self.sources[name]


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


def retain_profession(lua, slug, identities, *, materialize=False):
    provider = lua.globals().ns['ProfLearningSources']
    provider['ForProfession'](slug)
    selected = lua.table()
    for spell in identities[slug]:
        record = provider['Get'](slug, spell)
        if record is not None:
            selected[spell] = record
    return provider['Materialize'](selected) if materialize else selected


def full_native_vm(locale='zhCN', *, source_root=None):
    """Reuse the complete current TOC/mocks without running a memory comparison."""
    return full_native_cold(None, locale, _vm_only=True, source_root=source_root)[0]


def full_native_cold(baseline_path, locale, *, _vm_only=False, source_root=None,
                     baseline_repository=None, retain_learning_details=False):
    """Compare resident Lua allocations with every changed profession chunk loaded.

    The snapshot preserves dirty pre-implementation files. Clean files absent
    from that snapshot come from its recorded HEAD, rather than from today's
    working tree (notably ProfRecovery and ProfSolverRun changed afterwards).
    Both VMs use identical @repository/path chunk names and explicit mocks.
    """
    source_root = Path(source_root or ROOT).resolve()
    historical = None if _vm_only else BaselineSources(baseline_path, baseline_repository)
    manifest = historical.manifest if historical else {}

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

    current_toc = (source_root / 'DungeonsForever.toc').read_text(encoding='utf8')
    current_sources = {p: (source_root / p).read_text(encoding='utf8')
                       for p in toc_entries(current_toc, locale)}
    if _vm_only:
        return measure(current_toc, current_sources.__getitem__)
    _, _, before = measure(manifest['toc'], historical.read)
    current, start, after = measure(current_toc, current_sources.__getitem__)
    # Discover identities in a separate VM. Walking ns.ProfRecipes in only the
    # measured current VM would also materialize original lazy Data, incorrectly
    # charging pre-existing native tables to this feature's retained-record delta.
    identities = native_recipe_ids(native(source_root=source_root))
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
    report = {'locale': locale, 'baseline': before, 'current': after,
            'additionalColdKiB': delta, 'budgetKiB': 256, 'withinBudget': delta <= 256,
            'singleProfessionAdditionalKiB': individual, 'allProfessionAdditionalKiB': all_delta,
            'nativeRecipeCounts': {slug: len(ids) for slug, ids in identities.items()},
            'singleProfessionBudgetKiB': 512, 'allProfessionBudgetKiB': 2048,
            'retentionScenario': 'strongly retain generated facts for every existing native recipe ID; '
                                 'each single-profession sample starts in a fresh complete current VM',
            'exportsVerified': exports_verified,
            'memoryPassed': exports_verified and delta <= 256
                            and max(individual.values()) <= 512 and all_delta <= 2048,
            'sourceRoot': str(source_root),
            'baselineHead': historical.head, 'baselineFileOrigins': historical.origins,
            'baselineSourceSHA256': historical.hashes,
            'currentSourceSHA256': {p.as_posix(): hashlib.sha256((source_root / p).read_bytes()).hexdigest()
                                    for p in current_sources},
            'scope': 'TOC-selected locales, every TOC Data Lua file, Core/Hui/DungeonUI/LootFilter, '
                     'all TOC Core/Prof* chunks, AuctionatorBridge and VendorPriceDB; pre-ADDON_LOADED',
            'limitations': ['Offline Lua5.1 allocations only; no actual client/frame engine memory.',
                            'ADDON_LOADED/PLAYER_LOGIN and queued initialization/timers are not dispatched; '
                            'UI pages, HUD widgets, active plans and opened-profession caches are not created.',
                            'Unrelated addon UI chunks and external libraries are excluded.',
                            'Default retention keeps record/route views, not lazily decoded condition/acquisition pools.']}
    if retain_learning_details:
        vm, base, _ = measure(current_toc, current_sources.__getitem__)
        selected = vm.table()
        for slug in SLUGS:
            selected[slug] = retain_profession(vm, slug, identities)
        # One copy keeps repeated templates shared, as a complete snapshot copy
        # does; retaining only weak provider views would hide these allocations.
        materialized = vm.globals().ns['ProfLearningSources']['Materialize'](selected)
        selected = None
        all_materialized = memory(vm) - base - before['residentKiB']
        detailed = {}
        for slug in SLUGS:
            one, initial, _ = measure(current_toc, current_sources.__getitem__)
            frozen = retain_profession(one, slug, identities, materialize=True)
            detailed[slug] = memory(one) - initial - before['residentKiB']
        report['materializedLearning'] = {
            'singleProfessionAdditionalKiB': detailed,
            'allProfessionAdditionalKiB': all_materialized,
            'retentionScenario': 'strongly retain plain materialized records including every referenced '
                                 'conditions/acquisition/trainer/quest/gap field; one shared copy per sample',
            'singleProfessionBudgetKiB': 512, 'allProfessionBudgetKiB': 2048,
            'withinBudgets': max(detailed.values()) <= 512 and all_materialized <= 2048,
            'scope': 'Additional explicit frozen-fact scenario; reported separately from the original view-retention gate.'}
    return report


def memory(lua):
    return lua.eval("function() collectgarbage('collect'); return collectgarbage('count') end")()


def load(lua, path, overlay=None, *, source_root=None):
    historical = (overlay if isinstance(overlay, BaselineSources)
                  else BaselineSources(overlay) if overlay is not None else None)
    source = historical.read(path) if historical else (Path(source_root or ROOT) / path).read_text(encoding='utf8')
    lua.execute("local text,name=...; assert(loadstring(text,name))('DungeonsForever',ns)",
                source, '@' + path.as_posix())


def native(overlay=None, *, source_root=None, profession='alchemy', learned=True,
           baseline_repository=None):
    historical = (overlay if isinstance(overlay, BaselineSources) else
                  BaselineSources(overlay, baseline_repository) if overlay is not None else None)
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().BENCH_PROFESSION = profession
    lua.globals().BENCH_LEARNED = learned
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
      function IsPlayerSpell(id)return BENCH_LEARNED and type(id)=='number' and id>0 end
      function time()return 1000 end
      function GetBuildInfo()return '1.60.1',70658 end
      ns.ProfRouteAuto={AHPriceOf=function()return 1 end}
      ns.ProfModule={ProfLearned=function()return {[BENCH_PROFESSION]={cur=1,max=75}}end}
    """)
    for name in FILES:
        load(lua, Path('Core/Data') / name, historical, source_root=source_root)
    if historical is None:
        load(lua, Path('Core/Data/Data_ProfLearningSources.lua'), source_root=source_root)
    for name in DOMAIN:
        load(lua, Path('Core') / name, historical, source_root=source_root)
    return lua


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--iterations', type=int, default=100)
    parser.add_argument('--source-root', type=Path, default=ROOT,
                        help='Current game-source tree, e.g. an isolated committed checkout plus the new supplement.')
    parser.add_argument('--baseline-repository', type=Path, default=ROOT,
                        help='Git repository containing the baseline manifest commit; independent of --source-root.')
    parser.add_argument('--capture-case', action='append', metavar='PROFESSION:learned|unlearned',
                        help='Explicit paired Capture scenarios; default remains alchemy:learned only.')
    parser.add_argument('--retain-learning-details', action='store_true',
                        help='Also report strong materialized conditions/acquisition retention separately from compact views.')
    parser.add_argument('--memory-only', action='store_true',
                        help='Skip paired capture wall-clock timing; requires --baseline.')
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    if args.iterations < 1:
        parser.error('--iterations must be positive')
    cases = []
    for value in args.capture_case or ['alchemy:learned']:
        slug, separator, mode = value.partition(':')
        if not separator or slug not in SLUGS or mode not in ('learned', 'unlearned'):
            parser.error('--capture-case must be a supported PROFESSION:learned|unlearned')
        if (slug, mode) not in cases:
            cases.append((slug, mode))
    if args.memory_only and not args.baseline:
        parser.error('--memory-only requires --baseline')
    if args.memory_only and args.capture_case:
        parser.error('--memory-only cannot measure --capture-case')
    if args.capture_case and not args.baseline:
        parser.error('--capture-case requires a recorded --baseline for the paired comparison')
    if args.memory_only:
        samples = {locale: full_native_cold(args.baseline, locale, source_root=source_root,
                                          baseline_repository=args.baseline_repository,
                                          retain_learning_details=args.retain_learning_details)
                   for locale in ('zhCN', 'zhTW', 'enUS')}
        report = {'environment': 'offline Lua5.1; identical named chunks and explicit client mocks',
                  'measurement': 'full-native-cold-and-retained-learning-records',
                  'locales': samples,
                  'sourceRoot': str(source_root),
                  'baselineRepository': str(args.baseline_repository.resolve()),
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
    identities = native_recipe_ids(native(source_root=source_root))
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('ns={IsForever=true}')
    before = memory(lua)
    started = time.perf_counter()
    load(lua, SUPPLEMENT, source_root=source_root)
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
        load(vm, SUPPLEMENT, source_root=source_root)
        vm.globals().ns['ProfLearningSources']['ForProfession'](slug)
        selected = vm.table()
        for spell in identities[slug]:
            record = vm.globals().ns['ProfLearningSources']['Get'](slug, spell)
            if record is not None:
                selected[spell] = record
        individual[slug] = memory(vm) - base
    report = {'environment': 'offline Lua5.1, mocked client; explicit per-case learning state',
              'sourceRoot': str(source_root),
              'dataSHA256': hashlib.sha256((source_root / SUPPLEMENT).read_bytes()).hexdigest(),
              'currentSourceSHA256': {str(path): hashlib.sha256((source_root / path).read_bytes()).hexdigest()
                                      for path in [SUPPLEMENT, *(Path('Core') / name for name in DOMAIN)]},
              'memoryScope': 'provider-only; total runtime/locale/UI increments require --memory-only --baseline',
              'coldKiB': cold, 'coldLoadMs': cold_ms, 'singleProfessionKiB': individual,
              'retentionScenario': 'strongly retain generated facts for every existing native recipe ID',
              'nativeRecipeCounts': {slug: len(ids) for slug, ids in identities.items()},
              'allProfessionKiB': max(expanded.values()), 'expansionMs': expansion_ms,
              'budgets': {'coldKiB': 256, 'singleProfessionKiB': 512, 'allProfessionKiB': 2048,
                          'captureP95RegressionPercent': 10}}
    if args.retain_learning_details:
        frozen_vm = LuaRuntime(unpack_returned_tuples=True)
        frozen_vm.execute('ns={IsForever=true}')
        initial = memory(frozen_vm)
        load(frozen_vm, SUPPLEMENT, source_root=source_root)
        selected = frozen_vm.table()
        for slug in SLUGS:
            selected[slug] = retain_profession(frozen_vm, slug, identities)
        materialized = frozen_vm.globals().ns['ProfLearningSources']['Materialize'](selected)
        selected = None
        frozen_all = memory(frozen_vm) - initial
        frozen_single = {}
        for slug in SLUGS:
            one = LuaRuntime(unpack_returned_tuples=True)
            one.execute('ns={IsForever=true}')
            base = memory(one)
            load(one, SUPPLEMENT, source_root=source_root)
            frozen = retain_profession(one, slug, identities, materialize=True)
            frozen_single[slug] = memory(one) - base
        report['materializedLearning'] = {
            'singleProfessionKiB': frozen_single, 'allProfessionKiB': frozen_all,
            'singleProfessionBudgetKiB': 512, 'allProfessionBudgetKiB': 2048,
            'withinBudgets': max(frozen_single.values()) <= 512 and frozen_all <= 2048,
            'retentionScenario': 'plain strongly retained Materialize copies including lazy conditions/acquisition; '
                                 'one shared copy per sample',
            'scope': 'Provider-only explicit frozen-fact scenario, separate from default view-retention gate.'}
    if args.baseline:
        historical = BaselineSources(args.baseline, args.baseline_repository)
        observations = []
        for slug, mode in cases:
            baseline = native(historical, source_root=source_root, profession=slug, learned=mode == 'learned')
            current = native(source_root=source_root, profession=slug, learned=mode == 'learned')
            call = "function() return ns.ProfEconomy.Capture(" + json.dumps(slug) + ",{start=1,target=75}) end"
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
            observation = {'profession': slug, 'learned': mode == 'learned',
                           'iterations': args.iterations, 'baselineP95Ms': old, 'currentP95Ms': new,
                           'regressionPercent': (new / old - 1) * 100,
                           'baselineMedianMs': statistics.median(samples[0]),
                           'currentMedianMs': statistics.median(samples[1])}
            describe = current.eval("""function(s)
              local recipes,unlearned,records,routes=0,0,0,0
              for _,r in ipairs(s.recipes or {})do
                recipes=recipes+1;if not (s.known or {})[r.key]then unlearned=unlearned+1 end
                if r.learningInfo then records=records+1;routes=routes+#(r.learningInfo.routes or {})end
              end
              return {recipes=recipes,unlearned=unlearned,learningRecords=records,learningRoutes=routes}
            end""")
            retained_before = memory(current)
            captured = functions[1]()
            observation['currentFacts'] = dict(describe(captured).items())
            observation['currentRetainedCaptureKiB'] = memory(current) - retained_before
            observation['scope'] = 'Warmed Capture only, target 75, no route solve, UI, execution history or initial provider lookup.'
            observations.append(observation)
        # Keep the old field available for the old single default scenario.
        if cases == [('alchemy', 'learned')]:
            report['capture'] = observations[0]
        report['captureScenarios'] = observations
        report['baselineHead'] = historical.head
        report['baselineSourceOrigins'] = historical.origins
        report['baselineSourceSHA256'] = historical.hashes
        report['baselineRepository'] = str(historical.repository)
    report['providerMemoryPassed'] = cold <= 256 and max(individual.values()) <= 512 and max(expanded.values()) <= 2048
    report['memoryPassed'] = report['providerMemoryPassed']
    report['captureMeasured'] = bool(args.baseline)
    report['capturePassed'] = (all(row['regressionPercent'] <= 10 for row in report['captureScenarios'])
                               if args.baseline else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, indent=2))
    return 0 if report['memoryPassed'] and report['capturePassed'] is not False else 1


if __name__ == '__main__':
    raise SystemExit(main())
