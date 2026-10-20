"""The migrated legacy originals remain independently verifiable."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'df-data-pipeline/_temp'))
import fc_legacy_audit as audit
import fc_pipeline_common as common


class LegacyCoverageTests(unittest.TestCase):
    def test_all_tracked_legacy_originals_are_hash_preserved(self):
        report = audit.verify(include_cache=False)
        self.assertEqual(report['checked'], 69)
        self.assertEqual(report['skippedCaches'], 180)
        self.assertEqual(report['failures'], [])
        self.assertFalse(report['readsOriginalPackage'])
        self.assertEqual(len(report['excludedRebuildableBytecode']), 9)

    def test_preservation_manifest_cannot_point_outside_package(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.pipeline-runtime/tmp') as temporary:
            path = Path(temporary) / 'manifest.json'
            path.write_text(json.dumps({'sourcePackage': 'old', 'excludedRebuildableBytecode': [],
                'records': [{'source': 'unsafe', 'preservedAt': '../../outside', 'sha256': 'x',
                             'status': 'immutable-versioned-history'}]}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'inside the current repository'):
                audit.verify(path)


if __name__ == '__main__':
    unittest.main()
