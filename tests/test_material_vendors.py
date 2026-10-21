"""Supply evidence, refresh failures and price units are independent of buy-price metadata."""
import argparse
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'df-data-pipeline/_temp'))
material = importlib.import_module('fc_material_vendors')
FIXTURES = Path(__file__).parent / 'fixtures/material-vendors'
NPC = (FIXTURES / 'npc-5514.html').read_text(encoding='utf-8')
ITEM = (FIXTURES / 'item-2880.html').read_text(encoding='utf-8')


def evidence(kind='npc', entity=5514):
    return {'sourceURL': material.entity_url(kind, entity), 'verifiedAt':'2026-10-21T00:00:00Z',
            'evidenceHash':'a'*64, 'gameFlavor':'forever', 'sourceBuild':''}


def snapshot(html=NPC):
    npc, rows = material.shelf_page(html, 5514)
    return {'schemaVersion':1, 'gameFlavor':'forever', 'generatedAt':'2026-10-21T00:00:00Z',
            'registry':{'5514':{'id':5514}}, 'shelves':{'5514':{'status':'ok','npc':npc,'rows':rows,'evidence':evidence()}},
            'coverage':{'complete':False}}


class Client:
    def __init__(self, failures=()): self.failures, self.calls = set(failures), []
    def fetch(self, kind, entity):
        self.calls.append((kind,entity))
        if kind in self.failures: raise material.PipelineError('fixture unavailable')
        return (NPC if kind=='npc' else ITEM), evidence(kind,entity)


class MaterialVendorTests(unittest.TestCase):
    def offers(self, value=None, prices=None):
        return material.eligible_offers(value or snapshot(), prices or {})[0]

    def test_realistic_shelf_qualifies_flux_but_not_limited_ingot_or_unknown_linen(self):
        result=self.offers()
        self.assertEqual(set(result),{2880})
        offer=result[2880]['offers'][5514]
        self.assertEqual((offer['price'],offer['quantity'],offer['side']),(100,1,'a'))
        self.assertEqual(offer['priceSource'],'wowhead_npc_bundle')

    def test_root_prices_never_create_availability(self):
        self.assertNotIn(2589,self.offers(prices={2589:{'price':1,'quantity':1}}))

    def test_npc_price_wins_even_if_client_is_cheaper(self):
        self.assertEqual(self.offers(prices={2880:{'price':1,'quantity':1}})[2880]['offers'][5514]['price'],100)

    def test_npc_purchase_bundle_is_not_max_stack(self):
        value=snapshot(); row=value['shelves']['5514']['rows'][0]
        row.update({'stack':[5],'cost':[[20,[],[]]],'maxstack':200})
        self.assertEqual(self.offers(value)[2880]['offers'][5514]['quantity'],5)

    def test_mixed_token_and_multiple_alternative_prices_are_rejected(self):
        for cost in ([[0,[[3402,10]],[]]],[[100,[],[[1,3]]]],[[100,[],[]],[200,[],[]]],[[False,[],[]]]):
            value=snapshot();value['shelves']['5514']['rows'][0]['cost']=cost
            self.assertNotIn(2880,self.offers(value))

    def test_gold_only_flag_cannot_override_malformed_or_alternative_costs(self):
        for cost in ('tokens',[[10,[],[]],[0,[[123,1]],[]]]):
            value=snapshot();value['shelves']['5514']['rows'][0].update({'cost':cost,'goldOnly':True})
            self.assertNotIn(2880,self.offers(value,{2880:{'price':100,'quantity':1}}))

    def test_explicit_gold_missing_amount_allows_only_equal_client_bundle(self):
        value=snapshot();value['shelves']['5514']['rows'][0].update({'cost':[[None,[],[]]],'stack':[5]})
        self.assertNotIn(2880,self.offers(value,{2880:{'price':20,'quantity':1}}))
        offer=self.offers(value,{2880:{'price':20,'quantity':5}})[2880]['offers'][5514]
        self.assertEqual((offer['price'],offer['priceSource']),(20,'client_base_bundle'))

    def test_missing_currency_information_does_not_enable_client_fallback(self):
        value=snapshot();value['shelves']['5514']['rows'][0].pop('cost')
        self.assertNotIn(2880,self.offers(value,{2880:{'price':100,'quantity':1}}))

    def test_unknown_hostile_and_non_supplier_npc_are_rejected(self):
        for field,val in [('role',None),('role','quartermaster'),('side',None)]:
            value=snapshot();value['shelves']['5514']['npc'][field]=val
            self.assertFalse(self.offers(value))

    def test_neutral_reaction_is_not_explicit_friendly_access(self):
        self.assertIsNone(material.side_from_react([0,0]))
        self.assertEqual(material.side_from_react([1,0]),'a')
        value=snapshot();value['shelves']['5514']['rows'][0]['react']=[-1,1]
        self.assertNotIn(2880,self.offers(value))

    def test_each_explicit_friendly_faction_survives_other_faction_unknown(self):
        self.assertEqual(material.side_from_react([1,None]),'a')
        self.assertEqual(material.side_from_react([None,1]),'h')
        self.assertEqual(material.side_from_react([1,1]),'n')
        self.assertIsNone(material.side_from_react([None,None]))
        self.assertIsNone(material.side_from_react([False,None]))

    def test_missing_null_or_boolean_standing_is_not_unconditional(self):
        for standing in ('missing',None,False):
            value=snapshot();row=value['shelves']['5514']['rows'][0]
            if standing=='missing':row.pop('standing')
            else:row['standing']=standing
            self.assertNotIn(2880,self.offers(value))

    def test_conditions_are_not_hidden_by_role_override(self):
        for condition in ({'standing':4},{'requiredQuestID':123},{'conditions':[1]},{'event':5}):
            value=snapshot();value['shelves']['5514']['rows'][0].update(condition)
            self.assertNotIn(2880,self.offers(value))

    def test_zero_stock_boolean_stock_and_missing_stock_are_not_unlimited(self):
        for stock in (0,1,None,False,'-1'):
            value=snapshot();value['shelves']['5514']['rows'][0]['avail']=stock
            self.assertNotIn(2880,self.offers(value))

    def test_unknown_or_alternative_bundles_are_rejected(self):
        for count in (None,[],[1,5],[0],[True],['5']):
            value=snapshot();value['shelves']['5514']['rows'][0]['stack']=count
            self.assertNotIn(2880,self.offers(value))

    def test_valid_explicit_empty_shelf_is_distinct_from_missing_tab(self):
        empty=NPC.replace('data:[{"id":2880', 'data:[{"id":2880')
        start=empty.index("new Listview")
        empty=empty[:start]+"new Listview({template:'item',id:'sells',data:[]});</script></body></html>"
        self.assertEqual(material.shelf_page(empty,5514)[1],[])
        with self.assertRaises(material.PipelineError):material.shelf_page(empty.replace("id:'sells'","id:'outfit'"),5514)

    def test_challenge_truncation_wrong_environment_and_wrong_id_are_failures(self):
        for html in ('<html>JavaScript is disabled</html>',NPC.replace('</html>',''),NPC.replace('"env":16','"env":4'),NPC.replace('typeId: 5514','typeId: 5515')):
            with self.assertRaises(material.PipelineError):material.shelf_page(html,5514)

    def test_capped_and_duplicate_rows_are_rejected(self):
        with self.assertRaises(material.PipelineError):material.shelf_page(NPC.replace("id:'sells'","id:'sells',totalCount:999"),5514)
        with self.assertRaises(material.PipelineError):material.shelf_page(NPC.replace('"id":2840','"id":2880'),5514)

    def test_discovery_reads_npc_ids_and_refreshes_known_npc_after_seed_failure(self):
        self.assertEqual(material.discovery_page(ITEM,2880)[0][0]['id'],5514)
        client=Client(failures=('item',))
        value=material.collect({'seedItemIDs':[2880],'npcs':{}},snapshot(),client)
        self.assertEqual(client.calls,[('item',2880),('npc',5514)])
        self.assertEqual(value['shelves']['5514']['status'],'ok')

    def test_refresh_failure_downgrades_old_eligibility_and_retains_evidence(self):
        value=material.collect({'seedItemIDs':[2880],'npcs':{}},snapshot(),Client(failures=('npc',)))
        self.assertEqual(value['shelves']['5514']['status'],'failed')
        self.assertEqual(value['shelves']['5514']['previousEvidence']['evidenceHash'],'a'*64)
        self.assertFalse(self.offers(value))

    def test_manual_tombstone_does_not_fetch_or_reappear(self):
        client=Client();value=material.collect({'seedItemIDs':[2880],'npcs':{'5514':{'enabled':False,'reason':'removed'}}},snapshot(),client)
        self.assertEqual(client.calls,[('item',2880)])
        self.assertFalse(self.offers(value))

    def test_semantic_fingerprint_ignores_refresh_timestamp_and_html_hash(self):
        first=snapshot();material.generate(first,{})
        second=snapshot();second['shelves']['5514']['evidence'].update({'verifiedAt':'2026-10-22T00:00:00Z','evidenceHash':'b'*64})
        material.generate(second,{})
        self.assertEqual(first['eligibility']['fingerprint'],second['eligibility']['fingerprint'])
        second['shelves']['5514']['rows'][0]['cost']=[[99,[],[]]];material.generate(second,{})
        self.assertNotEqual(first['eligibility']['fingerprint'],second['eligibility']['fingerprint'])

    def test_prepare_batch_frozen_inputs_and_offline_replay(self):
        with tempfile.TemporaryDirectory(prefix='material-vendors-',dir=ROOT/'.pipeline-runtime') as folder:
            base=Path(folder);config=base/'config.json';snap=base/'snapshot.json';prices=base/'prices.csv';lua=base/'supply.lua'
            opts=argparse.Namespace(material_config=config,material_snapshot=snap,prices_csv=prices,material_output_lua=lua,material_cache_root=base/'cache',offline=True,
                input_overrides={config:json.dumps({'schemaVersion':1,'gameFlavor':'forever','seedItemIDs':[2880],'npcs':{}}).encode(),snap:json.dumps(snapshot()).encode(),prices:b'ItemID,BuyPriceCopper,VendorStackCount,PriceStatus\n2880,1,1,priced\n'})
            outputs,observed=material.prepare_batch(opts)
            self.assertIn(b'wowhead_npc_bundle',outputs[lua]);self.assertFalse(lua.exists());self.assertFalse(snap.exists())
            self.assertEqual(observed[0]['sha256'],hashlib.sha256(opts.input_overrides[config]).hexdigest())
            self.assertEqual(json.loads(outputs[snap])['eligibility']['items'],1)

    def test_paths_outside_checkout_are_rejected_before_network(self):
        opts=argparse.Namespace(material_config=ROOT.parent/'outside.json')
        with self.assertRaises(material.PipelineError):material.prepare_batch(opts)

    def test_snapshot_provenance_and_identity_validation(self):
        for mutate in (lambda x:x['shelves']['5514']['npc'].update(id=1),lambda x:x['shelves']['5514']['evidence'].update(evidenceHash='bad'),lambda x:x['shelves']['5514']['evidence'].update(sourceURL='https://evil.example/npc=5514'),lambda x:x['shelves']['5514']['evidence'].update(verifiedAt=123),lambda x:x['shelves']['5514']['npc'].update(conditions=None),lambda x:x['registry']['5514'].update(id=3)):
            value=snapshot();mutate(value)
            with self.assertRaises(material.PipelineError):material.validate_snapshot(value)

    def test_maintenance_role_aliases_are_editable_and_ambiguity_rejected(self):
        config=json.loads(material.DEFAULT_CONFIG.read_bytes())
        config['roleAliases']['profession_supply'].append('Local Material Shop')
        material.validate_config(config)
        self.assertEqual(material.role_from_tag('Local Material Shop',config['roleAliases']),'profession_supply')
        config['roleAliases']['trade_supply'].append('Local Material Shop')
        with self.assertRaises(material.PipelineError):material.validate_config(config)

    def test_robots_failure_opens_batch_circuit_without_repeated_requests(self):
        client=material.PageClient(ROOT/'.pipeline-runtime/material-fetch-test')
        with mock.patch.object(client,'_http',side_effect=OSError('offline')) as request:
            for item in (2320,2324):
                with self.assertRaises(material.PipelineError):client.fetch('item',item)
            self.assertEqual(request.call_count,1)

    def test_raw_reparse_uses_checked_hash_and_rejects_tampering(self):
        value=snapshot();e=value['shelves']['5514']['evidence']
        e.update({'rawPath':str((FIXTURES/'npc-5514.html').relative_to(ROOT)),
                  'evidenceHash':hashlib.sha256((FIXTURES/'npc-5514.html').read_bytes()).hexdigest()})
        value['shelves']['5514']['npc']['side']=None
        material.reparse_snapshot(value,json.loads(material.DEFAULT_CONFIG.read_bytes()))
        self.assertEqual(value['shelves']['5514']['npc']['side'],'a')
        self.assertEqual(material.evidence_observations(value)[0]['sha256'],e['evidenceHash'])
        e['evidenceHash']='a'*64
        with self.assertRaises(material.PipelineError):material.reparse_snapshot(value,{})

    def test_failed_shelf_with_old_raw_is_never_resurrected(self):
        value=snapshot();value['shelves']['5514'].update({'status':'failed','reason':'refresh unavailable'})
        value['shelves']['5514']['evidence']['rawPath']=str((FIXTURES/'npc-5514.html').relative_to(ROOT))
        material.reparse_snapshot(value,{})
        self.assertFalse(self.offers(value))

    def test_maintenance_tombstone_boolean_reason_and_typos_are_validated(self):
        base={'schemaVersion':1,'gameFlavor':'forever','seedItemIDs':[2880],'npcs':{}}
        for entry in ({'enabled':0},{'enabled':False},{'enabled':False,'reason':' '},{'enable':False}):
            config=deepcopy(base);config['npcs']['5514']=entry
            with self.assertRaises(material.PipelineError):material.validate_config(config)

    def test_report_delta_includes_price_change_and_eligibility_removal(self):
        old=snapshot();material.generate(old,{})
        new=snapshot();new['shelves']['5514']['rows'][0]['cost']=[[99,[],[]]]
        delta=material.offer_delta(old,new,{})
        self.assertEqual(delta['changedPrices'][0]['before']['price'],100)
        new['shelves']['5514']['status']='failed'
        self.assertEqual(material.offer_delta(old,new,{})['removedOffers'],['2880:5514'])


if __name__=='__main__':unittest.main()
