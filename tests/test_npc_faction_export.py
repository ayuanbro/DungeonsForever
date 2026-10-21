"""Independent NPC affiliation exports: mocked WTL HTTP and frozen offline replay."""
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/export_npc_factions/export-npc-factions.ps1"
DECODER = ROOT / "scripts/export_npc_factions/decode_faction_names.py"
POWERSHELL = shutil.which("powershell.exe")
BUILD = "1.60.1.70450"
SPEC = importlib.util.spec_from_file_location("npc_faction_name_decoder", DECODER)
decoder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decoder)


def csv_bytes(fields, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(fields)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def faction_db2(names=None, copies=(), locale=1):
    names = names or {92: "Gelkis Clan Centaur", 93: "Magram Clan Centaur"}
    strings = bytearray(b"\0")
    records = bytearray()
    for index, name in enumerate(names.values()):
        relative = (len(names) - index) * 20 + len(strings)
        records += struct.pack("<i", relative) + b"\0" * 16
        strings += name.encode("utf-8") + b"\0"
    offset = 204 + 40 + 21 * 4 + 21 * 24
    header = struct.pack("<9I2H7I", len(names), 21, 20, len(strings), 0x06F624D7,
        0x6D443C38, min(names), max(names), locale, 4, 0, 21, 8, 0, 504, 0, 0, 1)
    section = struct.pack("<Q8I", 0, offset, len(names), len(strings), 0, len(names) * 4, 0, 0, len(copies))
    fields = b"\0" * (21 * 4)
    columns = struct.pack("<HHIIIII", 0, 32, 0, 0, 0, 0, 0) + b"\0" * (20 * 24)
    return (b"WDC5" + struct.pack("<I", 5) + b"wowstatic_camelot_1_60_1".ljust(128, b"\0") + header
        + section + fields + columns + records + strings + struct.pack(f"<{len(names)}I", *names)
        + b"".join(struct.pack("<2I", *copy) for copy in copies))


class FactionNameDecoderTests(unittest.TestCase):
    def test_all_rows_copy_ids_and_quoted_unicode_names_are_decoded(self):
        names, evidence = decoder.decode(faction_db2({8: 'Guild, "A"\n公会', 93: "Magram Clan Centaur"}, [(2790, 8)]))
        self.assertEqual(names, {8: 'Guild, "A"\n公会', 93: "Magram Clan Centaur", 2790: 'Guild, "A"\n公会'})
        self.assertTrue(evidence["localeVerified"])
        self.assertEqual(evidence["readableRows"], 3)

    def test_unknown_layout_locale_and_truncation_fail_closed(self):
        for offset, value in ((156, 0x12345678), (152, 3), (168, 0xFFFFFFFF)):
            data = bytearray(faction_db2())
            struct.pack_into("<I", data, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                decoder.decode(bytes(data))
        with self.assertRaises(ValueError):
            decoder.decode(faction_db2()[:-8])

    def test_cli_exports_full_csv_empty_npc_map_and_complete_hash_manifest(self):
        temporary = ROOT / ".pipeline-runtime/tmp"
        temporary.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary, prefix="df-faction-decoder-") as directory:
            folder = Path(directory)
            source = folder / "Faction.db2"
            source.write_bytes(faction_db2({10: "Ten", 92: "Gelkis Clan Centaur", 93: "Magram Clan Centaur"}, [(200, 10)]))
            before = source.read_bytes()
            output = folder / "result"
            run = subprocess.run([sys.executable, "-B", str(DECODER), "--input", str(source),
                "--output-dir", str(output), "--build", BUILD], capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr.decode(errors="replace"))
            with (output / "factions.csv").open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([int(row["ID"]) for row in rows], [10, 92, 93, 200])
            self.assertTrue(all(row["Name_zhCN"] == row["Name_zhTW"] == "" for row in rows))
            with (output / "npc-factions.csv").open(encoding="utf-8") as stream:
                self.assertEqual(list(csv.DictReader(stream)), [])
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(set(manifest["files"]), {"factions.csv", "npc-factions.csv", "raw/faction_enUS.db2"})
            for relative, proof in manifest["files"].items():
                content = (output / relative).read_bytes()
                self.assertEqual(proof, {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)})
            self.assertEqual(source.read_bytes(), before)


@unittest.skipUnless(POWERSHELL, "Windows PowerShell 5.1 is required")
class NPCFactionExportTests(unittest.TestCase):
    def setUp(self):
        temporary = ROOT / ".pipeline-runtime/tmp"
        temporary.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temporary, prefix="df-npc-faction-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.output = self.folder / "result"
        self.requests = []
        self.build_reads = 0
        self.changed_build = False
        self.bad_header = False
        self.bad_fk = False
        self.masks = {"enUS": 1, "zhCN": 16, "zhTW": 32}
        self.headers = {"creaturedifficulty": ["ID", "CreatureID", "FactionTemplateID"],
            "factiontemplate": ["ID", "Faction"], "faction": ["ID", "Name_lang"]}
        self.fks = {"creaturedifficulty": {"CreatureID": "Creature::ID", "FactionTemplateID": "FactionTemplate::ID"},
            "factiontemplate": {"Faction": "Faction::ID"}, "faction": {}}
        self.data = {("creaturedifficulty", "enUS"): csv_bytes(self.headers["creaturedifficulty"],
            [[1, 100, 10], [2, 100, 11], [3, 101, 12], [4, 101, 13], [5, 102, 99],
             [6, 103, 14], [7, 104, 0], [8, 105, 15], [9, 106, 10], [10, 106, 99], [11, 107, 10], [12, 107, 0]]),
            ("factiontemplate", "enUS"): csv_bytes(self.headers["factiontemplate"], [[10, 93], [11, 93], [12, 92], [13, 93], [14, 999], [15, 0]])}
        for locale, names in (("enUS", ["Gelkis Clan Centaur", 'Magram, "Clan"\nCentaur']),
                              ("zhCN", ["吉尔吉斯半人马", "玛格拉姆半人马"]),
                              ("zhTW", ["吉爾吉斯半人馬", "瑪格拉姆半人馬"])):
            self.data[("faction", locale)] = csv_bytes(self.headers["faction"], [[92, names[0]], [93, names[1]]])
        self.npcs = self.folder / "npcs.csv"
        self.npcs.write_bytes(csv_bytes(["npc_id", "name_en"], [[npc, "A merchant"] for npc in range(100, 109)]))
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                fixture.requests.append(self.path)
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                path = parsed.path.rstrip("/")
                if path == "/casc/buildname":
                    fixture.build_reads += 1
                    body = ("1.60.1.70374" if fixture.changed_build and fixture.build_reads > 1 else BUILD).encode()
                elif path.startswith("/dbc/header/"):
                    table = path.split("/")[-1]
                    fields = fixture.headers[table][:]
                    if fixture.bad_header and table == "creaturedifficulty":
                        fields.remove("CreatureID")
                    fks = dict(fixture.fks[table])
                    if fixture.bad_fk and table == "factiontemplate":
                        fks["Faction"] = "Creature::ID"
                    body = json.dumps({"headers": fields, "fks": fks, "error": ""}).encode()
                elif path == "/dbc/export":
                    body = fixture.data[(query["name"][0], query["locale"][0])]
                elif path == "/dbc/export/db2":
                    body = faction_db2(locale=fixture.masks[query["locale"][0]])
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def run_export(self, *extra, output=None, replay=None, success=True, hotfix=None):
        command = [POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
            "-Build", BUILD, "-OutputDirectory", str(output or self.output)]
        if replay:
            command += ["-InputSnapshotPath", str(replay)]
        else:
            command += ["-BaseUrl", self.url, "-NpcCsvPath", str(self.npcs)]
            command += ["-HotfixCachePath", str(hotfix)] if hotfix else ["-WithoutHotfixes"]
        run = subprocess.run(command + list(extra), capture_output=True, timeout=40)
        if success:
            self.assertEqual(run.returncode, 0, run.stderr.decode(errors="replace") + run.stdout.decode(errors="replace"))
        else:
            self.assertNotEqual(run.returncode, 0)
        return run

    def rows(self, filename, output=None):
        with ((output or self.output) / filename).open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))

    def test_chain_resolution_multiple_difficulties_missing_zero_and_conflicts(self):
        self.run_export()
        rows = {int(row["npc_id"]): row for row in self.rows("npc-factions.csv")}
        self.assertEqual(rows[100], {"npc_id": "100", "faction_id": "93", "status": "resolved",
            "faction_template_ids": "10;11", "creature_difficulty_ids": "1;2"})
        expected = {101: "conflict", 102: "missing-template", 103: "missing-faction", 104: "no-faction",
            105: "no-faction", 106: "missing-template", 107: "conflict", 108: "no-faction"}
        for npc, status in expected.items():
            self.assertEqual(rows[npc]["status"], status)
            self.assertEqual(rows[npc]["faction_id"], "")
        names = {int(row["ID"]): row for row in self.rows("factions.csv")}
        self.assertEqual(names[93]["Name_enUS"], 'Magram, "Clan"\nCentaur')
        self.assertEqual(names[93]["Name_zhCN"], "玛格拉姆半人马")
        self.assertEqual(names[92]["Name_zhTW"], "吉爾吉斯半人馬")
        manifest = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        actual_files = {str(p.relative_to(self.output)).replace("\\", "/") for p in self.output.rglob("*") if p.is_file()} - {"manifest.json"}
        self.assertEqual(set(manifest["files"]), actual_files)
        for relative, evidence in manifest["files"].items():
            content = (self.output / relative).read_bytes()
            self.assertEqual(evidence, {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)})
        for request in self.requests:
            query = parse_qs(urlparse(request).query)
            if "/dbc/export/?" in request:
                self.assertEqual(query["build"], [BUILD])
                self.assertEqual(query["useHotfixes"], ["false"])
                self.assertEqual(query["newLinesInStrings"], ["true"])
        self.assertFalse(any("reload" in request or "download" in request for request in self.requests))

    def test_requested_chinese_returning_english_db2_keeps_translation_empty(self):
        self.masks["zhTW"] = 1
        self.run_export()
        self.assertTrue(all(row["Name_zhTW"] == "" for row in self.rows("factions.csv")))
        manifest = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["localeEvidence"]["zhTW"]["verified"])
        self.assertTrue(manifest["localeEvidence"]["zhCN"]["verified"])

    def test_offline_replay_preserves_target_npcs_and_csv_bytes_without_http(self):
        self.run_export()
        replay = self.folder / "replay"
        requests = len(self.requests)
        self.run_export(output=replay, replay=self.output)
        self.assertEqual(len(self.requests), requests)
        for name in ("factions.csv", "npc-factions.csv"):
            self.assertEqual((self.output / name).read_bytes(), (replay / name).read_bytes())

    def test_tampered_snapshot_and_wrong_build_fail_without_output(self):
        self.run_export()
        manifest_path = self.output / 'manifest.json'
        original = manifest_path.read_bytes()
        manifest = json.loads(original)
        manifest['build'] = '1.60.1.70374'
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        replay = self.folder / 'wrong-build'
        self.run_export(output=replay, replay=self.output, success=False)
        self.assertFalse(replay.exists())
        manifest_path.write_bytes(original)
        raw = self.output / "raw/faction_enUS.csv"
        raw.write_bytes(raw.read_bytes() + b"\n")
        replay = self.folder / "tampered"
        self.run_export(output=replay, replay=self.output, success=False)
        self.assertFalse(replay.exists())

    def test_missing_columns_or_foreign_key_contract_do_not_publish(self):
        self.bad_header = True
        self.run_export(success=False)
        self.assertFalse(self.output.exists())

    def test_output_boundary_is_checked_before_http(self):
        outside = ROOT.parent / ('outside-' + self.folder.name)
        self.run_export(output=outside, success=False)
        self.assertFalse(outside.exists())
        self.assertEqual(self.requests, [])
        self.bad_header = False
        self.bad_fk = True
        self.run_export(success=False)
        self.assertFalse(self.output.exists())

    def test_invalid_values_and_duplicate_raw_ids_fail(self):
        self.data[("creaturedifficulty", "enUS")] = csv_bytes(self.headers["creaturedifficulty"], [[1, 100, -1]])
        self.run_export(success=False)
        self.assertFalse(self.output.exists())
        self.data[("creaturedifficulty", "enUS")] = csv_bytes(self.headers["creaturedifficulty"], [[1, 100, 10], [1, 100, 11]])
        self.run_export(success=False)

    def test_build_change_and_existing_destination_preserve_outputs(self):
        self.changed_build = True
        self.run_export(success=False)
        self.assertFalse(self.output.exists())
        self.output.mkdir()
        sentinel = self.output / "sentinel"
        sentinel.write_text("keep", encoding="utf-8")
        before = len(self.requests)
        self.run_export(success=False)
        self.assertEqual(len(self.requests), before)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_hotfix_build_is_validated_and_matching_cache_is_retained(self):
        cache = self.folder / "DBCache.bin"
        cache.write_bytes(b"XFTH" + struct.pack("<II", 9, 70374) + b"\0" * 32)
        self.run_export(hotfix=cache, success=False)
        self.assertEqual(self.requests, [])
        cache.write_bytes(b"XFTH" + struct.pack("<II", 9, 70450) + b"\0" * 32)
        self.run_export(hotfix=cache)
        manifest = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["hotfix"]["build"], 70450)
        self.assertFalse(manifest["hotfix"]["serverAttested"])
        self.assertEqual((self.output / "raw/DBCache.bin").read_bytes(), cache.read_bytes())
        for request in self.requests:
            if "/dbc/export/?" in request:
                self.assertEqual(parse_qs(urlparse(request).query)["useHotfixes"], ["true"])


if __name__ == "__main__":
    unittest.main()
