"""Lazy data entrypoints retain data while releasing one-time Lua factories."""
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.pipeline-runtime' / 'lib'))
from lupa.lua51 import LuaRuntime


FILES = (
    'Data_BIS', 'Data_ClassCombat', 'Data_ClassGuide', 'Data_ClassQuest',
    'Data_DungeonQuestFlow', 'Data_DungeonQuests', 'Data_Gear',
    'Data_GearVendors', 'Data_ProfFormulaOffers', 'Data_ProfMaterialSupply',
    'Data_ProfNPCLocs', 'Data_ProfSources', 'Data_ProfTrainers',
)
ENTRIES = {
    'EnsureBISData': 'BIS',
    'EnsureClassCombat': 'ClassCombat',
    'EnsureClassGuide': 'ClassGuide',
    'EnsureClassQuestInfo': 'ClassQuestInfo',
    'EnsureDungeonQuestExtInfo': 'DungeonQuestExtInfo',
    'EnsureDungeonQuestFlow': 'DungeonQuestFlow',
    'EnsureGearData': 'GearData',
    'EnsureGearSrc': 'GearSrc',
    'EnsureGearVendors': 'GearVendors',
    'EnsureProfFormulaOffers': 'ProfFormulaOffers',
    'EnsureProfMaterialSupply': 'ProfMaterialSupply',
    'EnsureProfNPCLocs': 'ProfNPCLocs',
    'EnsureProfSources': 'ProfSources',
    'EnsureProfTrainers': 'ProfTrainers',
}
LOCALES = ('zhCN', 'enUS', 'zhTW')


def runtime(locale):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
      ns={IsForever=true,LoadForeverPages=true}
      function heap()
        collectgarbage('collect');collectgarbage('collect')
        return collectgarbage('count')
      end
      function count(t)local n=0;for _ in pairs(t)do n=n+1 end;return n end
      function snapshot(value,seen)
        local kind=type(value)
        if kind=='string'then return string.format('%q',value)end
        if kind~='table'then return kind..':'..tostring(value)end
        seen=seen or {n=0}
        if seen[value]then return '@'..seen[value]end
        seen.n=seen.n+1;seen[value]=seen.n
        local keys={}
        for key,child in pairs(value)do
          if type(child)~='function'then keys[#keys+1]=key end
        end
        table.sort(keys,function(a,b)
          if type(a)~=type(b)then return type(a)<type(b)end
          return tostring(a)<tostring(b)
        end)
        local out={}
        for _,key in ipairs(keys)do
          out[#out+1]=snapshot(key)..'='..snapshot(value[key],seen)
        end
        return '{'..table.concat(out,'|')..'}'
      end
    ''')
    lua.globals().locale = locale
    lua.execute('function GetLocale()return locale end')
    load = lua.eval("function(source,path)assert(loadstring(source,'@'..path))('DungeonsForever',ns)end")
    directories = [ROOT / 'Core' / 'Data']
    if locale != 'zhCN':
        directories.append(directories[0] / locale)
    for directory in directories:
        for name in FILES:
            path = directory / (name + '.lua')
            if path.exists():
                load(path.read_text(encoding='utf-8-sig'), str(path.relative_to(ROOT)))
    lua.globals().entries = lua.table_from(ENTRIES)
    return lua


class DataFactoryMemoryTests(unittest.TestCase):
    def test_lazy_data_is_only_built_when_requested(self):
        for locale in LOCALES:
            with self.subTest(locale=locale):
                lua = runtime(locale)
                lua.execute('''
                  for name,field in pairs(entries)do
                    assert(type(ns[name])=='function',name)
                    local eager=locale=='enUS'and (field=='ClassCombat'or field=='ProfTrainers')
                    assert((ns[field]~=nil)==eager,field)
                  end
                  assert(type(ns.EnsureGearData().items)=='table')
                  assert(ns.GearSrc==nil,'loading equipment also expanded its sources')
                  assert(type(ns.EnsureBISData().levels)=='table')
                  assert(ns.BIS.classes==ns.BIS.levels[ns.BIS.default].classes)
                  assert(type(ns.EnsureProfSources())=='table'and type(ns.ProfZoneText)=='table')
                ''')

    def test_factories_collect_and_all_generated_data_survives(self):
        for locale in LOCALES:
            with self.subTest(locale=locale):
                lua = runtime(locale)
                lua.execute('''
                  retired=setmetatable({},{__mode='v'});live={}
                  for name,field in pairs(entries)do
                    retired[name]=ns[name]
                    local first=ns[name]()
                    assert(type(first)=='table'and first==ns[field],name)
                    assert(first==ns[name]()and first==ns[name](),name)
                    live[name]=first
                  end
                  local before=snapshot(ns)
                  heap()
                  assert(count(retired)==0,'one-time generators remain reachable')
                  for name,field in pairs(entries)do assert(ns[name]()==live[name],name)end
                  assert(snapshot(ns)==before,'collection or repeated reads changed data')
                ''')

    def test_preloaded_tables_release_unused_factories_too(self):
        for locale in LOCALES:
            with self.subTest(locale=locale):
                lua = runtime(locale)
                lua.execute('''
                  retired=setmetatable({},{__mode='v'})
                  for name,field in pairs(entries)do
                    local existing=ns[field]or {sentinel=field}
                    ns[field]=existing;retired[name]=ns[name]
                    assert(ns[name]()==existing and ns[name]()==existing,name)
                  end
                  heap()
                  assert(count(retired)==0,'early return retained an unused generator')
                ''')

    def test_lightweight_readers_follow_namespace_replacements(self):
        for locale in LOCALES:
            with self.subTest(locale=locale):
                lua = runtime(locale)
                lua.execute('''
                  for name,field in pairs(entries)do
                    local initial=ns[name]()
                    local replacement={sentinel=field}
                    ns[field]=replacement
                    assert(ns[name]()==replacement,'reader captured an obsolete table: '..name)
                    ns[field]=initial
                    assert(ns[name]()==initial,name)
                  end
                ''')


if __name__ == '__main__':
    unittest.main()
