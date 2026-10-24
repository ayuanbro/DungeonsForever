"""Profession locale preservation and ownership contracts; no game client writes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "df-data-pipeline/_temp"
sys.path.insert(0, str(TOOLS))
import fc_pipeline_common as common
import fc_locales as locales


NAME = "Data_ProfRecipes.lua"
BASE = '''local _, ns = ...
ns.ProfRecipes = {
    alchemy = {rows = {
        {1001, 2001, 1, "Potions", "基础说明", "背包", true},
    }},
}
-- Comment with "基础说明" must stay unchanged.
'''
EN = 'if GetLocale() ~= "enUS" then return end\n' + BASE.replace('"基础说明"', '"Hand reviewed English"', 1)
TW = 'if GetLocale() ~= "zhTW" then return end\n' + BASE.replace('"基础说明"', '"保留的繁體說明"', 1)
ENCHANT_A = '{"Enchant Test A","短名A","武器","说明A",1,2,3,4,{},{},false,false,{{"paladin","holy","神圣"},{"hunter","pve","射击"}}}'
ENCHANT_B = '{"Enchant Test B","短名B","武器","说明B",1,2,3,4,{},{},false,false,{}}'
ENCHANT_BASE = 'local _,ns=...\nns.ProfRecipes={enchanting={enchants={' + ENCHANT_A + ',' + ENCHANT_B + '}}}\n'


class LocaleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".locale-test-", dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.baseline = self.directory / "baseline"
        self.baseline.mkdir()
        for name, content in [(NAME, BASE), ("enUS/" + NAME, EN), ("zhTW/" + NAME, TW)]:
            path = self.baseline / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        self.maintenance = self.directory / "locales.json"
        self.maintenance.write_text(json.dumps(locales.capture_maintenance(self.baseline), ensure_ascii=False), encoding="utf-8")

    def render(self, text=BASE):
        return locales.render_locales({NAME: text.encode("utf-8")}, self.baseline, self.maintenance)

    def enchant_fixture(self, legacy=False):
        en = ENCHANT_BASE.replace('"神圣"', '"Reviewed Holy"').replace('"射击"', '"Reviewed Hunter"')
        tw = ENCHANT_BASE.replace('"神圣"', '"保留神聖譯文"').replace('"射击"', '"保留射擊譯文"')
        for path, content in [(self.baseline / NAME, ENCHANT_BASE),
                              (self.baseline / "enUS" / NAME, en),
                              (self.baseline / "zhTW" / NAME, tw)]:
            path.write_text(content, encoding="utf-8")
        value = locales.capture_maintenance(self.baseline)
        if legacy:
            source = locales._records(ENCHANT_BASE, 1)
            current = locales._records(ENCHANT_BASE, 2)
            old_by_offset = {token.start: key for key, token in source.items()}
            new = {old_by_offset[current[key].start]: entry for key, entry in value["files"][NAME].items()}
            value = {"schemaVersion": 1, "files": {NAME: new}}
        self.maintenance.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return value

    def test_preserves_reviewed_text_and_identical_traditional_word(self):
        original = {p: p.read_bytes() for p in self.baseline.rglob("*.lua")}
        outputs = self.render()
        self.assertIn(b"Hand reviewed English", outputs["enUS/" + NAME])
        self.assertIn("保留的繁體說明".encode(), outputs["zhTW/" + NAME])
        self.assertIn('"背包"'.encode(), outputs["zhTW/" + NAME])
        self.assertIn('-- Comment with "基础说明"'.encode(), outputs["enUS/" + NAME])
        self.assertEqual(original, {p: p.read_bytes() for p in original})
        self.assertEqual(outputs, self.render())

    def test_recipe_identity_survives_row_insertion_and_reordering(self):
        updated = BASE.replace('{1001,', '{1000, 2000, 1, "Potions", "新配方", "", false},\n        {1001,')
        outputs = self.render(updated)
        lua, ns = common.raw_namespace([(NAME, updated.encode()), ("enUS/" + NAME, outputs["enUS/" + NAME])], "enUS")
        rows = ns.ProfRecipes.alchemy.rows
        self.assertEqual(rows[1][1], 1000)
        self.assertEqual(rows[2][1], 1001)
        self.assertEqual(rows[2][5], "Hand reviewed English")

    def test_trainer_identity_survives_bracket_key_serialization(self):
        base = 'local _,ns=...\nns.ProfTrainers={alchemy={list={{en="Known Trainer",rng="1-75",map=1453,fac="A",zh="训练师",tw="訓練師"}}}}\n'
        name = "Data_ProfTrainers.lua"
        (self.baseline / name).write_text(base, encoding="utf-8")
        for locale in locales.LOCALES:
            (self.baseline / locale / name).write_text(base.replace('zh="训练师"', 'zh="Reviewed trainer"'), encoding="utf-8")
        value = locales.capture_maintenance(self.baseline)
        self.maintenance.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        serialized = base
        for key in ("en", "rng", "map", "fac", "zh", "tw", "alchemy", "list"):
            serialized = serialized.replace(key + "=", '["' + key + '"]=')
        outputs = locales.render_locales({name: serialized.encode()}, self.baseline, self.maintenance)
        self.assertIn(b'Reviewed trainer', outputs["enUS/" + name])

    def test_bis_and_enchant_reordering_keep_translations_with_their_identities(self):
        self.enchant_fixture()
        updated_a = ENCHANT_A.replace('{{"paladin","holy","神圣"},{"hunter","pve","射击"}}',
                                      '{{"priest","shadow","暗影"},{"hunter","pve","射击"},{"paladin","holy","神圣"}}')
        updated = ENCHANT_BASE.replace(ENCHANT_A + ',' + ENCHANT_B, ENCHANT_B + ',' + updated_a)
        outputs = self.render(updated)
        expected = {"enUS": ("Reviewed Holy", "Reviewed Hunter"),
                    "zhTW": ("保留神聖譯文", "保留射擊譯文")}
        for locale, (holy, hunter) in expected.items():
            _, ns = common.raw_namespace([(NAME, updated.encode()), (locale + '/' + NAME, outputs[locale + '/' + NAME])], locale)
            row = ns.ProfRecipes.enchanting.enchants[2]
            self.assertEqual(row[1], "Enchant Test A")
            bis = {(item[1], item[2]): item[3] for _, item in row[13].items()}
            self.assertEqual(bis[("paladin", "holy")], holy)
            self.assertEqual(bis[("hunter", "pve")], hunter)
            self.assertNotEqual(bis[("priest", "shadow")], holy)

    def test_legacy_positional_maintenance_is_migrated_without_writes(self):
        self.enchant_fixture(legacy=True)
        before = self.maintenance.read_bytes()
        updated = ENCHANT_BASE.replace(ENCHANT_A + ',' + ENCHANT_B, ENCHANT_B + ',' + ENCHANT_A)
        outputs = self.render(updated)
        self.assertIn(b'Reviewed Holy', outputs['enUS/' + NAME])
        self.assertEqual(self.maintenance.read_bytes(), before)
        migrated = locales._maintenance(self.maintenance, self.baseline)
        keys = migrated['files'][NAME]
        self.assertTrue(any('/@enchant=Enchant Test A/[13]/@bis=paladin:holy/' in key for key in keys))

    def test_reviewed_history_matches_exact_source_and_unknown_changes_still_fail(self):
        value = json.loads(self.maintenance.read_text(encoding="utf-8"))
        key = next(key for key, entry in value['files'][NAME].items() if entry['source'] == '基础说明')
        entry = value['files'][NAME][key]
        original = dict(entry)
        entry.update(source='新的说明', sourceSHA256=locales._hash('新的说明'),
                     translations={'enUS': 'Reviewed new text', 'zhTW': '審核後新說明'}, history=[original])
        self.maintenance.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        self.assertIn(b'Hand reviewed English', self.render()['enUS/' + NAME])
        self.assertIn(b'Reviewed new text', self.render(BASE.replace('基础说明', '新的说明'))['enUS/' + NAME])
        with self.assertRaises(locales.LocaleError):
            self.render(BASE.replace('基础说明', '未审查的第三版'))

    def test_reviewed_history_hash_is_validated_even_when_not_selected(self):
        value = json.loads(self.maintenance.read_text(encoding="utf-8"))
        entry = next(iter(value['files'][NAME].values()))
        entry['history'] = [{'source': 'old source', 'sourceSHA256': 'invalid',
                             'translations': {'enUS': 'old reviewed translation'}}]
        self.maintenance.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaisesRegex(locales.LocaleError, 'source hash mismatch'):
            self.render()

    def test_duplicate_bis_identity_is_rejected_as_ambiguous(self):
        self.enchant_fixture()
        ambiguous = ENCHANT_BASE.replace('{"hunter","pve","射击"}', '{"paladin","holy","别的原文"}')
        with self.assertRaisesRegex(locales.LocaleError, 'Ambiguous stable locale identity'):
            self.render(ambiguous)

    def test_changed_source_blocks_existing_translation_with_audit(self):
        with self.assertRaises(locales.LocaleError) as caught:
            self.render(BASE.replace("基础说明", "新的说明"))
        failures = caught.exception.invalidated
        self.assertEqual({f["locale"] for f in failures}, {"enUS", "zhTW"})
        self.assertTrue(all("@id=1001" in f["record"] for f in failures))
        self.assertTrue(all(f["previousSource"] == "基础说明" for f in failures))

    def test_maintenance_hash_mismatch_is_an_error(self):
        value = json.loads(self.maintenance.read_text(encoding="utf-8"))
        first = next(iter(value["files"][NAME].values()))
        first["source"] = "changed without hash update"
        self.maintenance.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(locales.LocaleError, "source hash mismatch"):
            self.render()

    def test_language_guards_apply_only_selected_overlay(self):
        outputs = self.render()
        paths = [(NAME, BASE.encode())] + list(outputs.items())
        for locale, expected in [("zhCN", "基础说明"), ("enUS", "Hand reviewed English"), ("zhTW", "保留的繁體說明")]:
            _, ns = common.raw_namespace(paths, locale)
            self.assertEqual(ns.ProfRecipes.alchemy.rows[1][5], expected)

    def test_escaped_and_single_quoted_text_is_valid_lua(self):
        modified = BASE.replace('"基础说明"', "'新\\'配方'", 1).replace("1001", "1002")
        for relative, content in self.render(modified).items():
            _, ns = common.raw_namespace([(NAME, modified.encode()), (relative, content)], relative.split("/")[0])
            self.assertIn("'", ns.ProfRecipes.alchemy.rows[1][5])

    def test_rejects_shared_and_unowned_data(self):
        for name in ("Data_ProfItems.lua", "Data_ProfSpecializations.lua", "Data_ProfMining.lua", "Data_ProfFishingRoutes.lua", "Data_Gear.lua"):
            with self.assertRaisesRegex(locales.LocaleError, "does not own"):
                locales.render_locales({name: b""}, self.baseline, self.maintenance)

    def test_missing_opencc_fails_without_fallback(self):
        with patch("gen_zhtw.require_opencc", side_effect=RuntimeError("missing OpenCC")):
            with self.assertRaisesRegex(locales.LocaleError, "requires OpenCC"):
                self.render()

    def test_cli_dry_run_writes_nothing_and_rejects_outside_output(self):
        output = self.directory / "output"
        command = [sys.executable, str(TOOLS / "gen_enus_data.py"), "--source-root", str(self.baseline),
                   "--output-root", str(output), "--files", NAME, "--maintenance", str(self.maintenance), "--dry-run"]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(output.exists())
        command[command.index(str(output))] = str(ROOT.parent / "outside-locale-output")
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inside the Git checkout", result.stderr)

    def test_current_baseline_replays_all_twelve_files_byte_for_byte(self):
        baseline = ROOT / "Core/Data"
        outputs = locales.render_locales({name: (baseline / name).read_bytes() for name in locales.FILES}, baseline)
        self.assertEqual(len(outputs), 12)
        for relative, content in outputs.items():
            self.assertEqual(content, (baseline / relative).read_bytes(), relative)

    def test_all_current_profession_ids_and_numeric_data_survive_overlays(self):
        baseline = ROOT / "Core/Data"
        sources = {name: (baseline / name).read_bytes() for name in locales.FILES}
        outputs = locales.render_locales(sources, baseline)
        def without_text(value):
            if isinstance(value, str): return "<text>"
            if isinstance(value, list): return [without_text(item) for item in value]
            if isinstance(value, dict): return {key: without_text(item) for key, item in value.items()}
            return value
        expected = without_text(common.load_namespace(list(sources.items()), "zhCN"))
        for locale in locales.LOCALES:
            paths = list(sources.items()) + [(name, content) for name, content in outputs.items() if name.startswith(locale + "/")]
            self.assertEqual(expected, without_text(common.load_namespace(paths, locale)), locale)

    def test_reviewed_70450_changes_and_added_i18n_keep_versioned_sources(self):
        manifest = locales._maintenance(None, ROOT / 'Core/Data')
        self.assertEqual(manifest['schemaVersion'], 2)
        self.assertEqual(manifest['identityVersion'], 2)
        audit = json.loads((locales.MAINTENANCE.parent / 'locales-audit-70450-v2.json').read_text(encoding='utf-8'))
        self.assertEqual(common.sha(locales.MAINTENANCE.read_bytes()), audit['afterMaintenanceSHA256'])
        self.assertEqual(sum(len(entries) for entries in manifest['files'].values()),
                         audit['identityMigration']['preservedRecordCount'] + len(audit['addedSourceRecords']))
        for migration in audit['identityMigration']['keyMigrations']:
            record = manifest['files'][migration['file']][migration['after']]
            self.assertTrue(any(version['sourceSHA256'] == migration['sourceSHA256']
                                for version in locales._versions(record)), migration['after'])
        self.assertEqual(len(audit['reviewedSourceChanges']), 7)
        for change in audit['reviewedSourceChanges']:
            record = manifest['files'][change['file']][change['record']]
            self.assertEqual(record['source'], change['after']['source'])
            self.assertTrue(any(prior['source'] == change['before']['source'] and
                                prior['translations'] == change['before']['translations']
                                for prior in record['history']))
        zh = json.loads((TOOLS / '_fc/i18n/zh.json').read_text(encoding='utf-8'))
        self.assertEqual(zh['All Stats +1'], '全属性 +1')
        self.assertEqual(zh['Fishing Pole'], '鱼竿')


if __name__ == "__main__":
    unittest.main()
