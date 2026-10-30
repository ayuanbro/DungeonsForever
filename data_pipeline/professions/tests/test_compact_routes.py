"""Generated learning-route public fields survive the private compact codec."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / '.pipeline-runtime/lib'))
from lupa.lua51 import LuaRuntime
from data_pipeline.professions.build import RULES_VERSION, emit_lua, runtime_facts


META = {'build': '1.60.1.70658', 'fingerprint': 'a' * 64}


def record(spell, kind, status, known, *, fee=None, trainers=None, quests=None, coverage='partial'):
    route = {'id': f'{kind}:{spell}', 'kind': kind, 'status': status,
             'conditionsKnown': known,
             'conditions': [{'kind': 'skill', 'professionID': 171, 'value': 25},
                            {'kind': 'classIDs', 'values': [1, 4]},
                            {'kind': 'reputation', 'factionID': 529, 'value': 7}],
             'acquisition': {'status': 'unknown', 'conditionsKnown': False,
                             'coverage': 'partial', 'conditions': [], 'nonAuctionable': False,
                             'vendors': [{'id': 99, 'npcID': 99, 'price': 0, 'quantity': 1,
                                          'stock': -1, 'conditionsKnown': False}],
                             'quests': [{'id': 7, 'conditions': [{'kind': 'level', 'value': 10}]}],
                             'drops': [{'id': 88}]}}
    if kind == 'trainer':
        route['trainerIDs'] = [11, 12] if trainers is None else trainers
        if fee is not None:
            route['trainingCost'] = fee
    elif kind == 'item':
        route['teachingItemID'] = 50000 + spell
        route['id'] += ':' + str(route['teachingItemID'])
    else:
        route['questIDs'] = [7, 8] if quests is None else quests
        route['id'] += ':' + str(route['questIDs'][0])
    return {'spell': spell, 'profession': 'alchemy', 'coverage': coverage,
            'missingReasons': ['sourceMissing', 'sourceConflict'], 'routes': [route]}


class CompactRouteContracts(unittest.TestCase):
    def test_specialization_index_retains_alternatives_without_expanding_records(self):
        records={spell:record(spell,'item','confirmed',True) for spell in range(1,5)}
        for value in records.values():
            value['routes'][0]['conditions']=[{'kind':'ability','value':20222}]
        records[2]['routes'].append(copy.deepcopy(records[2]['routes'][0]))
        records[2]['routes'][1]['conditions']=[{'kind':'ability','value':20219}]
        records[3]['routes'].append(copy.deepcopy(records[3]['routes'][0]))
        records[3]['routes'][1]['conditions']=[]
        records[4]['routes'][0]['conditions'].append({'kind':'ability','value':17039})
        p=self.provider({'alchemy':records})
        p['Get']=lambda *_: self.fail('compact index expanded a learning record')
        self.assertEqual(p['SpecializationGroups']('alchemy',1)[1][1],20222)
        self.assertEqual([list(g.values()) for g in p['SpecializationGroups']('alchemy',2).values()],[[20222],[20219]])
        self.assertIsNone(p['SpecializationGroups']('alchemy',3))
        self.assertEqual(list(p['SpecializationGroups']('alchemy',4)[1].values()),[17039,20222])

    def test_automatic_rank_index_excludes_unknown_and_inconsistent_grants(self):
        records={spell:record(spell,'trainer','confirmed',True) for spell in range(1,6)}
        for value in records.values():
            route=value['routes'][0]
            route['conditions']=[{'kind':'skill','professionID':171,'value':1}]
            route['acquisition']={'kind':'skillGrant','status':'confirmed','coverage':'complete',
                                  'conditions':[],'minSkillRank':1,'skillLineID':171,'acquireMethod':1}
        records[2]['routes'][0]['status']='unknown'
        records[3]['routes'][0]['conditionsKnown']=False
        records[4]['routes'][0]['acquisition']['acquireMethod']=0
        records[5]['routes'][0]['acquisition']['minSkillRank']=5
        p=self.provider({'alchemy':records})
        self.assertEqual(p['AutomaticSkillRank']('alchemy',1),1)
        for spell in range(2,7):
            self.assertIsNone(p['AutomaticSkillRank']('alchemy',spell))
        self.assertIsNone(p['AutomaticSkillRank']('first-aid',1))

    def provider(self, facts):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('ns={IsForever=true}')
        self.lua.execute("assert(loadstring(...))('DungeonsForever',ns)", emit_lua(facts, META).decode('utf8'))
        self.lua.execute("""
          function same(actual,expected,path)
            path=path or 'record'
            assert(type(actual)==type(expected),path..': type changed')
            if type(expected)~='table' then
              assert(actual==expected,path..': value changed');return
            end
            for key,value in pairs(expected)do same(actual[key],value,path..'.'..tostring(key))end
            for key in pairs(actual)do assert(expected[key]~=nil,path..': unexpected '..tostring(key))end
          end
        """)
        return self.lua.globals().ns['ProfLearningSources']

    def test_all_route_kinds_statuses_known_flags_and_fees_materialize_without_changes(self):
        records, spell = {}, 100
        for kind in ('trainer', 'item', 'quest'):
            for status in ('unknown', 'confirmed', 'conflict'):
                for known in (False, True):
                    for fee in ((None, 0, 12500) if kind == 'trainer' else (None,)):
                        records[spell] = record(spell, kind, status, known, fee=fee,
                                                coverage=('none', 'partial', 'complete')[spell % 3])
                        spell += 1
        facts = {'alchemy': records}
        unchanged = copy.deepcopy(facts)
        provider = self.provider(facts)
        for spell, expected in records.items():
            with self.subTest(spell=spell, route=expected['routes'][0]['id']):
                actual = provider['Materialize'](provider['Get']('alchemy', spell))
                self.lua.globals().same(actual, self.lua.table_from(expected, recursive=True))
        self.assertEqual(facts, unchanged, 'encoding mutated normalized input facts')

    def test_shared_sets_and_condition_templates_remain_shared_in_queries_and_freezes(self):
        records = {1: record(1, 'trainer', 'confirmed', True, fee=0),
                   2: record(2, 'trainer', 'unknown', False),
                   3: record(3, 'quest', 'unknown', False),
                   4: record(4, 'quest', 'conflict', True),
                   5: record(5, 'trainer', 'unknown', False, trainers=[])}
        self.provider({'alchemy': records})
        self.lua.execute("""
          local p=ns.ProfLearningSources
          local a,b,c,d,e=p.Get('alchemy',1),p.Get('alchemy',2),p.Get('alchemy',3),p.Get('alchemy',4),p.Get('alchemy',5)
          assert(a==p.ForProfession('alchemy')[1])
          local trainers=a.routes[1].trainerIDs
          assert(trainers==b.routes[1].trainerIDs,'shared trainer set was duplicated')
          local quests=c.routes[1].questIDs
          assert(quests==d.routes[1].questIDs,'shared quest set was duplicated')
          assert(#e.routes[1].trainerIDs==0)
          assert(a.routes[1].trainingCost==0 and b.routes[1].trainingCost==nil)
          local frozen=p.Materialize({a,b,c,d,e})
          assert(frozen[1].routes[1].trainerIDs==frozen[2].routes[1].trainerIDs)
          assert(frozen[3].routes[1].questIDs==frozen[4].routes[1].questIDs)
          assert(frozen[1].routes[1].conditions==frozen[2].routes[1].conditions)
          assert(frozen[1].routes[1].acquisition==frozen[2].routes[1].acquisition)
          assert(getmetatable(frozen[1])==nil and getmetatable(frozen[1].routes[1])==nil)
          assert(rawget(frozen[1].routes[1],1)==nil,'private tuple escaped Materialize')
          assert(not pcall(function()a.spell=2 end),'named record field became writable')
          assert(not pcall(function()a.routes[1].status='unknown' end),'named route field became writable')
          local n=0;for id,value in p.Each('alchemy')do assert(value.spell==id);n=n+1 end
          assert(n==5 and p.Get('alchemy',999)==nil)
        """)

    def test_generation_is_deterministic_and_preserves_semantic_metadata(self):
        facts = {'alchemy': {25: record(25, 'item', 'conflict', False)}}
        self.assertEqual(emit_lua(facts, META), emit_lua(copy.deepcopy(facts), META))
        provider = self.provider(facts)
        self.assertEqual(provider['meta']['build'], META['build'])
        self.assertEqual(provider['meta']['fingerprint'], META['fingerprint'])
        self.assertEqual(provider['meta']['rules'], RULES_VERSION)

    def test_nested_shared_acquisition_values_roundtrip_without_changing_public_fields(self):
        records = {spell: record(spell, 'item', 'confirmed', True) for spell in (1, 2, 3)}
        for spell, value in records.items():
            source = value['routes'][0]['acquisition']
            source['drops'] = [{'id': 2**53 - 1}] + [{'id': entity} for entity in range(100, 230)]
            source['quests'][0]['id'] = spell
        provider = self.provider({'alchemy': records})
        for spell, expected in records.items():
            actual = provider['Materialize'](provider['Get']('alchemy', spell))
            self.lua.globals().same(actual, self.lua.table_from(expected, recursive=True))

    def test_runtime_projection_keeps_learning_conditions_and_minimal_source_references(self):
        facts = {'alchemy': {1: record(1, 'item', 'confirmed', True)}}
        before = copy.deepcopy(facts)
        projected = runtime_facts(facts)
        route = projected['alchemy'][1]['routes'][0]
        original = facts['alchemy'][1]['routes'][0]
        self.assertEqual(route['conditions'], original['conditions'])
        self.assertEqual(route['status'], original['status'])
        self.assertEqual(route['acquisition']['vendors'],
                         [{k:v for k,v in vendor.items() if k != 'npcID'}
                          for vendor in original['acquisition']['vendors']])
        self.assertEqual(route['acquisition']['quests'], original['acquisition']['quests'])
        self.assertTrue(route['acquisition']['dropDetailsOffline'])
        self.assertEqual(route['acquisition']['dropSourceCount'], 1)
        self.assertNotIn('drops', route['acquisition'])
        self.assertFalse(route['acquisition']['conditionsKnown'])
        self.assertEqual(facts, before)


if __name__ == '__main__':
    unittest.main()
