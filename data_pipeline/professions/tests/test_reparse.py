import json
from pathlib import Path
import unittest
from unittest.mock import patch

from data_pipeline.professions.model import listview_json, parse_page
from data_pipeline.professions.fetch import fetch
from data_pipeline.professions.reparse import reparse
from data_pipeline.professions.tests import test_source_pipeline as fixtures
from data_pipeline.professions.tests.test_source_pipeline import snapshot, temporary_directory, BUILD


class ReparseContracts(unittest.TestCase):
    def test_bare_keys_preserve_strings_and_reject_executable_values(self):
        self.assertEqual(listview_json('[{"name":"{modes: string}",modes:{"mode":[0]}}]'),
                         [{'name': '{modes: string}', 'modes': {'mode': [0]}}])
        self.assertEqual(listview_json("[{pctstack:'{1: 50.8,2: 49.2}'}]"),
                         [{'pctstack': '{1: 50.8,2: 49.2}'}])
        with self.assertRaises(ValueError):
            listview_json('[{modes:runCode()}]')

    def test_reparse_is_offline_and_retains_original_manifest(self):
        with temporary_directory() as temp:
            raw = Path(temp); manifest = snapshot(raw)
            manifest['webRun'] = {'id': 'current', 'mode': 'acquire', 'targets': ['web:spell:1000']}
            for record in manifest['responses']:
                if record['key'] == 'web:spell:1000':
                    record.update(status='parseError', error='old parser', webRunID='current', attempted=True)
            path = raw / 'manifest.json'
            path.write_text(json.dumps(manifest))
            before = path.read_bytes()
            with patch('socket.socket.connect', side_effect=AssertionError('offline only')):
                result = reparse(raw, raw / 'audit.json')
            self.assertEqual(result['changes'][0]['after'], 'verified')
            self.assertEqual(next(raw.glob('manifest.before-reparse.*.json')).read_bytes(), before)

    def test_acquire_resume_requests_inherited_old_run_records(self):
        with temporary_directory() as temp:
            raw = Path(temp) / 'raw'; work = Path(temp) / 'raw.partial'; work.mkdir(); manifest = snapshot(work)
            manifest.update(fetchComplete=False, webRun={'id': 'current', 'mode': 'acquire',
                'requestCoverageComplete': False, 'targets': ['web:spell:1000', 'web:item:2000']})
            for record in manifest['responses']:
                if record['key'].startswith('web:'):
                    record.update(webRunID='old', attempted=True)
            (work / 'manifest.json').write_text(json.dumps(manifest))
            with patch('data_pipeline.professions.fetch.latest', return_value=BUILD), \
                 patch('data_pipeline.professions.fetch.WowheadTransport') as cls:
                transport = cls.return_value.__enter__.return_value
                transport.get.side_effect = fixtures.RefreshRunContracts.page_response
                fetch(raw, resume=True, log=lambda *a, **k: None)
            final = json.loads((raw / 'manifest.json').read_text())
            self.assertTrue(final['requestCoverageComplete'])
            self.assertTrue(all(r.get('webRunID') == 'current' for r in final['responses'] if r['key'].startswith('web:')))
