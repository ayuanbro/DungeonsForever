"""Generic NPC affiliation collection, cache recovery and replay contracts."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('generic_npc_collector', ROOT / 'scripts/gen_vendors.py')
COLLECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECTOR)


def payload(name='Example Merchant', affiliation='Example Faction', faction_id=None):
    faction = affiliation
    if faction_id is not None:
        faction = '<a href="/forever/faction=%d">%s</a>' % (faction_id, affiliation)
    return {'name': name, 'tooltip': '<table><tr><td><b>%s</b></td></tr>'
            '<tr><td>General Supplies</td></tr><tr><td>Level 25 Humanoid (Normal)</td></tr>'
            '%s</table>' % (name, '<tr><td>%s</td></tr>' % faction if faction else ''),
            'map': {'zone': 50, 'coords': {'0': [[12.3, 45.6]]}}}


def faction(names=None, faction_id=None):
    result = {'names': names or {'enUS': 'Example Faction'},
              'sources': [{'type': 'wowhead-npc-tooltip',
                           'url': 'https://nether.wowhead.com/forever/tooltip/npc/123456'}]}
    if faction_id is not None:
        result['factionID'] = faction_id
    return result


class GenericNpcFactionCollectorTests(unittest.TestCase):
    def setUp(self):
        temporary = ROOT / '.pipeline-runtime/tmp'
        temporary.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='npc-collector-', dir=temporary)
        self.addCleanup(self.directory.cleanup)
        self.cache = Path(self.directory.name)

    def write_cache(self, value, npc=123456, locale='', crlf=False):
        suffix = '.' + locale if locale else ''
        path = self.cache / ('%d%s.json' % (npc, suffix))
        text = json.dumps(value, ensure_ascii=False, indent=2)
        if crlf:
            text = text.replace('\n', '\r\n')
        path.write_bytes(text.encode('utf-8'))
        return path

    def provider(self, **options):
        return COLLECTOR.NpcNether(cache_dir=self.cache, **options)

    def test_link_uses_anchor_name_only_and_repeated_same_link_is_consistent(self):
        html = '<table><tr><td>Faction: <a href="/forever/faction=7777">Example &amp; Friends</a>' \
               ' (Revered)</td></tr><tr><td><a href="/forever/faction=7777">Example &amp; Friends</a></td></tr></table>'
        self.assertEqual(COLLECTOR.parse_npc_faction(html),
                         {'name': 'Example & Friends', 'factionID': 7777})

    def test_conflicting_links_fail_instead_of_selecting_an_arbitrary_faction(self):
        for second in ('<a href="/forever/faction=8888">Other Faction</a>',
                       '<a href="/forever/faction=7777">Other Name</a>'):
            with self.subTest(second=second), self.assertRaisesRegex(ValueError, 'conflicting'):
                COLLECTOR.parse_npc_faction('<table><tr><td><a href="/forever/faction=7777">'
                                           'Example Faction</a>%s</td></tr></table>' % second)

    def test_localized_and_unknown_level_rows_supply_only_the_following_affiliation(self):
        for marker in ('等级 25 人型生物（普通）', '等級 25 人型生物（普通）',
                       'Level ?? Humanoid (Elite)', '人型生物（普通）'):
            with self.subTest(marker=marker):
                html = '<table><tr><td>商人</td></tr><tr><td>%s</td></tr>' \
                       '<tr><td>明确组织</td></tr></table>' % marker
                self.assertEqual(COLLECTOR.parse_npc_faction(html), {'name': '明确组织'})

    def test_cache_only_missing_has_status_and_never_requests(self):
        with mock.patch.object(COLLECTOR, 'http_json', side_effect=AssertionError('offline')):
            result = self.provider(cache_only=True)._info(123456)
        self.assertEqual(result['collectionStatus'], 'missing')
        self.assertEqual(result['name'], '')
        self.assertTrue(any(row['code'] == 'cache_only_unavailable' for row in result['diagnostics']))

    def test_corrupt_cache_is_reported_and_repaired_by_valid_request(self):
        path = self.cache / '123456.json'
        path.write_text('{broken', encoding='utf-8')
        with mock.patch.object(COLLECTOR, 'http_json', return_value=payload()) as request:
            result = self.provider()._info(123456)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(result['collectionStatus'], 'ok')
        self.assertEqual(json.loads(path.read_bytes())['name'], 'Example Merchant')
        self.assertTrue(any(row['code'] == 'cache_invalid' for row in result['diagnostics']))
        self.assertTrue(any(row['code'] == 'request_recovered' for row in result['diagnostics']))

    def test_corrupt_cache_offline_returns_error_without_erasing_file(self):
        path = self.cache / '123456.json'
        path.write_bytes(b'{broken')
        with mock.patch.object(COLLECTOR, 'http_json', side_effect=AssertionError('offline')):
            result = self.provider(cache_only=True)._info(123456)
        self.assertEqual(result['collectionStatus'], 'error')
        self.assertEqual(path.read_bytes(), b'{broken')
        self.assertNotIn('faction', result)

    def test_refresh_failure_preserves_previous_name_coordinates_and_evidence(self):
        path = self.write_cache(payload())
        before = path.read_bytes()
        with mock.patch.object(COLLECTOR, 'http_json', return_value=None):
            result = self.provider(refetch=True)._info(123456)
        self.assertEqual(result['collectionStatus'], 'error')
        self.assertEqual(result['name'], 'Example Merchant')
        self.assertEqual(result['coords'], [(50, 12.3, 45.6)])
        self.assertEqual(result['faction']['names']['enUS'], 'Example Faction')
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue(any(row['code'] == 'request_failed' for row in result['diagnostics']))

    def test_expired_cache_offline_is_reported_and_online_refreshes_it(self):
        path = self.write_cache(payload())
        old = time.time() - 10 * 86400
        os.utime(path, (old, old))
        with mock.patch.object(COLLECTOR, 'http_json', side_effect=AssertionError('offline')):
            result = self.provider(cache_only=True, max_age_days=7)._info(123456)
        self.assertEqual(result['collectionStatus'], 'error')
        self.assertEqual(result['name'], 'Example Merchant')
        self.assertTrue(any(row['code'] == 'cache_expired' for row in result['diagnostics']))
        with mock.patch.object(COLLECTOR, 'http_json', return_value=payload('New Merchant')) as request:
            result = self.provider(max_age_days=7)._info(123456)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(result['collectionStatus'], 'ok')
        self.assertEqual(result['name'], 'New Merchant')

    def test_valid_payload_without_affiliation_is_successful_without_neutral_guess(self):
        self.write_cache(payload(affiliation=''))
        result = self.provider(cache_only=True)._info(123456)
        self.assertEqual(result['collectionStatus'], 'ok')
        self.assertNotIn('faction', result)
        self.assertNotIn('side', result)

    def test_tooltip_conflict_keeps_name_and_coordinates(self):
        data = payload()
        data['tooltip'] = '<table><tr><td><a href="/faction=7777">One</a>' \
                          '<a href="/faction=8888">Two</a></td></tr></table>'
        self.write_cache(data)
        result = self.provider(cache_only=True)._info(123456)
        self.assertEqual(result['collectionStatus'], 'error')
        self.assertEqual(result['name'], 'Example Merchant')
        self.assertEqual(result['coords'], [(50, 12.3, 45.6)])
        self.assertNotIn('faction', result)
        self.assertTrue(any(row['code'] == 'affiliation_invalid' for row in result['diagnostics']))

    def test_bad_coordinates_do_not_hide_name_or_affiliation_and_other_points_recover(self):
        data = payload()
        data['map']['coords'] = {'bad': [['nan', 5]], 'good': [[12.3, 45.6]]}
        self.write_cache(data)
        result = self.provider(cache_only=True)._info(123456)
        self.assertEqual(result['collectionStatus'], 'ok')
        self.assertEqual(result['name'], 'Example Merchant')
        self.assertEqual(result['coords'], [(50, 12.3, 45.6)])
        self.assertEqual(result['faction']['names']['enUS'], 'Example Faction')
        self.assertTrue(any(row['code'] == 'coordinates_invalid' for row in result['diagnostics']))

    def test_source_hash_uses_exact_raw_cache_bytes(self):
        path = self.write_cache(payload(), crlf=True)
        result = self.provider(cache_only=True)._info(123456)
        source = result['faction']['sources'][0]
        self.assertEqual(source['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(source['locale'], 'enUS')

    def test_localized_observation_joins_existing_english_cache_without_extra_request(self):
        self.write_cache(payload(faction_id=7777))
        self.write_cache(payload('示例商人', '示例组织', faction_id=7777), locale='zhCN')
        with mock.patch.object(COLLECTOR, 'http_json', side_effect=AssertionError('offline')):
            result = self.provider(cache_only=True, locale='zhCN')._info(123456)
        self.assertEqual(result['collectionStatus'], 'ok')
        self.assertEqual(result['name'], '示例商人')
        self.assertEqual(result['faction']['names'], {'enUS': 'Example Faction', 'zhCN': '示例组织'})
        output = COLLECTOR.build_npc_factions({123456: result})['npcs']['123456']
        self.assertEqual(output['factionID'], 7777)
        self.assertEqual(output['names']['zhCN'], '示例组织')
        self.assertEqual(len(output['sources']), 2)

    def test_localized_conflicting_id_is_reported_without_losing_other_fields(self):
        self.write_cache(payload(faction_id=7777))
        self.write_cache(payload('示例商人', '不同组织', faction_id=8888), locale='zhTW')
        result = self.provider(cache_only=True, locale='zhTW')._info(123456)
        self.assertEqual(result['collectionStatus'], 'error')
        self.assertEqual(result['name'], '示例商人')
        self.assertEqual(result['coords'], [(50, 12.3, 45.6)])
        self.assertNotIn('faction', result)
        self.assertTrue(any(row['code'] == 'affiliation_conflict' for row in result['diagnostics']))

    def test_language_list_merge_keeps_localized_name_missing_from_client_catalog(self):
        info = {123456: {'factions': [faction(), faction({'zhCN': '示例组织'})]}}
        client = {'Example Faction': {'factionID': 7777, 'names': {'enUS': 'Example Faction'}}}
        output = COLLECTOR.build_npc_factions(info, client)['npcs']['123456']
        self.assertEqual(output['names'], {'enUS': 'Example Faction', 'zhCN': '示例组织'})
        self.assertEqual(output['factionID'], 7777)
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            COLLECTOR.merge_npc_faction_evidence([faction(faction_id=7777), faction(faction_id=8888)])

    def test_missing_english_or_sources_is_an_explicit_diagnostic(self):
        messages = []
        result = COLLECTOR.build_npc_factions({123456: {'faction': faction({'zhCN': '示例组织'})}},
                                             diagnostics=messages)
        self.assertEqual(result['npcs'], {})
        self.assertEqual(messages[0]['code'], 'affiliation_missing_english')
        result = COLLECTOR.build_npc_factions({123456: {'faction': {'names': {'enUS': 'Test'}}}})
        self.assertEqual(result['npcs'], {})
        self.assertEqual(result['diagnostics'][0]['code'], 'affiliation_missing_evidence')

    def test_json_replay_keeps_fields_and_validates_affiliation_independently(self):
        path = self.cache / 'replay.json'
        path.write_text(json.dumps({'123456': {'name': 'Example Merchant', 'coords': [[50, 12.3, 45.6]],
                                               'faction': faction(faction_id=7777)}}), encoding='utf-8')
        result = COLLECTOR.NpcJson(path).npc_info([123456])[123456]
        self.assertEqual(result['collectionStatus'], 'ok')
        self.assertEqual(result['coords'], [(50, 12.3, 45.6)])
        self.assertEqual(result['faction']['factionID'], 7777)
        saved = json.loads(path.read_bytes())
        saved['123456']['faction']['side'] = 'N'
        path.write_text(json.dumps(saved), encoding='utf-8')
        result = COLLECTOR.NpcJson(path).npc_info([123456])[123456]
        self.assertEqual(result['collectionStatus'], 'error')
        self.assertEqual(result['name'], 'Example Merchant')
        self.assertEqual(result['coords'], [(50, 12.3, 45.6)])
        self.assertNotIn('faction', result)

    def test_standalone_affiliation_json_can_be_replayed_as_a_provider(self):
        path = self.cache / 'factions.json'
        data = {'schemaVersion': 1, 'npcs': {'123456': faction(faction_id=7777)}}
        path.write_text(json.dumps(data), encoding='utf-8-sig')
        info = COLLECTOR.NpcJson(path).npc_info([123456, 999999])
        self.assertEqual(info[123456]['collectionStatus'], 'ok')
        self.assertEqual(info[999999]['collectionStatus'], 'missing')
        self.assertEqual(COLLECTOR.build_npc_factions(info), data)

    def test_invalid_cache_options_and_cache_write_failure_are_reported(self):
        for options in ({'max_age_days': -1}, {'max_age_days': float('nan')},
                        {'refetch': True, 'cache_only': True}, {'locale': 'unknown'}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.provider(**options)
        with mock.patch.object(COLLECTOR, 'http_json', return_value=payload()), \
                mock.patch.object(COLLECTOR, 'save', side_effect=OSError('read-only cache')):
            result = self.provider()._info(123456)
        self.assertEqual(result['name'], 'Example Merchant')
        self.assertEqual(result['collectionStatus'], 'error')
        self.assertTrue(any(row['code'] == 'cache_write_failed' for row in result['diagnostics']))

    def test_cli_reports_conflict_before_publishing_any_csv_or_json(self):
        csv_path, npc_path, faction_path = [self.cache / name for name in
                                            ('vendors.csv', 'npcs.csv', 'factions.json')]
        soldby = mock.Mock()
        soldby.sold_by.return_value = {9: [{'npc': 123456, 'zone': 50, 'side': None,
                                           'name': 'Example Merchant', 'cost': 10,
                                           'currency_kind': None, 'currency_id': None,
                                           'currency_amount': None, 'stock': -1}]}
        npc_provider = mock.Mock()
        npc_provider.npc_info.return_value = {123456: {
            'name': 'Example Merchant', 'coords': [(50, 12.3, 45.6)], 'collectionStatus': 'error',
            'diagnostics': [{'code': 'affiliation_invalid', 'message': 'conflicting explicit links',
                             'severity': 'error'}]}}
        argv = ['gen_vendors.py', '--ids', '9', '--npc-cache-only', '--npc-max-age', '7',
                '--csv-out', str(csv_path), '--npcs-out', str(npc_path),
                '--npc-factions-out', str(faction_path)]
        with mock.patch.object(COLLECTOR.sys, 'argv', argv), \
                mock.patch.object(COLLECTOR, 'make_soldby_provider', return_value=soldby), \
                mock.patch.object(COLLECTOR, 'make_npc_provider', return_value=npc_provider), \
                mock.patch.object(COLLECTOR, 'load_area_map', return_value={50: 1250}), \
                mock.patch.object(COLLECTOR, 'log') as log:
            with self.assertRaisesRegex(SystemExit, 'conflicts'):
                COLLECTOR.main()
        self.assertFalse(any(path.exists() for path in (csv_path, npc_path, faction_path)))
        self.assertTrue(any('affiliation_invalid' in str(call) for call in log.call_args_list))


if __name__ == '__main__':
    unittest.main()
