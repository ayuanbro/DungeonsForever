import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from data_pipeline.professions.fetch import accepted_reuse, fetch, update_web_run
from data_pipeline.professions.model import SourceError, write_json
from data_pipeline.professions.reuse import reuse_verified
from data_pipeline.professions.tests import test_source_pipeline as fixtures


class VerifiedReuseContracts(unittest.TestCase):
    def fixture(self, raw):
        manifest = copy.deepcopy(fixtures.snapshot(raw))
        manifest['webRun'] = {'id': 'current', 'mode': 'acquire',
            'targets': ['web:spell:1000', 'web:item:2000', 'web:spell:1001']}
        for record in manifest['responses']:
            if record['key'].startswith('web:'):
                record.update(webRunID='old', attempted=True, fetchedAt='2026-10-29T00:00:00+00:00')
            if record['key'] == 'web:item:2000':
                record['status'] = 'sourceMissing'
        manifest['responses'].append({'key': 'web:spell:1001', 'status': 'sourceBlocked',
            'webRunID': 'current', 'attempted': True, 'httpStatus': 403})
        write_json(raw / 'manifest.json', manifest)
        return manifest

    def test_offline_reuse_preserves_origin_and_separates_actual_requests(self):
        with fixtures.temporary_directory() as temp:
            raw = Path(temp); before = self.fixture(raw)
            with patch('socket.socket.connect', side_effect=AssertionError('must stay offline')):
                report = reuse_verified(raw, raw / 'reuse.json')
            after = json.loads((raw / 'manifest.json').read_text())
            self.assertEqual(after['responses'], before['responses'])
            counts = report['summary']
            self.assertEqual((counts['newlyRequested'], counts['reused'], counts['uncovered']), (1, 1, 1))
            self.assertEqual(counts['notAttempted'], 2)
            self.assertFalse(counts['requestCoverageComplete'])
            self.assertEqual(report['sourceGapCounts'], {'sourceBlocked': 1, 'sourceMissing': 1})
            self.assertEqual(len(report['notNewlyRequestedAndNotReused']), 1)

    def test_changed_build_or_response_cannot_reuse_stale_acceptance(self):
        with fixtures.temporary_directory() as temp:
            raw = Path(temp); self.fixture(raw); reuse_verified(raw, raw / 'reuse.json')
            manifest = json.loads((raw / 'manifest.json').read_text())
            record = next(r for r in manifest['responses'] if r['key'] == 'web:spell:1000')
            self.assertTrue(accepted_reuse(manifest, record))
            changed = copy.deepcopy(record); changed['sha256'] = '0' * 64
            self.assertFalse(accepted_reuse(manifest, changed))
            manifest['buildInfo']['build_config'] = 'b' * 32
            self.assertFalse(accepted_reuse(manifest, record))

    def test_mixed_build_or_corrupt_raw_does_not_publish_reuse(self):
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), fixtures.temporary_directory() as temp:
                raw = Path(temp); manifest = self.fixture(raw)
                if corrupt:
                    record = next(r for r in manifest['responses'] if r['key'] == 'web:spell:1000')
                    (raw / record['path']).write_bytes(b'bad')
                else:
                    manifest['latestAfter']['version'] = '1.60.1.12345'
                    write_json(raw / 'manifest.json', manifest)
                before = (raw / 'manifest.json').read_bytes()
                with self.assertRaises(SourceError):
                    reuse_verified(raw, raw / 'reuse.json')
                self.assertEqual((raw / 'manifest.json').read_bytes(), before)

    def test_all_targets_can_be_covered_by_requests_and_reuse_without_faking_new_requests(self):
        with fixtures.temporary_directory() as temp:
            raw = Path(temp); self.fixture(raw); reuse_verified(raw, raw / 'reuse.json')
            manifest = json.loads((raw / 'manifest.json').read_text())
            records = {r['key']: r for r in manifest['responses']}
            targets = {('spell', 1000), ('spell', 1001)}
            update_web_run(manifest, targets, records)
            self.assertTrue(manifest['acquisitionCoverageComplete'])
            self.assertFalse(manifest['requestCoverageComplete'])
            self.assertEqual(manifest['webRun']['newlyRequested'], 1)
            self.assertEqual(manifest['webRun']['reused'], 1)

    def test_closed_incomplete_acquire_resume_skips_registered_reuse(self):
        with fixtures.temporary_directory() as temp:
            raw = Path(temp) / 'raw'; raw.mkdir(); self.fixture(raw)
            reuse_verified(raw, Path(temp) / 'reuse.json')
            with patch('data_pipeline.professions.fetch.latest', return_value=fixtures.BUILD), \
                 patch('data_pipeline.professions.fetch.WowheadTransport') as cls:
                transport = cls.return_value.__enter__.return_value
                transport.get.side_effect = fixtures.RefreshRunContracts.page_response
                fetch(raw, resume=True, log=lambda *a, **k: None)
                urls = [call.args[0] for call in transport.get.call_args_list]
            self.assertNotIn('https://www.wowhead.com/forever/spell=1000', urls)
            self.assertIn('https://www.wowhead.com/forever/item=2000', urls)
            final = json.loads((raw / 'manifest.json').read_text())
            self.assertEqual(final['webRun']['id'], 'current')
            self.assertEqual(final['webRun']['reused'], 1)
            self.assertTrue(final['acquisitionCoverageComplete'])
