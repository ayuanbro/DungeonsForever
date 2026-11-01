"""Offline scheduling, byte preservation and deferred experiment contracts."""
import base64
from concurrent.futures import ThreadPoolExecutor
import datetime
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import zipfile

from data_pipeline.professions import fetch as collection
from data_pipeline.professions import compare_transport as comparison
from data_pipeline.professions.browser_transport import BrowserTransport
from data_pipeline.professions.model import SourceError
from data_pipeline.professions.tests import test_source_pipeline as fixtures


URL = 'https://www.wowhead.com/forever/spell=1000'


class ImprovedTransportContracts(unittest.TestCase):
    def test_retry_after_case_seconds_dates_and_invalid_values(self):
        self.assertEqual(collection.retry_delay({'retry-after': '120'}, 0), 120)
        self.assertEqual(collection.retry_delay({'RETRY-AFTER': '3600'}, 0), 3600)
        timestamp = datetime.datetime(2026, 10, 29, tzinfo=datetime.timezone.utc).timestamp()
        self.assertEqual(collection.retry_delay({'Retry-After': 'Thu, 29 Oct 2026 00:02:00 GMT'}, 0, timestamp), 120)
        self.assertEqual(collection.retry_delay({'Retry-After': 'Wed, 28 Oct 2026 00:00:00 GMT'}, 0, timestamp), 0)
        for value in ('invalid', '-5', 'nan', '1.5', ''):
            self.assertEqual(collection.retry_delay({'retry-after': value}, 2), 4)

    def test_recovery_has_a_finite_budget_and_retains_browser_session(self):
        browser = MagicMock()
        browser.get.return_value = (403, b'denied', {}, URL)
        with patch.object(collection.time, 'sleep') as sleep:
            with collection.WowheadTransport(interval=0, mode='browser', browser_factory=lambda: browser,
                                            recoveries=2, cooldown=120) as transport:
                for _ in range(4):
                    self.assertEqual(transport.get(URL)[0], 403)
                with self.assertRaises(collection.HostCircuitOpen):
                    transport.get(URL)
                self.assertEqual(transport.metrics['recoveries'], 2)
                self.assertEqual(browser.get.call_count, 4)
                self.assertEqual(sleep.call_args_list, [unittest.mock.call(120), unittest.mock.call(120)])
            browser.close.assert_called_once()

    def test_429_wait_is_shared_with_following_entity_after_last_attempt(self):
        clock = [100.0]
        def sleep(seconds):
            clock[0] += seconds
        for status in (429, 403):
            clock[0] = 100.0
            browser = MagicMock()
            browser.get.side_effect = [(status, b'rate limited', {'retry-after': '120'}, URL), (200, b'ok', {}, URL)]
            with patch.object(collection.time, 'monotonic', side_effect=lambda: clock[0]), patch.object(collection.time, 'sleep', side_effect=sleep):
                with collection.WowheadTransport(interval=0, mode='browser', browser_factory=lambda: browser) as transport:
                    transport.get(URL, retries=1)
                    transport.get(URL, retries=1)
            self.assertGreaterEqual(clock[0], 220)

    def test_interactive_challenge_stops_automatic_recovery(self):
        browser = MagicMock()
        browser.get.return_value = (202, b'<div class="g-recaptcha">', {}, URL)
        with collection.WowheadTransport(interval=0, mode='browser', browser_factory=lambda: browser, recoveries=2) as transport:
            self.assertEqual(transport.get(URL)[0], 202)
            with self.assertRaises(collection.HostCircuitOpen):
                transport.get(URL)
            self.assertEqual(browser.get.call_count, 1)

    def test_light_fetch_preserves_bytes_and_403_does_not_navigate_again(self):
        owner = BrowserTransport(request_mode='fetch')
        body = b'\x00\xff<html>\xe4\xb8\xad</html>'
        owner._page = SimpleNamespace(url=URL, evaluate=MagicMock(return_value={
            'status': 200, 'body': base64.b64encode(body).decode(), 'headers': {}, 'url': URL}))
        try:
            self.assertEqual(owner._fetch_owned(URL)[1], body)
            owner._page.evaluate.return_value.update(status=403)
            self.assertEqual(owner._fetch_owned(URL)[0], 403)
            owner._page.evaluate.return_value.update(status=202)
            self.assertIsNone(owner._fetch_owned(URL))
            with self.assertRaises(SourceError):
                owner._fetch_owned('https://example.com/forever/spell=1000')
        finally:
            owner._page = None
            owner.close()

    def test_fetch_validation_falls_back_to_native_navigation_once(self):
        factory, events, _ = fixtures.BrowserOwnerContracts().browser_fixture({URL: [(200, b'complete', URL)]})
        with BrowserTransport(factory=factory, request_mode='fetch') as owner:
            owner.get(URL)  # bootstrap
            with patch.object(owner, '_fetch_owned', return_value=None) as light:
                self.assertEqual(owner.get(URL)[1], b'complete')
                light.assert_called_once()
            self.assertEqual(owner.metrics['navigationFallbacks'], 1)
        self.assertEqual(sum(name == 'goto:commit' for name, _ in events), 2)

    def test_light_assets_preserve_validation_and_document_resources(self):
        factory, _, _ = fixtures.BrowserOwnerContracts().browser_fixture({URL: [(200, b'complete', URL)]})
        context = factory().start().chromium.launch().new_context()
        context.route = MagicMock()
        with BrowserTransport(factory=factory, assets='light') as owner:
            owner.get(URL)
            handler = context.route.call_args.args[1]
            for kind in ('image', 'font', 'media', 'script', 'document', 'stylesheet', 'fetch', 'xhr', 'other'):
                route = MagicMock(); route.request.resource_type = kind
                handler(route)
                self.assertEqual(route.abort.called, kind in ('image', 'font', 'media'))
                self.assertEqual(route.continue_.called, kind not in ('image', 'font', 'media'))

    def test_crashed_browser_restarts_but_healthy_session_stays(self):
        factory, _, _ = fixtures.BrowserOwnerContracts().browser_fixture({URL: [(200, b'complete', URL)]})
        with BrowserTransport(factory=factory) as owner:
            owner.get(URL)
            owner._browser.is_connected = lambda: True
            owner.get(URL)
            self.assertEqual(owner.metrics['browserRestarts'], 0)
            owner._browser.is_connected = lambda: False
            owner.get(URL)
            self.assertEqual(owner.metrics['browserRestarts'], 1)

    def test_identity_checks_report_mismatch_without_modifying_browser_attributes(self):
        owner = BrowserTransport()
        owner._browser = SimpleNamespace(version='156.0.8078.4')
        owner._page = SimpleNamespace(evaluate=MagicMock(return_value={
            'userAgent': 'Chrome/155.0.1.0', 'platform': 'Linux x86_64', 'languages': ['en-US'],
            'brands': [{'brand': 'Chromium', 'version': '155'}]}))
        try:
            owner._identity_owned()
            self.assertFalse(owner.identity['uaVersionMatches'])
            self.assertFalse(owner.identity['brandVersionMatches'])
            self.assertTrue(owner.identity['platformMatchesLinux'])
            self.assertEqual(owner._page.evaluate.call_count, 1)
        finally:
            owner._page = owner._browser = None
            owner.close()

    def test_bounded_queue_parses_each_new_entity_once_and_does_not_serialize_parsed_trees(self):
        outstanding, peaks = [0], []
        class TrackedPool(ThreadPoolExecutor):
            def submit(self, fn, *args, **kwargs):
                outstanding[0] += 1; peaks.append(outstanding[0])
                future = super().submit(fn, *args, **kwargs)
                original = future.result
                consumed = [False]
                def result(*a, **k):
                    value = original(*a, **k)
                    if not consumed[0]:
                        outstanding[0] -= 1; consumed[0] = True
                    return value
                future.result = result
                return future
        with fixtures.temporary_directory() as temp:
            raw = Path(temp) / 'raw'; raw.mkdir(); fixtures.snapshot(raw, with_web=False)
            with patch.object(collection, 'latest', return_value=fixtures.BUILD), \
                 patch.object(collection, 'WowheadTransport') as cls, \
                 patch.object(collection, 'parse_page', wraps=collection.parse_page) as parse, \
                 patch.object(collection.concurrent.futures, 'ThreadPoolExecutor', TrackedPool):
                transport = cls.return_value.__enter__.return_value
                transport.get.side_effect = fixtures.RefreshRunContracts.page_response
                collection.fetch(raw, resume=True, refresh_web=True, workers=2, log=lambda *a, **k: None)
                self.assertEqual(parse.call_count, transport.get.call_count)
            manifest = json.loads((raw / 'manifest.json').read_text())
            self.assertTrue(manifest['webRun']['requestCoverageComplete'])
            self.assertLessEqual(max(peaks), 2)
            self.assertEqual(outstanding[0], 0)
            self.assertNotIn('_parsed', json.dumps(manifest))

    def completed_fixture(self, root):
        raw, proc = root / 'raw', root / 'proc'
        raw.mkdir(); proc.mkdir()
        records = [{'key': f'web:{kind}:{n}', 'webRunID': 'run', 'attempted': True, 'status': status}
                   for n, (kind, status) in enumerate([('spell', 'verified'), ('item', 'sourceMissing'), ('quest', 'parseError'), ('npc', 'verified')], 1)]
        manifest = {'fetchComplete': True, 'responses': records, 'webRun': {'id': 'run', 'requestCoverageComplete': True,
            'targets': [r['key'] for r in records], 'targetCount': len(records)}}
        (raw / 'manifest.json').write_text(json.dumps(manifest))
        with zipfile.ZipFile(raw.with_suffix('.zip'), 'w') as package:
            package.write(raw / 'manifest.json', 'manifest.json')
        return raw, proc, manifest

    def test_comparison_gate_blocks_partial_active_process_and_unpublished_archive(self):
        with fixtures.temporary_directory() as temp:
            raw, proc, manifest = self.completed_fixture(Path(temp))
            self.assertEqual(comparison.completion_gate(raw, proc), manifest)
            partial = raw.with_name('raw.partial'); partial.mkdir()
            with self.assertRaisesRegex(SourceError, 'partial'):
                comparison.completion_gate(raw, proc)
            partial.rmdir()
            process = proc / '999999999'; process.mkdir()
            (process / 'cmdline').write_bytes(b'python\0-m\0data_pipeline.professions\0fetch\0')
            with self.assertRaisesRegex(SourceError, 'running'):
                comparison.completion_gate(raw, proc)
            (process / 'cmdline').write_bytes(b'other')
            raw.with_suffix('.zip').unlink()
            with self.assertRaisesRegex(SourceError, 'archive'):
                comparison.completion_gate(raw, proc)

    def test_comparison_does_not_start_network_before_gate(self):
        with patch.object(comparison, 'completion_gate', side_effect=SourceError('collection active')), \
             patch.object(comparison, 'latest') as network:
            with self.assertRaises(SourceError):
                comparison.compare(Path('raw'), Path('new-out'))
            network.assert_not_called()

    def test_sample_is_deterministic_and_covers_types_and_failure_states(self):
        with fixtures.temporary_directory() as temp:
            _, _, manifest = self.completed_fixture(Path(temp))
            sample = comparison.select_sample(manifest, 4)
            self.assertEqual(sample, comparison.select_sample(manifest, 4))
            self.assertEqual({r['key'].split(':')[1] for r in sample}, {'spell', 'item', 'quest', 'npc'})
            self.assertIn('sourceMissing', {r['status'] for r in sample})

    def test_comparison_reports_all_arms_and_stops_on_refusal_without_switching_identity(self):
        class Browser:
            refused = False
            calls = 0
            def __init__(self, **kwargs):
                self.metrics = {'requests': 0, 'encodedBytes': 0}
                self.identity = {'uaVersionMatches': True}
            def get(self, url):
                Browser.calls += 1; self.metrics['requests'] += 1
                return (403, b'denied', {}, url) if Browser.refused else fixtures.RefreshRunContracts.page_response(url)
            def close(self):
                pass
        with fixtures.temporary_directory() as temp:
            root = Path(temp)
            raw, _, manifest = self.completed_fixture(root)
            manifest.update(build=fixtures.BUILD['version'], buildInfo=fixtures.BUILD)
            for row in manifest['responses']:
                _, kind, identity = row['key'].split(':')
                row['url'] = f'https://www.wowhead.com/forever/{kind}={identity}'
            with patch.object(comparison, 'completion_gate', return_value=manifest), \
                 patch.object(comparison, 'latest', return_value=fixtures.BUILD), \
                 patch.object(comparison, 'BrowserTransport', Browser), \
                 patch.object(collection.WowheadTransport, 'pace'):
                report = comparison.compare(raw, root / 'experiment', limit=4, rounds=2)
                self.assertTrue(report['complete'])
                self.assertTrue(report['factsEqual'])
                self.assertEqual(len(report['results']), 6)
                self.assertEqual(Browser.calls, 48)
                self.assertTrue(all(len(rows) == 12 for rows in report['observations'].values()))
                Browser.refused = True; Browser.calls = 0
                with self.assertRaisesRegex(SourceError, 'stopped'):
                    comparison.compare(raw, root / 'failed-experiment', limit=4, rounds=1)
                failed = json.loads((root / 'failed-experiment/report.json').read_text())
                self.assertFalse(failed['complete'])
                self.assertEqual(Browser.calls, 1)
                self.assertEqual(failed['interruptedNetwork']['requests'], 1)


if __name__ == '__main__':
    unittest.main()
