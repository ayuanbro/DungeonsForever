"""Installation previews contain staged data while the checkout stays unchanged."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'df-data-pipeline/_temp'))
import fc_package as package
import fc_pipeline as pipeline
import fc_pipeline_common as common


class PreviewPackageTests(unittest.TestCase):
    def setUp(self):
        directory = ROOT / '.pipeline-runtime/tmp'
        directory.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='package-中文 space-', dir=directory)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.addCleanup(patch.stopall)
        patch.object(common, 'REPO', self.root).start()
        patch.object(package, 'REPO', self.root).start()
        self.write('DungeonsForever.toc', b'## Version: 1.8.31\nLibs/embeds.xml\nCore/Data/Data_Professions.lua\nCore/Data/enUS/Data_Professions.lua [AllowLoadTextLocale enUS]\n')
        self.write('Libs/embeds.xml', b'<Ui><Script file="helper.lua"/></Ui>')
        self.write('Libs/helper.lua', b'local _,ns=...\nns.Helper=true\n')
        self.data = self.write('Core/Data/Data_Professions.lua', b'local _,ns=...\nns.Build="old"\n')
        self.write('Core/Data/enUS/Data_Professions.lua', b'local _,ns=...\nns.Locale="English"\n')
        self.write('LICENSE', b'license')
        self.write('Media/icon.tga', b'asset')
        self.write('Media/debug.log', b'not a runtime asset')
        self.write('scripts/unsafe.ps1', b'not a runtime dependency')
        self.zip = self.root / 'dist/preview.zip'

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_staged_data_goes_into_install_zip_without_touching_checkout(self):
        old = self.data.read_bytes(), self.data.stat().st_mtime_ns
        candidate = b'local _,ns=...\nns.Build="70450"\n'
        report = package.build_install_zip(self.zip, {self.data: candidate})
        self.assertEqual((self.data.read_bytes(), self.data.stat().st_mtime_ns), old)
        self.assertFalse(report['published'])
        with zipfile.ZipFile(self.zip) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(archive.read('DungeonsForever/Core/Data/Data_Professions.lua'), candidate)
            self.assertIn('DungeonsForever/Libs/helper.lua', archive.namelist())
            self.assertIn('DungeonsForever/Core/Data/enUS/Data_Professions.lua', archive.namelist())
            self.assertIn('DungeonsForever/Media/icon.tga', archive.namelist())
            self.assertFalse(any('scripts/' in p or p.endswith('.log') for p in archive.namelist()))
        repeated = self.root / 'dist/second.zip'
        package.build_install_zip(repeated, {self.data: candidate})
        self.assertEqual(self.zip.read_bytes(), repeated.read_bytes())

    def test_existing_archive_is_never_overwritten(self):
        self.zip.parent.mkdir()
        self.zip.write_bytes(b'keep this archive')
        with self.assertRaisesRegex(ValueError, 'new .zip'):
            package.build_install_zip(self.zip, {})
        self.assertEqual(self.zip.read_bytes(), b'keep this archive')

    def test_runtime_change_before_packaging_blocks_archive(self):
        expected = {self.data: common.sha(self.data.read_bytes())}
        self.data.write_bytes(b'changed by another writer')
        with self.assertRaisesRegex(ValueError, 'changed before packaging'):
            package.build_install_zip(self.zip, {}, expected)
        self.assertFalse(self.zip.exists())

    def test_runtime_change_during_packaging_leaves_no_archive(self):
        real = package.fingerprint
        def changed(path):
            if path == self.data:
                return common.sha(b'external change')
            return real(path)
        with patch.object(package, 'fingerprint', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed during packaging'):
                package.build_install_zip(self.zip, {})
        self.assertFalse(self.zip.exists())
        self.assertEqual(list(self.zip.parent.glob('.df-preview-*')), [])

    def test_csv_changed_during_compression_leaves_no_install_archive(self):
        source = self.write('client.csv', b'original CSV')
        expected = {source: common.sha(source.read_bytes())}
        original = zipfile.ZipFile.writestr
        def changed(archive, *args, **kwargs):
            source.write_bytes(b'external replacement CSV')
            return original(archive, *args, **kwargs)
        with patch.object(zipfile.ZipFile, 'writestr', changed):
            with self.assertRaisesRegex(ValueError, 'file changed during update'):
                package.build_install_zip(self.zip, {}, expected)
        self.assertFalse(self.zip.exists())

    def test_manifest_outside_reference_is_rejected(self):
        self.write('Libs/embeds.xml', b'<Ui><Script file="../../outside.lua"/></Ui>')
        with self.assertRaisesRegex(ValueError, 'inside the current repository'):
            package.build_install_zip(self.zip, {})
        self.assertFalse(self.zip.exists())

    def test_non_profession_runtime_overrides_are_rejected(self):
        for name in ('DungeonsForever.toc', 'Libs/helper.lua', 'Libs/embeds.xml', 'LICENSE'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'outside profession data'):
                package.build_install_zip(self.zip, {self.root / name: b'changed'})
        self.assertFalse(self.zip.exists())

    def test_manifest_changed_after_discovery_cannot_mix_dependency_lists(self):
        original = package.runtime_files
        def changed(*args, **kwargs):
            files = original(*args, **kwargs)
            self.write('Libs/embeds.xml', b'<Ui><Script file="different.lua"/></Ui>')
            self.write('Libs/different.lua', b'new dependency')
            return files
        with patch.object(package, 'runtime_files', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed during packaging'):
                package.build_install_zip(self.zip, {})
        self.assertFalse(self.zip.exists())

    def test_current_runtime_files_match_independent_packaging_manifest(self):
        from test_package_prof_prices import runtime_files
        with patch.object(common, 'REPO', ROOT), patch.object(package, 'REPO', ROOT):
            self.assertEqual(set(package.runtime_files()), runtime_files(ROOT))


class ExplicitRemovalTests(unittest.TestCase):
    approval = {'namespace': 'ProfRecipes', 'profession': 'alchemy', 'collection': 'rows',
                'spell': 1251750, 'item': 250952, 'target_build': '1.60.1.70450',
                'approval': 'user selected upstream removal'}

    def test_only_approved_stable_identity_can_leave_the_retention_view(self):
        old = {'ProfRecipes': {'alchemy': {'rows': [[1251750, 250952], [123, 456]]}}}
        saved = copy.deepcopy(old)
        new = {'ProfData': {'build': '1.60.1.70450'}, 'ProfRecipes': {'alchemy': {'rows': []}}}
        report = {}
        view = pipeline.retention_view(old, new, [self.approval], report)
        self.assertEqual(view['ProfRecipes']['alchemy']['rows'], [[123, 456]])
        self.assertTrue(pipeline.missing_records(view, new))
        self.assertEqual(old, saved)
        self.assertEqual(report['approvedRemovals'], [self.approval])

    def test_different_build_or_item_does_not_match_approval(self):
        old = {'ProfRecipes': {'alchemy': {'rows': [[1251750, 250953]]}}}
        new = {'ProfData': {'build': '1.60.1.70450'}, 'ProfRecipes': {'alchemy': {'rows': []}}}
        self.assertEqual(pipeline.retention_view(old, new, [self.approval], {}), old)
        old['ProfRecipes']['alchemy']['rows'] = [[1251750, 250952]]
        new['ProfData']['build'] = '1.60.1.99999'
        self.assertEqual(pipeline.retention_view(old, new, [self.approval], {}), old)

    def test_same_spell_different_item_still_blocks_unapproved_record_loss(self):
        old = {'ProfRecipes': {'alchemy': {'rows': [[100, 20], [100, 21]]}}}
        new = {'ProfRecipes': {'alchemy': {'rows': [[100, 20]]}}}
        self.assertEqual(pipeline.missing_records(old, new), ['/ProfRecipes/alchemy/rows/spell:100/item:21'])

    def test_leveling_threshold_changes_preserve_stable_spell_identity(self):
        old = {'ProfLeveling': {'tailoring': {'steps': [[36, 41, 123, 5], [41, 46, 456, 5]]}}}
        new = {'ProfLeveling': {'tailoring': {'steps': [[40, 45, 123, 5], [45, 50, 456, 5]]}}}
        self.assertEqual(pipeline.missing_records(old, new), [])
        new['ProfLeveling']['tailoring']['steps'].pop()
        self.assertEqual(pipeline.missing_records(old, new), ['/ProfLeveling/tailoring/steps/spell:456'])

    def test_retired_route_fallback_requires_preserved_main_identity_and_resolved_new_guide(self):
        old = {'ProfRecipes': {'enchanting': {'enchants': [['Original Enchant'] + [None] * 12 + [13746]]}},
               'ProfLeveling': {'enchanting': {'steps': [[1, 10, 13746, 9]],
                                               'rinfo': {13746: {'mats': [[11137, 1]]}}}}}
        new = copy.deepcopy(old)
        new['ProfLeveling']['enchanting'].update(steps=[[1, 10, 13815, 9]], rinfo={13815: {'mats': [[11137, 1]]}})
        evidence = {13746: [('enchanting', 'enchants', 'name:Original Enchant')]}
        report = {}
        view = pipeline.retention_view(old, new, [], report, evidence)
        self.assertNotIn(13746, view['ProfLeveling']['enchanting']['rinfo'])
        self.assertEqual(report['retiredRouteFallbacks'][0]['spell'], 13746)
        self.assertIn(13746, pipeline.retention_view(old, new, [], {}, {})['ProfLeveling']['enchanting']['rinfo'])
        new['ProfRecipes']['enchanting']['enchants'][0][13] = None
        self.assertIn(13746, pipeline.retention_view(old, new, [], {}, evidence)['ProfLeveling']['enchanting']['rinfo'])
        new['ProfRecipes']['enchanting']['enchants'] = []
        self.assertIn(13746, pipeline.retention_view(old, new, [], {}, evidence)['ProfLeveling']['enchanting']['rinfo'])

    def test_guide_may_replace_spell_when_its_runtime_fallback_is_retained(self):
        old = {'ProfLeveling': {'enchanting': {'steps': [[218, 225, 13746, 7]],
                                               'rinfo': {13746: {'mats': [[11137, 1]]}}}}}
        new = copy.deepcopy(old)
        new['ProfLeveling']['enchanting']['steps'] = [[218, 225, 13815, 7]]
        new['ProfLeveling']['enchanting']['rinfo'][13815] = {'mats': [[11137, 1]]}
        report = {}
        view = pipeline.retention_view(old, new, [], report)
        self.assertEqual(pipeline.missing_records(view, new), [])
        self.assertEqual(report['updatedGuideSpells'][0]['spell'], 13746)
        del new['ProfLeveling']['enchanting']['rinfo'][13746]
        self.assertTrue(pipeline.missing_records(pipeline.retention_view(old, new, [], {}), new))

    def test_specialization_removal_requires_used_exact_base_recipe_approval(self):
        before = {1251750: {'status': 'pending'}, 123: {'status': 'confirmed'}}
        report = {'approvedRemovals': [self.approval]}
        view = pipeline.shared_retention_view(before, {}, 'ProfSpecializations', report)
        self.assertEqual(view, {123: {'status': 'confirmed'}})
        self.assertEqual(report['approvedSpecializationRemovals'], [1251750])
        self.assertEqual(pipeline.shared_retention_view(before, {}, 'ProfSpecializations', {}), before)
        self.assertEqual(pipeline.shared_retention_view(before, {}, 'ProfItems', report), before)


if __name__ == '__main__':
    unittest.main()
