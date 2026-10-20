"""Run the exporter under Windows PowerShell 5.1 with isolated WTL fixtures."""
import csv
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/export_buyprice/export-item-buy-prices.ps1"
POWERSHELL = shutil.which("powershell.exe")


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(POWERSHELL, "Windows PowerShell 5.1 is required")
class ItemPriceExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="df-item-export-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.tool = self.directory / "tool"
        self.tool.mkdir()
        (self.tool / "wow.tools.local.exe").write_bytes(b"fixture executable")
        self.cache = self.tool / "caches"
        self.cache.mkdir()
        self.cache_file = self.cache / "DBCache-Raidbots-classic_beta-fixture.bin"
        self.price = self.directory / "prices.csv"
        self.item = self.directory / "item.csv"
        self.recipe = self.directory / "recipe-item-specializations.csv"
        self.snapshot = self.directory / "snapshot"
        self.item_text = 'ID,ClassID,SubclassID,Comment,Unchanged\r\n2,7,0,"Copper, \"\"raw\"\"\n铜",keep\r\n3,2,1,不翻译,yes\r\n1,15,0,,last\r\n'
        (self.directory / "raw.csv").write_text(self.item_text, encoding="utf-8", newline="")
        for locale, name in (("enUS", 'Thread, "name"\nnext'), ("zhTW", "粗線"), ("zhCN", "粗线")):
            self.write_sparse(locale, name)
        for table, fields in {
            "itemeffect": ["ID", "SpellID", "TriggerType"],
            "itemxitemeffect": ["ID", "ItemID", "ItemEffectID"],
            "spelleffect": ["ID", "SpellID", "Effect", "EffectTriggerSpell"],
            "spelllearnspell": ["ID", "SpellID", "LearnSpellID"],
            "skilllineability": ["ID", "SkillLine", "Spell"],
            "skillline": ["ID", "ParentSkillLineID"],
        }.items():
            self.write_table(table, fields, [])
        self.write_table("spellname", ["ID", "Name_lang"], [[12906, '侏儒, "battle"\nchicken']])
        self.mock = r'''
$script:FixtureRequests = [Collections.Generic.List[string]]::new()
$script:FixtureBuildReads = 0
$script:FixtureStarts = 0
$script:FixtureStops = 0
$script:FixtureOwn = $false
$script:FixtureStarted = $false
function Get-WtlListener {
    param($BaseUri)
    if ($script:FixtureOwn -and -not $script:FixtureStarted) { return $null }
    $pidValue = if ($script:FixtureOwn) { [Diagnostics.Process]::GetCurrentProcess().Id } else { 900001 }
    return [pscustomobject]@{ Id=$pidValue; ExecutablePath=(Join-Path $script:FixtureTool 'wow.tools.local.exe') }
}
function Start-WtlService {
    param($ExecutablePath,$ToolDirectory,$BaseUri,$LogDirectory)
    $script:FixtureStarts++; $script:FixtureStarted=$true
    return [Diagnostics.Process]::GetCurrentProcess()
}
function Stop-WtlOwnedProcess { param($Process,$ExecutablePath); $script:FixtureStops++ }
function Invoke-WtlTextRequest {
    param($BaseUri,$RelativeUrl,$TimeoutSec)
    $script:FixtureRequests.Add($RelativeUrl)
    if ($RelativeUrl -eq 'casc/buildname') {
        $script:FixtureBuildReads++
        return '1.60.1.70450'
    }
    if ($RelativeUrl -like 'dbc/hotfixes/downloadLatest*') {
        $bytes = [byte[]]([Text.Encoding]::ASCII.GetBytes('XFTH') + [BitConverter]::GetBytes([uint32]9) +
            [BitConverter]::GetBytes([uint32]70450) + (New-Object byte[] 32))
        [IO.File]::WriteAllBytes($script:FixtureCache,$bytes)
        return ''
    }
    if ($RelativeUrl -eq 'dbc/reloadHotfixes') { return 'Reloaded hotfixes' }
    if ($RelativeUrl -like 'dbc/export/?name=item&*') {
        return [IO.File]::ReadAllText((Join-Path $script:FixtureRoot 'raw.csv'),[Text.Encoding]::UTF8)
    }
    if ($RelativeUrl -like 'dbc/export/?name=itemsparse&*') {
        $locale = ($RelativeUrl -split 'locale=')[-1]
        return [IO.File]::ReadAllText((Join-Path $script:FixtureRoot ($locale+'.csv')),[Text.Encoding]::UTF8)
    }
    if ($RelativeUrl -match '^dbc/export/\?name=(itemeffect|itemxitemeffect|spelleffect|spelllearnspell|skilllineability|skillline|spellname)&') {
        return [IO.File]::ReadAllText((Join-Path $script:FixtureRoot ($Matches[1]+'.csv')),[Text.Encoding]::UTF8)
    }
    throw ('Unexpected fixture request: '+$RelativeUrl)
}
'''

    def test_repository_boundary_rejects_output_before_any_service_request(self):
        escape = self.directory.parent / (self.directory.name + '-outside') / 'prices.csv'
        code = '$script:ItemPriceRepositoryRoot=' + literal(self.directory) + ';'
        code += 'try { $null=' + self.invocation(price=escape) + "; throw 'expected boundary rejection' } catch {"
        code += "if($_.Exception.Message -notlike '*inside the current repository*'){throw};"
        code += "if($script:FixtureRequests.Count -ne 0){throw 'network before boundary check'}; exit 23 }"
        self.ps(code, expected=23)
        self.assertFalse(escape.parent.exists())

    def test_repository_boundary_rejects_external_tool_before_service_request(self):
        scope = self.directory / 'limited-repository'
        scope.mkdir()
        code = '$script:ItemPriceRepositoryRoot=' + literal(scope) + ';'
        code += 'try { $null=' + self.invocation() + "; throw 'expected boundary rejection' } catch {"
        code += "if($_.Exception.Message -notlike '*inside the current repository*'){throw};"
        code += "if($script:FixtureRequests.Count -ne 0){throw 'network before tool boundary check'}; exit 23 }"
        self.ps(code, expected=23)

    def write_sparse(self, locale, name, price=20, pack=5):
        with (self.directory / (locale + ".csv")).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["ID", "Display_lang", "BuyPrice", "VendorStackCount"])
            writer.writerow([2, name, price, pack])
            writer.writerow([3, "Zero", 0, 0])
            writer.writerow([4, "Sparse only", 100, 1])

    def write_table(self, table, fields, rows):
        with (self.directory / (table + ".csv")).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(fields)
            writer.writerows(rows)

    def configure_recipes(self, abilities, required_skills=None, subclasses=None):
        subclasses = subclasses or {}
        self.write_table("raw", ["ID", "ClassID", "SubclassID"], [[item_id, 9, subclasses.get(item_id, 3)] for item_id in abilities] + [[900, 7, 1]])
        for locale in ("enUS", "zhTW", "zhCN"):
            fields = ["ID", "Display_lang", "BuyPrice", "VendorStackCount", "RequiredAbility"]
            rows = [[item_id, "Goblin/Gnomish name is not evidence", 10, 1, ability]
                    for item_id, ability in abilities.items() if ability is not None] + [[900, "Finished product", 10, 1, 20222]]
            if required_skills is not None:
                fields.append("RequiredSkill")
                for row in rows:
                    row.append(required_skills.get(row[0]))
            self.write_table(locale, fields, rows)
        self.write_table("skillline", ["ID", "ParentSkillLineID"], [[202, 0], [2941, 202], [762, 0]])
        self.write_table("skilllineability", ["ID", "SkillLine", "Spell"],
                         [[1, 2941, 12906], [2, 202, 12760], [3, 202, 12754], [4, 202, 50000], [5, 762, 88888]])

    def recipe_rows(self):
        return list(csv.DictReader(io.StringIO(self.recipe.read_text(encoding="utf-8-sig"))))

    def ps(self, code, expected=0, mock=True):
        source = ". " + literal(SCRIPT) + "; $ErrorActionPreference='Stop'; "
        if mock:
            source += "$script:FixtureRoot=" + literal(self.directory) + ";"
            source += "$script:FixtureTool=" + literal(self.tool) + ";"
            source += "$script:FixtureCache=" + literal(self.cache_file) + ";"
            source += self.mock
        result = subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", base64.b64encode((source + code + "; exit 0").encode('utf-16le')).decode('ascii')],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        self.assertEqual(result.returncode, expected, result.stdout + "\n" + result.stderr)
        return result

    def invocation(self, price=None, item=None, recipe=None, snapshot=None):
        command = (
            "Invoke-ItemBuyPriceExport -ToolDirectory " + literal(self.tool)
            + " -OutputPath " + literal(price or self.price)
            + " -ItemOutputPath " + literal(item or self.item)
            + " -RecipeItemOutputPath " + literal(recipe or self.recipe)
        )
        if snapshot is not None:
            command += " -LearningSnapshotPath " + literal(snapshot)
        return command

    def prior_outputs(self):
        self.price.write_bytes(b"previous price\n")
        self.item.write_bytes(b"previous item\n")
        self.recipe.write_bytes(b"previous recipe\n")

    def assert_prior(self):
        self.assertEqual(self.price.read_bytes(), b"previous price\n")
        self.assertEqual(self.item.read_bytes(), b"previous item\n")
        self.assertEqual(self.recipe.read_bytes(), b"previous recipe\n")
        self.assertFalse(list(self.directory.rglob("*.tmp")))
        self.assertFalse(list(self.directory.rglob("*.previous")))
        self.assertFalse(list(self.directory.rglob("*.rollback")))

    def expect_failure(self, before="", invocation=None):
        return self.ps(before + "try { $null=" + (invocation or self.invocation()) +
                       "; throw 'expected failure was not raised' } catch { [Console]::WriteLine($_.Exception.Message); exit 23 }", expected=23)

    def test_pair_exports_full_item_once_with_unicode_and_original_columns(self):
        result = self.ps("$r=" + self.invocation() + "; 'RESULT:'+(@{Result=$r;Requests=@($script:FixtureRequests);Stops=$script:FixtureStops}|ConvertTo-Json -Depth 5 -Compress)")
        data = json.loads(next(line[7:] for line in result.stdout.splitlines() if line.startswith("RESULT:")))
        self.assertEqual(data["Result"]["ItemOutputPath"], str(self.item))
        self.assertEqual(data["Result"]["ItemCount"], 3)
        self.assertEqual(data["Result"]["RecipeItemOutputPath"], str(self.recipe))
        self.assertEqual(data["Result"]["RecipeItemCount"], 0)
        self.assertIsNone(data["Result"]["LearningSnapshotPath"])
        requests = data["Requests"]
        self.assertEqual(sum("name=item&" in url for url in requests), 1)
        self.assertEqual(sum("name=itemsparse&" in url for url in requests), 3)
        self.assertEqual(sum("dbc/export/" in url for url in requests), 10)
        self.assertFalse(any("name=spellname&" in url for url in requests))
        self.assertTrue(all("build=1.60.1.70450" in url and "useHotfixes=true" in url for url in requests if "dbc/export/" in url))
        self.assertEqual(data["Stops"], 0, "a reused service was stopped")
        self.assertEqual(self.item.read_bytes(), b"\xef\xbb\xbf" + self.item_text.encode("utf-8"))
        rows = list(csv.DictReader(io.StringIO(self.item.read_text(encoding="utf-8-sig"))))
        self.assertEqual(list(rows[0]), ["ID", "ClassID", "SubclassID", "Comment", "Unchanged"])
        self.assertEqual(rows[0]["Comment"], 'Copper, "raw"\n铜')
        self.assertEqual(rows[1]["Comment"], "不翻译")
        prices = list(csv.DictReader(io.StringIO(self.price.read_text(encoding="utf-8-sig"))))
        self.assertEqual([r["ItemID"] for r in prices], ["1", "2", "3", "4"])
        self.assertEqual(prices[0]["PriceStatus"], "missing_item_sparse")
        self.assertEqual(prices[1]["BuyPriceCopper"], "20")
        self.assertEqual(prices[1]["VendorStackCount"], "5")
        self.assertEqual(prices[1]["Name_zhCN"], "粗线")
        self.assertEqual(prices[2]["PriceStatus"], "zero")
        reader = csv.DictReader(io.StringIO(self.recipe.read_text(encoding="utf-8-sig")))
        self.assertEqual(reader.fieldnames, ["RecipeItemID", "RecipeSpellID", "RequiredAbility", "Status", "Reason", "LearningPath", "Build", "HotfixBuild", "Source"])
        self.assertEqual(list(reader), [])
        self.assertFalse(list(self.directory.rglob("*.tmp")))

    def test_success_replaces_both_existing_files_and_cleans_backups(self):
        self.prior_outputs()
        self.ps("$null=" + self.invocation())
        self.assertTrue(self.item.read_bytes().startswith(b"\xef\xbb\xbfID,"))
        self.assertTrue(self.price.read_bytes().startswith(b'\xef\xbb\xbf"ItemID"'))
        self.assertFalse(list(self.directory.rglob("*.previous")))

    def test_learning_snapshot_reuses_requests_and_records_exact_bytes_and_version(self):
        self.snapshot.mkdir()  # A pre-existing empty stage directory is supported.
        result = self.ps("$r=" + self.invocation(snapshot=self.snapshot) +
                         "; 'RESULT:'+(@{Result=$r;Requests=@($script:FixtureRequests)}|ConvertTo-Json -Depth 5 -Compress)")
        data = json.loads(next(line[7:] for line in result.stdout.splitlines() if line.startswith("RESULT:")))
        manifest = json.loads((self.snapshot / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(data["Result"]["LearningSnapshotPath"], str(self.snapshot))
        self.assertEqual(manifest["schemaVersion"], 1)
        self.assertEqual(manifest["build"], data["Result"]["Build"])
        self.assertEqual(manifest["hotfixBuild"], data["Result"]["HotfixBuild"])
        self.assertEqual(manifest["hotfixSHA256"], hashlib.sha256(self.cache_file.read_bytes()).hexdigest().upper())
        self.assertIs(manifest["useHotfixes"], True)
        self.assertIsNotNone(datetime.fromisoformat(manifest["fetchedAt"].replace("Z", "+00:00")).tzinfo)
        expected = {"item": "raw", "itemsparse": "enUS", "itemeffect": "itemeffect", "itemxitemeffect": "itemxitemeffect",
                    "spelleffect": "spelleffect", "spelllearnspell": "spelllearnspell", "skilllineability": "skilllineability",
                    "skillline": "skillline", "spellname": "spellname"}
        self.assertEqual(set(manifest["tables"]), set(expected))
        self.assertEqual({p.name for p in self.snapshot.iterdir()}, {name + ".csv" for name in expected} | {"manifest.json"})
        self.assertEqual(sum("dbc/export/" in url for url in data["Requests"]), 11)
        for table, fixture in expected.items():
            with self.subTest(table=table):
                contents = (self.snapshot / (table + ".csv")).read_bytes()
                self.assertEqual(contents, b"\xef\xbb\xbf" + (self.directory / (fixture + ".csv")).read_bytes())
                metadata = manifest["tables"][table]
                self.assertEqual(metadata["sha256"], hashlib.sha256(contents).hexdigest())
                rows = list(csv.DictReader(io.StringIO(contents.decode("utf-8-sig"))))
                self.assertEqual(metadata["rows"], len(rows))
                self.assertIn("build=1.60.1.70450&useHotfixes=true", metadata["url"])
                self.assertTrue(metadata["url"].startswith("http://127.0.0.1:5000/dbc/export/"))
                self.assertTrue(metadata["url"].endswith("locale=enUS"))
                self.assertEqual(sum(f"name={table}&" in url and url.endswith("locale=enUS") for url in data["Requests"]), 1)
        self.assertEqual((self.snapshot / "item.csv").read_bytes(), self.item.read_bytes())

    def test_nonempty_snapshot_is_rejected_without_modifying_outputs_or_snapshot(self):
        self.prior_outputs()
        self.snapshot.mkdir()
        existing = self.snapshot / "manifest.json"
        existing.write_bytes(b"previous snapshot")
        result = self.expect_failure(invocation=self.invocation(snapshot=self.snapshot))
        self.assertIn("existing snapshots are never overwritten", result.stdout)
        self.assertEqual(existing.read_bytes(), b"previous snapshot")
        self.assertEqual([p.name for p in self.snapshot.iterdir()], ["manifest.json"])
        self.assertFalse(self.cache_file.exists(), "a rejected snapshot should not contact the service")
        self.assert_prior()

    def test_snapshot_path_cannot_alias_or_contain_outputs(self):
        self.prior_outputs()
        for path in (self.item, self.directory, self.directory / ".." / self.directory.name, self.item / "child"):
            with self.subTest(path=path):
                self.assertIn("overlaps a CSV output", self.expect_failure(invocation=self.invocation(snapshot=path)).stdout)
                self.assert_prior()
        self.assertFalse(self.cache_file.exists())

    def test_snapshot_write_failure_preserves_outputs_and_removes_created_snapshot_files(self):
        self.prior_outputs()
        before = "${function:FixtureWriteSnapshot}=${function:Write-WtlNewSnapshotFile};"
        before += "function Write-WtlNewSnapshotFile {param($Path,$Text,$Bom,$CreatedFiles);"
        before += "if([IO.Path]::GetFileName($Path) -eq 'itemsparse.csv'){throw [IO.IOException]::new('fixture snapshot write failed')};"
        before += "FixtureWriteSnapshot $Path $Text $Bom $CreatedFiles};"
        self.assertIn("Learning snapshot failed", self.expect_failure(before, self.invocation(snapshot=self.snapshot)).stdout)
        self.assertTrue(self.snapshot.is_dir())
        self.assertEqual(list(self.snapshot.iterdir()), [])
        self.assert_prior()

    def test_changed_build_prevents_snapshot_and_output_publication(self):
        self.prior_outputs()
        before = "${function:FixtureOriginalRequest}=${function:Invoke-WtlTextRequest};function Invoke-WtlTextRequest {param($BaseUri,$RelativeUrl,$TimeoutSec);if($RelativeUrl -eq 'casc/buildname' -and $script:FixtureBuildReads -gt 0){return '1.60.1.70451'};FixtureOriginalRequest $BaseUri $RelativeUrl $TimeoutSec};"
        self.assertIn("changed during export", self.expect_failure(before, self.invocation(snapshot=self.snapshot)).stdout)
        self.assertFalse((self.snapshot / "manifest.json").exists())
        self.assert_prior()

    def test_recipe_direct_and_explicit_nested_learning_paths(self):
        self.configure_recipes({100: 20219, 101: 20222, 102: 20219, 103: 20219, 104: 20219})
        self.write_table("itemeffect", ["ID", "SpellID", "TriggerType", "ParentItemID"],
                         [[1, 12906, 6, 0], [2, 402265, 6, 0], [3, 7001, 0, 0],
                          [4, 7300, 0, 0], [5, 7500, 0, 0], [6, 12906, 6, 104],
                          [7, 12754, 6, 900]])
        self.write_table("itemxitemeffect", ["ID", "ItemID", "ItemEffectID"],
                         [[1, 100, 1], [2, 101, 2], [3, 101, 3], [4, 102, 4], [5, 103, 5], [6, 900, 7]])
        self.write_table("spelleffect", ["ID", "SpellID", "Effect", "EffectTriggerSpell"],
                         [[1, 7001, 36, 12760], [2, 7500, 36, 12906]])
        self.write_table("spelllearnspell", ["ID", "SpellID", "LearnSpellID"],
                         [[1, 7300, 7301], [2, 7301, 12906], [3, 7500, 12906]])
        self.ps("$null=" + self.invocation())
        rows = self.recipe_rows()
        self.assertEqual([(r["RecipeItemID"], r["RecipeSpellID"], r["RequiredAbility"], r["Status"]) for r in rows],
                         [("100", "12906", "20219", "confirmed"), ("101", "12760", "20222", "confirmed"),
                          ("102", "12906", "20219", "confirmed"), ("103", "12906", "20219", "confirmed"),
                          ("104", "12906", "20219", "confirmed")])
        self.assertIn("TriggerType=6", rows[0]["LearningPath"])
        self.assertIn("Effect=36/EffectTriggerSpell=12760", rows[1]["LearningPath"])
        self.assertIn("SpellLearnSpell[2].LearnSpellID=12906", rows[2]["LearningPath"])
        self.assertIn("SpellEffect", rows[3]["LearningPath"])
        self.assertIn("SpellLearnSpell", rows[3]["LearningPath"], "two paths to one target must be retained without ambiguity")
        self.assertIn("ParentItemID=104", rows[4]["LearningPath"])
        self.assertTrue(all(r["Build"] == "1.60.1.70450" and r["HotfixBuild"] == "70450" for r in rows))
        self.assertTrue(all(r["Source"] == "wow.tools.local:ItemSparse.RequiredAbility" for r in rows))

    def test_zero_and_missing_ability_remain_pending_even_with_resolved_spells(self):
        self.configure_recipes({100: 0, 101: None, 102: ""})
        self.write_table("itemeffect", ["ID", "SpellID", "TriggerType"], [[1, 12906, 6]])
        self.write_table("itemxitemeffect", ["ID", "ItemID", "ItemEffectID"], [[i, item_id, 1] for i, item_id in enumerate((100, 101, 102), 1)])
        self.ps("$null=" + self.invocation())
        rows = self.recipe_rows()
        self.assertEqual([r["RequiredAbility"] for r in rows], ["0", "", ""])
        self.assertTrue(all(r["RecipeSpellID"] == "12906" and r["Status"] == "pending" for r in rows))
        self.assertEqual(rows[0]["Reason"], "zero_required_ability")
        self.assertTrue(all(r["Reason"] == "missing_required_ability" for r in rows[1:]))
        for locale in ("enUS", "zhTW", "zhCN"):
            self.write_table(locale, ["ID", "Display_lang", "BuyPrice", "VendorStackCount"],
                             [[item_id, "Recipe", 10, 1] for item_id in (100, 101, 102)])
        self.ps("$null=" + self.invocation())
        self.assertTrue(all(r["Status"] == "pending" and r["Reason"] == "missing_required_ability" and r["RequiredAbility"] == ""
                            for r in self.recipe_rows()))

    def test_required_profession_and_concrete_craft_effect_fill_missing_sla_targets(self):
        # Six real missing-SLA item links, plus a book using a child profession
        # and a permanent enchant. The source names do not drive the result.
        cases = [
            (2404, 2156, 165, 24, 2305, 1), (2405, 2157, 165, 24, 2306, 1),
            (6222, 7451, 333, 54, 64, 8), (6343, 7451, 333, 54, 64, 8),
            (8547, 10844, 129, 24, 8546, 7), (274491, 1294289, 165, 24, 274490, 1),
            (300001, 90001, 2941, 24, 99999, 0), (300002, 90002, 333, 53, 99, 0),
        ]
        self.configure_recipes({c[0]: 0 for c in cases}, {c[0]: c[2] for c in cases}, {c[0]: c[5] for c in cases})
        self.write_table("itemeffect", ["ID", "SpellID", "TriggerType"], [[i, c[1], 6] for i, c in enumerate(cases, 1)])
        self.write_table("itemxitemeffect", ["ID", "ItemID", "ItemEffectID"], [[i, c[0], i] for i, c in enumerate(cases, 1)])
        self.write_table("spelleffect", ["ID", "SpellID", "Effect", "EffectTriggerSpell", "EffectItemType", "EffectMiscValue[0]"],
                         [[i, c[1], c[3], 0, c[4] if c[3] == 24 else 0, c[4] if c[3] in (53, 54) else 0]
                          for i, c in enumerate(cases, 1)])
        self.ps("$null=" + self.invocation())
        rows = {int(r["RecipeItemID"]): r for r in self.recipe_rows()}
        self.assertEqual(len(rows), len(cases))
        for i, (item_id, spell_id, skill_id, effect, value, _) in enumerate(cases, 1):
            with self.subTest(item=item_id):
                row = rows[item_id]
                self.assertEqual((row["RecipeSpellID"], row["Status"], row["Reason"]), (str(spell_id), "pending", "zero_required_ability"))
                self.assertIn(f"ItemSparse[{item_id}].RequiredSkill={skill_id}", row["LearningPath"])
                field = "EffectItemType" if effect == 24 else "EffectMiscValue[0]"
                self.assertIn(f"SpellEffect[{i}].Effect={effect}/{field}={value}", row["LearningPath"])

    def test_craft_fallback_rejects_non_professions_nonlearning_triggers_and_incomplete_evidence(self):
        skills = {100: 40, 101: 2851, 102: 165, 103: 165, 104: 165, 105: 165,
                  106: 165, 107: 0, 108: None, 109: 165, 110: 165, 111: 165}
        self.configure_recipes({i: 0 for i in skills}, skills)
        self.write_table("itemeffect", ["ID", "SpellID", "TriggerType"],
                         [[i, i + 90000, 1 if i == 103 else 6] for i in skills])
        self.write_table("itemxitemeffect", ["ID", "ItemID", "ItemEffectID"], [[i, i, i] for i in skills])
        self.write_table("skilllineability", ["ID", "SkillLine", "Spell"], [[1, 40, 90102]])
        effects = [[i, i + 90000, 24, 0, 999, 0] for i in skills if i not in (104, 105, 109, 110)]
        effects += [[104, 90104, 24, 0, 0, 99], [105, 90105, 54, 0, 0, 0],
                    [109, 90109, 3, 0, 999, 99], [110, 90110, 54, 0, 0, -1],
                    [200, 90106, 118, 0, 0, 165], [201, 90111, 44, 0, 0, 165]]
        self.write_table("spelleffect", ["ID", "SpellID", "Effect", "EffectTriggerSpell", "EffectItemType", "EffectMiscValue[0]"], effects)
        self.ps("$null=" + self.invocation())
        rows = self.recipe_rows()
        self.assertEqual(len(rows), len(skills))
        self.assertTrue(all(r["RecipeSpellID"] == "" and r["Status"] == "pending" for r in rows))
        self.assertTrue(all("no_profession_recipe_target" in r["Reason"] for r in rows))

    def test_craft_fallback_requires_optional_fields_and_preserves_explicit_learning_graph(self):
        self.configure_recipes({100: 0}, {100: 165})
        self.write_table("itemeffect", ["ID", "SpellID", "TriggerType"], [[1, 7001, 0]])
        self.write_table("itemxitemeffect", ["ID", "ItemID", "ItemEffectID"], [[1, 100, 1]])
        self.write_table("spelleffect", ["ID", "SpellID", "Effect", "EffectTriggerSpell"],
                         [[1, 7001, 36, 90001], [2, 90001, 24, 0]])
        self.ps("$null=" + self.invocation())
        self.assertEqual(self.recipe_rows()[0]["RecipeSpellID"], "")
        self.write_table("spelleffect", ["ID", "SpellID", "Effect", "EffectTriggerSpell", "EffectItemType"],
                         [[1, 7001, 36, 90001, 0], [2, 90001, 24, 0, 999]])
        self.ps("$null=" + self.invocation())
        row = self.recipe_rows()[0]
        self.assertEqual(row["RecipeSpellID"], "90001")
        self.assertIn("Effect=36/EffectTriggerSpell=90001", row["LearningPath"])
        self.assertIn("RequiredSkill=165", row["LearningPath"])
        self.configure_recipes({100: 0})  # Missing RequiredSkill column is not zero or a profession.
        self.ps("$null=" + self.invocation())
        self.assertEqual(self.recipe_rows()[0]["RecipeSpellID"], "")

    def test_required_skill_locale_conflict_preserves_all_outputs(self):
        self.prior_outputs()
        self.configure_recipes({100: 0}, {100: 165})
        self.write_table("zhCN", ["ID", "Display_lang", "BuyPrice", "VendorStackCount", "RequiredAbility", "RequiredSkill"],
                         [[100, "Recipe", 10, 1, 0, 164], [900, "Finished product", 10, 1, 20222, ""]])
        self.assertIn("Conflicting RequiredSkill", self.expect_failure().stdout)
        self.assert_prior()

    def test_cycles_multiple_targets_and_non_recipe_targets_remain_pending(self):
        self.configure_recipes({item_id: 20219 for item_id in range(100, 109)})
        self.write_table("itemeffect", ["ID", "SpellID", "TriggerType"],
                         [[1, 7100, 0], [2, 7200, 0], [3, 402265, 6], [4, 50000, 6],
                          [5, 7400, 0], [6, 7401, 0], [7, 88888, 6]])
        self.write_table("itemxitemeffect", ["ID", "ItemID", "ItemEffectID"],
                         [[i, 99 + i, i] for i in range(1, 8)] + [[8, 107, 999]])
        self.write_table("spelleffect", ["ID", "SpellID", "Effect", "EffectTriggerSpell"],
                         [[1, 7100, 36, 7101], [2, 7101, 36, 7100],
                          [3, 7200, 36, 12906], [4, 7200, 36, 12760],
                          [5, 50000, 44, 0], [6, 7400, 36, -1], [7, 7401, 3, 12906]])
        self.ps("$null=" + self.invocation())
        rows = self.recipe_rows()
        self.assertEqual(len(rows), 10)
        self.assertTrue(all(r["Status"] == "pending" for r in rows))
        by_item = {}
        for row in rows:
            by_item.setdefault(row["RecipeItemID"], []).append(row)
        self.assertIn("learning_cycle", by_item["100"][0]["Reason"])
        self.assertEqual([r["RecipeSpellID"] for r in by_item["101"]], ["12760", "12906"])
        self.assertTrue(all("ambiguous_recipe_spells" in r["Reason"] for r in by_item["101"]))
        for item_id in range(102, 109):
            self.assertEqual(by_item[str(item_id)][0]["RecipeSpellID"], "")
        self.assertIn("missing_linked_item_effect", by_item["107"][0]["Reason"])
        self.assertIn("missing_item_effect", by_item["108"][0]["Reason"])

    def test_recipe_ability_conflict_and_bad_learning_table_preserve_all_outputs(self):
        self.prior_outputs()
        self.configure_recipes({100: 20219})
        self.write_table("zhCN", ["ID", "Display_lang", "BuyPrice", "VendorStackCount", "RequiredAbility"],
                         [[100, "Recipe", 10, 1, 20222], [900, "Finished product", 10, 1, 20222]])
        self.assertIn("Conflicting RequiredAbility", self.expect_failure().stdout)
        self.assert_prior()
        self.configure_recipes({100: 20219})
        self.write_table("spelllearnspell", ["ID", "SpellID"], [[1, 7300]])
        self.assertIn("LearnSpellID", self.expect_failure().stdout)
        self.assert_prior()

    def test_locale_price_conflict_preserves_both_previous_outputs(self):
        self.prior_outputs()
        self.write_sparse("zhCN", "粗线", price=21)
        self.assertIn("Conflicting price", self.expect_failure().stdout)
        self.assert_prior()

    def test_locale_bundle_conflict_preserves_both_previous_outputs(self):
        self.prior_outputs()
        self.write_sparse("zhTW", "粗線", pack=6)
        self.expect_failure()
        self.assert_prior()

    def test_invalid_raw_item_classes_preserve_previous_outputs(self):
        self.prior_outputs()
        (self.directory / "raw.csv").write_text("ID,ClassID,SubclassID\n1,invalid,0\n", encoding="utf-8")
        self.assertIn("ClassID", self.expect_failure().stdout)
        self.assert_prior()

    def test_duplicate_item_id_preserves_previous_outputs(self):
        self.prior_outputs()
        (self.directory / "raw.csv").write_text("ID,ClassID,SubclassID\n1,7,0\n1,7,0\n", encoding="utf-8")
        self.assertIn("Duplicate item", self.expect_failure().stdout)
        self.assert_prior()

    def test_missing_raw_columns_preserve_previous_outputs(self):
        self.prior_outputs()
        (self.directory / "raw.csv").write_text("ID,ClassID\n1,7\n", encoding="utf-8")
        self.assertIn("SubclassID", self.expect_failure().stdout)
        self.assert_prior()

    def test_failed_second_replacement_rolls_back_first(self):
        self.prior_outputs()
        code = "$lock=[IO.File]::Open(" + literal(self.item) + ",[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read);"
        code += "try { try { $null=" + self.invocation() + "; throw 'expected failure was not raised' } catch { [Console]::WriteLine($_.Exception.Message) } } finally {$lock.Dispose()}"
        result = self.ps(code)
        self.assertIn("CSV publication failed", result.stdout)
        self.assert_prior()

    def test_failed_third_replacement_rolls_back_both_previous_replacements(self):
        self.prior_outputs()
        code = "$lock=[IO.File]::Open(" + literal(self.recipe) + ",[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read);"
        code += "try { try { $null=" + self.invocation() + "; throw 'expected failure was not raised' } catch { [Console]::WriteLine($_.Exception.Message) } } finally {$lock.Dispose()}"
        self.assertIn("CSV publication failed", self.ps(code).stdout)
        self.assert_prior()

    def test_failed_first_replacement_leaves_second_untouched(self):
        self.prior_outputs()
        code = "$lock=[IO.File]::Open(" + literal(self.price) + ",[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read);"
        code += "try { try { $null=" + self.invocation() + "; throw 'expected failure was not raised' } catch { [Console]::WriteLine($_.Exception.Message) } } finally {$lock.Dispose()}"
        self.ps(code)
        self.assert_prior()

    def test_failed_second_new_file_removes_first_new_file(self):
        stage = self.directory / "stage.tmp"
        stage.write_bytes(b"new price")
        code = "$files=@([pscustomobject]@{OutputPath=" + literal(self.price) + ";StagingPath=" + literal(stage) + "},"
        code += "[pscustomobject]@{OutputPath=" + literal(self.item) + ";StagingPath=" + literal(self.directory / "does-not-exist.tmp") + "});"
        code += "try {Publish-WtlCsvPair $files;throw 'expected failure'} catch {[Console]::WriteLine($_.Exception.Message)}"
        self.assertIn("CSV publication failed", self.ps(code).stdout)
        self.assertFalse(self.price.exists())
        self.assertFalse(self.item.exists())

    def test_same_normalized_case_insensitive_destinations_rejected(self):
        self.prior_outputs()
        alias = self.directory / ".." / self.directory.name / "PRICES.CSV"
        result = self.expect_failure(invocation=self.invocation(item=alias))
        self.assertIn("same file", result.stdout)
        self.assert_prior()

    def test_existing_hard_link_destinations_rejected(self):
        self.price.write_bytes(b"previous")
        try:
            os.link(self.price, self.item)
        except OSError as error:
            self.skipTest(str(error))
        result = self.expect_failure()
        self.assertIn("same file", result.stdout)
        self.assertEqual(self.price.read_bytes(), b"previous")
        self.assertEqual(self.item.read_bytes(), b"previous")

    def test_recipe_output_alias_to_either_other_output_is_rejected(self):
        self.prior_outputs()
        for path in (self.price, self.item):
            with self.subTest(path=path):
                self.assertIn("same file", self.expect_failure(invocation=self.invocation(recipe=path)).stdout)
                self.assert_prior()

    def test_dot_source_does_not_contact_service_or_export(self):
        self.ps("if(Get-Command Invoke-ItemBuyPriceExport -ErrorAction SilentlyContinue){'LOADED'}else{exit 5}", mock=False)
        self.assertFalse(self.item.exists())

    def test_relative_paths_resolve_against_exporter_directory(self):
        result = self.ps("[Console]::WriteLine((Resolve-ItemPricePath 'output\\item.csv'))", mock=False)
        self.assertEqual(result.stdout.strip(), str(SCRIPT.parent / "output/item.csv"))

    def test_start_owned_service_is_stopped_after_export(self):
        result = self.ps("$script:FixtureOwn=$true;$null=" + self.invocation() + ";'OWN:'+ $script:FixtureStarts+','+$script:FixtureStops")
        self.assertIn("OWN:1,1", result.stdout)

    def test_owned_service_is_stopped_after_validation_failure(self):
        self.prior_outputs()
        self.write_sparse("zhCN", "粗线", price=21)
        result = self.ps("$script:FixtureOwn=$true;try{$null=" + self.invocation() + "}catch{};'OWN:'+$script:FixtureStarts+','+$script:FixtureStops")
        self.assertIn("OWN:1,1", result.stdout)
        self.assert_prior()

    def test_other_executable_listener_rejected_without_output_changes(self):
        self.prior_outputs()
        before = "function Get-WtlListener {param($BaseUri);return [pscustomobject]@{Id=2;ExecutablePath='C:\\unrelated.exe'}};"
        self.assertIn("another executable", self.expect_failure(before).stdout)
        self.assert_prior()

    def test_false_success_download_does_not_fall_back_to_cached_export(self):
        self.prior_outputs()
        before = "${function:FixtureOriginalRequest}=${function:Invoke-WtlTextRequest};function Invoke-WtlTextRequest {param($BaseUri,$RelativeUrl,$TimeoutSec);if($RelativeUrl -like 'dbc/hotfixes/downloadLatest*'){return ''};FixtureOriginalRequest $BaseUri $RelativeUrl $TimeoutSec};"
        self.assertIn("did not create or update", self.expect_failure(before).stdout)
        self.assert_prior()

    def test_changed_cache_after_fetch_preserves_both_old_outputs(self):
        self.prior_outputs()
        before = "${function:FixtureOriginalRequest}=${function:Invoke-WtlTextRequest};function Invoke-WtlTextRequest {param($BaseUri,$RelativeUrl,$TimeoutSec);if($RelativeUrl -eq 'casc/buildname' -and $script:FixtureBuildReads -gt 0){[IO.File]::AppendAllText($script:FixtureCache,'changed')};FixtureOriginalRequest $BaseUri $RelativeUrl $TimeoutSec};"
        self.assertIn("changed during export", self.expect_failure(before).stdout)
        self.assert_prior()

    def test_startup_timeout_stops_only_owned_service_and_keeps_outputs(self):
        self.prior_outputs()
        before = "function Get-WtlListener {param($BaseUri);return $null};"
        invocation = self.invocation() + " -StartupTimeoutSec 1"
        result = self.ps(before + "try{$null=" + invocation + "}catch{[Console]::WriteLine($_.Exception.Message)};'STOPS:'+$script:FixtureStops")
        self.assertIn("startup timed out", result.stdout)
        self.assertIn("STOPS:1", result.stdout)
        self.assert_prior()

    def assert_output_mutex_blocks(self, destination):
        self.prior_outputs()
        holder = ". " + literal(SCRIPT) + ";$ErrorActionPreference='Stop';"
        holder += "$id=Get-WtlOutputIdentity " + literal(destination) + ";$h=[Security.Cryptography.SHA256]::Create();"
        holder += "$key=[BitConverter]::ToString($h.ComputeHash([Text.Encoding]::UTF8.GetBytes($id.Path))).Replace('-','');"
        holder += "$m=[Threading.Mutex]::new($false,('Local\\DungeonsForever.ItemPriceOutput.'+$key));"
        holder += "try{if(-not $m.WaitOne(0)){throw 'lock unavailable'};[Console]::WriteLine('READY');[Console]::Out.Flush();Start-Sleep -Seconds 30}finally{$m.ReleaseMutex();$m.Dispose()}"
        process = subprocess.Popen(
            [POWERSHELL, "-NoProfile", "-EncodedCommand", base64.b64encode(holder.encode('utf-16le')).decode('ascii')],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            self.assertEqual(process.stdout.readline().strip(), "READY")
            self.assertIn("already writing", self.expect_failure().stdout)
        finally:
            process.terminate()
            process.communicate(timeout=10)
        self.assert_prior()

    def test_output_mutex_prevents_different_service_from_publishing_same_pair(self):
        self.assert_output_mutex_blocks(self.price)

    def test_recipe_output_has_its_own_mutex(self):
        self.assert_output_mutex_blocks(self.recipe)

    def test_changed_final_build_preserves_both_old_outputs(self):
        self.prior_outputs()
        before = "${function:FixtureOriginalRequest}=${function:Invoke-WtlTextRequest};function Invoke-WtlTextRequest {param($BaseUri,$RelativeUrl,$TimeoutSec);if($RelativeUrl -eq 'casc/buildname' -and $script:FixtureBuildReads -gt 0){return '1.60.1.70451'};FixtureOriginalRequest $BaseUri $RelativeUrl $TimeoutSec};"
        self.assertIn("changed during export", self.expect_failure(before).stdout)
        self.assert_prior()

    def test_snapshot_and_hotfix_header_validation(self):
        code = r'''
$cache=$script:FixtureCache
function WriteHeader([uint32]$build,[uint32]$version=9){[IO.File]::WriteAllBytes($cache,[byte[]]([Text.Encoding]::ASCII.GetBytes('XFTH')+[BitConverter]::GetBytes($version)+[BitConverter]::GetBytes($build)+(New-Object byte[] 32)))}
WriteHeader 70450
$fresh=Get-WtlFreshCache (Split-Path $cache) @{} 70450
if($fresh.Build -ne 70450){throw 'wrong build'}
$snapshot=Get-WtlCacheSnapshot (Split-Path $cache)
try{Get-WtlFreshCache (Split-Path $cache) $snapshot 70450;throw 'expected stale'}catch{if($_.Exception.Message -notlike '*did not create*'){throw}}
WriteHeader 70451
try{Get-WtlFreshCache (Split-Path $cache) @{} 70450;throw 'expected mismatch'}catch{if($_.Exception.Message -notlike '*does not match*'){throw}}
WriteHeader 70450 99
try{Get-WtlFreshCache (Split-Path $cache) @{} 70450;throw 'expected bad version'}catch{if($_.Exception.Message -notlike '*unsupported*'){throw}}
[IO.File]::WriteAllBytes($cache,[byte[]]@(1,2,3))
try{Get-WtlFreshCache (Split-Path $cache) @{} 70450;throw 'expected truncated'}catch{if($_.Exception.Message -notlike '*truncated*'){throw}}
'''
        self.ps(code)

    def test_parser_rejects_negative_and_overflow_prices_and_bad_csv(self):
        code = r'''
foreach($bad in @('-1','4294967296','1.5','NaN')) {
    $csv="ID,Display_lang,BuyPrice,VendorStackCount`n1,Item,$bad,1`n"
    try{ConvertFrom-WtlItemCsv $csv 'itemsparse' 'enUS';throw 'expected invalid'}catch{if($_.Exception.Message -notlike '*Invalid unsigned*'){throw}}
}
foreach($csv in @('ID,ID','<html>Error</html>',"ID,ClassID,SubclassID`n1,7`n")) {
    try{ConvertFrom-WtlItemCsv $csv 'item' 'enUS';throw 'expected malformed'}catch{if($_.Exception.Message -notlike '*CSV validation failed*'){throw}}
}
'''
        self.ps(code)


@unittest.skipUnless(POWERSHELL, "Windows PowerShell 5.1 is required")
class ItemPriceTransportTests(unittest.TestCase):
    def test_transport_decodes_utf8_and_rejects_invalid_utf8_and_non_200(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"\xef\xbb\xbf" + "粗线".encode("utf-8") if self.path == "/good" else b"\xff"
                self.send_response(200 if self.path != "/error" else 500)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            code = ". " + literal(SCRIPT) + ";$ErrorActionPreference='Stop';$u=[uri]'http://127.0.0.1:" + str(server.server_port) + "/';"
            code += "$good=Invoke-WtlTextRequest $u 'good' 5;if($good -ne ([string][char]0x7C97+[char]0x7EBF)){throw 'bad UTF8'};"
            code += "foreach($p in @('bad','error')){try{$null=Invoke-WtlTextRequest $u $p 5;throw 'expected error'}catch{if($_.Exception.Message -eq 'expected error'){throw}}}"
            result = subprocess.run([POWERSHELL, "-NoProfile", "-EncodedCommand", base64.b64encode((code + "; exit 0").encode('utf-16le')).decode('ascii')], cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
