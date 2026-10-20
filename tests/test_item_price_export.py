"""Run the exporter under Windows PowerShell 5.1 with isolated WTL fixtures."""
import csv
import base64
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
        self.item_text = 'ID,ClassID,SubclassID,Comment,Unchanged\r\n2,7,0,"Copper, \"\"raw\"\"\n铜",keep\r\n3,2,1,不翻译,yes\r\n1,15,0,,last\r\n'
        (self.directory / "raw.csv").write_text(self.item_text, encoding="utf-8", newline="")
        for locale, name in (("enUS", 'Thread, "name"\nnext'), ("zhTW", "粗線"), ("zhCN", "粗线")):
            self.write_sparse(locale, name)
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
    throw ('Unexpected fixture request: '+$RelativeUrl)
}
'''

    def write_sparse(self, locale, name, price=20, pack=5):
        with (self.directory / (locale + ".csv")).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["ID", "Display_lang", "BuyPrice", "VendorStackCount"])
            writer.writerow([2, name, price, pack])
            writer.writerow([3, "Zero", 0, 0])
            writer.writerow([4, "Sparse only", 100, 1])

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

    def invocation(self, price=None, item=None):
        return (
            "Invoke-ItemBuyPriceExport -ToolDirectory " + literal(self.tool)
            + " -OutputPath " + literal(price or self.price)
            + " -ItemOutputPath " + literal(item or self.item)
        )

    def prior_outputs(self):
        self.price.write_bytes(b"previous price\n")
        self.item.write_bytes(b"previous item\n")

    def assert_prior(self):
        self.assertEqual(self.price.read_bytes(), b"previous price\n")
        self.assertEqual(self.item.read_bytes(), b"previous item\n")
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
        requests = data["Requests"]
        self.assertEqual(sum("name=item&" in url for url in requests), 1)
        self.assertEqual(sum("name=itemsparse&" in url for url in requests), 3)
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
        self.assertFalse(list(self.directory.rglob("*.tmp")))

    def test_success_replaces_both_existing_files_and_cleans_backups(self):
        self.prior_outputs()
        self.ps("$null=" + self.invocation())
        self.assertTrue(self.item.read_bytes().startswith(b"\xef\xbb\xbfID,"))
        self.assertTrue(self.price.read_bytes().startswith(b'\xef\xbb\xbf"ItemID"'))
        self.assertFalse(list(self.directory.rglob("*.previous")))

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

    def test_output_mutex_prevents_different_service_from_publishing_same_pair(self):
        self.prior_outputs()
        holder = ". " + literal(SCRIPT) + ";$ErrorActionPreference='Stop';"
        holder += "$id=Get-WtlOutputIdentity " + literal(self.price) + ";$h=[Security.Cryptography.SHA256]::Create();"
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
