"""Hash-bound source evidence survives a Windows Git checkout unchanged."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path('df-data-pipeline/_temp')
INPUTS = SCRIPTS / '_fc/inputs'
MAINTENANCE = SCRIPTS / '_fc/maintenance'
REBASE = MAINTENANCE / 'source/rebase-2-70450'
# Original source-model fingerprints recorded by the reviewed 70450 migration.
MODEL_HASHES = {
    'previous-input-model.json': '5b87711d0d9614d199f8aa9a3d3920bdc14dfa6ce96e9c4260bf08766ce0f009',
    'incoming-input-model.json': 'f84df99f6ac06dc62d317aa9c844d5f8a7f4af71c3d990a43c8c3a912586912f',
}


def source_expectations(root=ROOT):
    """Read existing evidence identities; never derive expected hashes from files."""
    expected = {}

    def add(path, digest, size=None):
        if path in expected and expected[path][0] != digest:
            raise AssertionError('conflicting source identity: %s' % path)
        expected[path] = (digest, size)

    manifest = json.loads((root / INPUTS / 'manifest.json').read_bytes())
    for name, row in manifest['files'].items():
        add(INPUTS / name, row['sha256'], row.get('bytes'))
        if row.get('evidenceFile'):
            add(INPUTS / row['evidenceFile'], row['evidenceSha256'])
    affiliations = json.loads((root / INPUTS / 'vendors/npc-factions.json').read_bytes())
    bundle = INPUTS / 'vendors' / affiliations['sourceBundle']['directory']
    add(bundle / 'manifest.json', affiliations['sourceBundle']['manifestSHA256'])
    evidence = json.loads((root / bundle / 'manifest.json').read_bytes())
    for name, row in evidence['files'].items():
        add(bundle / name, row['sha256'], row['bytes'])
    maintenance = json.loads((root / MAINTENANCE / 'professions.json').read_bytes())
    locale_audit = json.loads((root / MAINTENANCE / 'locales-audit-70450-v2.json').read_bytes())
    add(MAINTENANCE / 'locales.json', locale_audit['afterMaintenanceSHA256'])
    for row in maintenance['supplemental_catalog_sources'].values():
        add(MAINTENANCE / row['source_file'], row['source_sha256'])
    rebase = maintenance['provenance']['rebase']
    for name, digest in rebase['new_normalized_sources'].items():
        add(REBASE / 'normalized' / name, digest)
    area_hash = rebase['support_inputs']['_wago_AreaTable_zh.csv']
    add(SCRIPTS / '_wago_AreaTable_zh.csv', area_hash)
    add(REBASE / 'normalized/_wago_AreaTable_zh.csv', area_hash)
    for name, digest in MODEL_HASHES.items():
        add(REBASE / name, digest)
    return expected


class FrozenInputBytesTests(unittest.TestCase):
    def assert_source_hashes(self, root, expected):
        for relative, (digest, size) in expected.items():
            with self.subTest(path=relative.as_posix()):
                content = (root / relative).read_bytes()
                self.assertEqual(hashlib.sha256(content).hexdigest(), digest)
                if size is not None:
                    self.assertEqual(len(content), size)

    def test_declared_source_hashes_match_original_bytes(self):
        self.assert_source_hashes(ROOT, source_expectations())

    @unittest.skipUnless(shutil.which('git'), 'requires Git')
    def test_autocrlf_checkout_preserves_frozen_source_hashes(self):
        expected = source_expectations()
        temporary = ROOT / '.pipeline-runtime/tmp'
        temporary.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='frozen-checkout-', dir=temporary) as name:
            repository = Path(name)
            for relative in [Path('.gitattributes'), *expected]:
                target = repository / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)

            def git(*args):
                result = subprocess.run(['git', *args], cwd=repository,
                                        capture_output=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))

            git('-c', 'init.defaultBranch=frozen-test', 'init', '--quiet')
            git('config', 'core.autocrlf', 'true')
            git('config', 'core.safecrlf', 'false')
            git('add', '--', '.gitattributes', 'df-data-pipeline')
            checkout = repository / 'checkout'
            checkout.mkdir()
            git('checkout-index', '--all', '--force', '--prefix=' + checkout.as_posix() + '/')
            self.assert_source_hashes(checkout, expected)


if __name__ == '__main__':
    unittest.main()
