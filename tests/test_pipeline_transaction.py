"""Exercise batch publication and locking in an isolated repository directory."""
import json
import os
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


class TransactionTests(unittest.TestCase):
    def setUp(self):
        temporary_root = ROOT / ".pipeline-runtime/tmp"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="transaction-", dir=temporary_root)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
        self.assertTrue(self.directory.is_relative_to(temporary_root.resolve()))
        self.repo = self.directory / "repo"
        self.repo.mkdir()
        self.outside = self.directory / "outside"
        self.outside.mkdir()
        self.addCleanup(patch.stopall)
        patch.object(common, "REPO", self.repo).start()
        patch.object(common, "LOCK_PATH", self.repo / "_cache/update.lock").start()

    def file(self, relative, content):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def backups(self):
        return sorted((self.repo / ".implementation-backup").glob("pipeline-publish-*"))

    def manifest(self):
        backups = self.backups()
        self.assertEqual(len(backups), 1)
        return backups[0], json.loads((backups[0] / "manifest.json").read_text(encoding="utf-8"))

    def test_multi_file_commit_records_originals_and_new_targets(self):
        first = self.file("Core/Data/Data_A.lua", b"old A\r\n")
        second = self.file("Core/Data/enUS/Data_A.lua", b"old English\n")
        new = self.repo / "Core/Data/zhTW/Data_A.lua"
        outputs = {first: b"new A\n", second: b"new English\n", new: b"new Traditional\n"}
        changed = common.publish_batch(outputs, expected={first: common.sha(first.read_bytes()),
                                                         second: common.sha(second.read_bytes()), new: None})
        self.assertEqual(changed, list(outputs))
        for path, content in outputs.items():
            self.assertEqual(path.read_bytes(), content)
        backup, manifest = self.manifest()
        self.assertEqual((backup / "0000.bin").read_bytes(), b"old A\r\n")
        self.assertEqual((backup / "0001.bin").read_bytes(), b"old English\n")
        self.assertFalse((backup / "0002.bin").exists())
        self.assertEqual([entry["existed"] for entry in manifest["files"]], [True, True, False])
        self.assertEqual(manifest["files"][2]["before"], None)
        self.assertEqual((backup / "complete").read_text(encoding="utf-8"), "committed\n")
        self.assertEqual(list(self.repo.rglob(".df-publish-*.tmp")), [])

    def test_unchanged_batch_preserves_mtime_and_creates_no_backup(self):
        path = self.file("Core/Data/Data_A.lua", b"same content\r\n")
        timestamp = 1_650_000_000_123_456_700
        os.utime(path, ns=(timestamp, timestamp))
        before = path.stat().st_mtime_ns
        self.assertEqual(common.publish_batch({path: path.read_bytes()}), [])
        self.assertEqual(path.stat().st_mtime_ns, before)
        self.assertFalse((self.repo / ".implementation-backup").exists())

    def test_replace_failure_restores_every_committed_existing_file(self):
        first = self.file("Core/Data/Data_A.lua", b"old A")
        second = self.file("Core/Data/enUS/Data_A.lua", b"old English")
        new = self.repo / "Core/Data/zhTW/Data_A.lua"
        replace = os.replace
        def fail_second(source, destination):
            if Path(destination) == second and Path(source).name.startswith(".df-publish-"):
                raise OSError("injected publish failure")
            return replace(source, destination)
        with patch.object(common.os, "replace", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "injected publish failure"):
                common.publish_batch({first: b"new A", second: b"new English", new: b"new Traditional"})
        self.assertEqual(first.read_bytes(), b"old A")
        self.assertEqual(second.read_bytes(), b"old English")
        self.assertFalse(new.exists())
        backup, _ = self.manifest()
        failure = json.loads((backup / "failure.json").read_text(encoding="utf-8"))
        self.assertEqual(failure["rollbackErrors"], [])
        self.assertFalse((backup / "complete").exists())
        self.assertEqual(list(self.repo.rglob(".df-publish-*.tmp")), [])

    def test_replace_failure_removes_a_new_file_committed_before_failure(self):
        new = self.repo / "Core/Data/Data_A.lua"
        second = self.file("Core/Data/enUS/Data_A.lua", b"old English")
        replace = os.replace
        def fail_second(source, destination):
            if Path(destination) == second and Path(source).name.startswith(".df-publish-"):
                raise OSError("injected publish failure")
            return replace(source, destination)
        with patch.object(common.os, "replace", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "injected publish failure"):
                common.publish_batch({new: b"new A", second: b"new English"}, expected={new: None})
        self.assertFalse(new.exists())
        self.assertEqual(second.read_bytes(), b"old English")

    def test_rollback_failure_keeps_recoverable_originals_and_manifest(self):
        first = self.file("Core/Data/Data_A.lua", b"recover this original")
        second = self.file("Core/Data/enUS/Data_A.lua", b"old English")
        replace = os.replace
        def fail_publication_and_rollback(source, destination):
            name = Path(source).name
            if Path(destination) == second and name.startswith(".df-publish-"):
                raise OSError("injected publish failure")
            if Path(destination) == first and name.startswith(".df-restore-"):
                raise OSError("injected rollback failure")
            return replace(source, destination)
        with patch.object(common.os, "replace", side_effect=fail_publication_and_rollback):
            with self.assertRaisesRegex(common.PipelineError, "recovery needed") as caught:
                common.publish_batch({first: b"new A", second: b"new English"})
        self.assertEqual(first.read_bytes(), b"new A")
        self.assertEqual(second.read_bytes(), b"old English")
        backup, manifest = self.manifest()
        self.assertIn(str(backup), str(caught.exception))
        original = manifest["files"][0]
        self.assertEqual((backup / original["backup"]).read_bytes(), b"recover this original")
        self.assertEqual(original["before"], common.sha(b"recover this original"))
        self.assertEqual(original["after"], common.sha(b"new A"))
        failure = json.loads((backup / "failure.json").read_text(encoding="utf-8"))
        self.assertEqual(len(failure["rollbackErrors"]), 1)
        self.assertIn("injected rollback failure", failure["rollbackErrors"][0])
        self.assertFalse((backup / "complete").exists())

    def test_expected_missing_target_rejects_concurrent_creation_before_staging(self):
        path = self.repo / "Core/Data/new.lua"
        snapshot = {path: None}
        path.parent.mkdir(parents=True)
        path.write_bytes(b"concurrent external content")
        with self.assertRaisesRegex(common.PipelineError, "file changed during update"):
            common.publish_batch({path: b"pipeline output"}, expected=snapshot)
        self.assertEqual(path.read_bytes(), b"concurrent external content")
        self.assertFalse((self.repo / ".implementation-backup").exists())

    def test_expected_missing_target_rejects_creation_during_commit(self):
        first = self.file("Core/Data/Data_A.lua", b"old A")
        new = self.repo / "Core/Data/enUS/new.lua"
        replace = os.replace
        def create_target_after_first_replace(source, destination):
            result = replace(source, destination)
            if Path(destination) == first and Path(source).name.startswith(".df-publish-"):
                new.write_bytes(b"concurrent external content")
            return result
        with patch.object(common.os, "replace", side_effect=create_target_after_first_replace):
            with self.assertRaisesRegex(common.PipelineError, "destination changed during publication"):
                common.publish_batch({first: b"new A", new: b"new English"}, expected={new: None})
        self.assertEqual(first.read_bytes(), b"old A")
        self.assertEqual(new.read_bytes(), b"concurrent external content")
        backup, _ = self.manifest()
        failure = json.loads((backup / "failure.json").read_text(encoding="utf-8"))
        self.assertEqual(failure["rollbackErrors"], [])

    def test_outside_path_rejected_before_any_output_directories_are_created(self):
        valid = self.repo / "not-created/Data_A.lua"
        invalid = self.outside / "also-not-created/Data_A.lua"
        with self.assertRaisesRegex(common.PipelineError, "inside the current repository"):
            common.publish_batch({valid: b"valid", invalid: b"invalid"})
        self.assertFalse(valid.parent.exists())
        self.assertFalse(invalid.parent.exists())
        self.assertFalse((self.repo / ".implementation-backup").exists())

    def test_link_to_outside_rejected_before_any_output_is_created(self):
        link = self.repo / "linked-data"
        try:
            link.symlink_to(self.outside, target_is_directory=True)
        except OSError as error:
            if os.name != "nt":
                self.skipTest("Directory symlinks unavailable: " + str(error))
            # Junctions need no Developer Mode privilege on Windows.
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(self.outside)],
                                    capture_output=True, timeout=10,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode:
                self.skipTest("Neither directory symlinks nor junctions are available")
        invalid = link / "not-created/Data_A.lua"
        with self.assertRaisesRegex(common.PipelineError, "inside the current repository"):
            common.publish_batch({invalid: b"invalid"})
        self.assertFalse((self.outside / "not-created").exists())
        self.assertFalse((self.repo / ".implementation-backup").exists())

    def test_another_process_cannot_acquire_the_update_lock(self):
        lock = self.repo / "_cache/update.lock"
        code = "\n".join([
            "import sys", "from pathlib import Path",
            "sys.path.insert(0, sys.argv[1])", "import fc_pipeline_common as common",
            "common.REPO = Path(sys.argv[2])",
            "with common.update_lock(Path(sys.argv[3])):", "    print('acquired')",
        ])
        command = [sys.executable, "-c", code, str(TOOLS), str(self.repo), str(lock)]
        kwargs = dict(capture_output=True, text=True, encoding="utf-8", timeout=10,
                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        with common.update_lock(lock):
            refused = subprocess.run(command, **kwargs)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("another data pipeline update is running", refused.stderr)
        self.assertNotIn("acquired", refused.stdout)
        released = subprocess.run(command, **kwargs)
        self.assertEqual(released.returncode, 0, released.stderr)
        self.assertIn("acquired", released.stdout)

    def test_lock_path_outside_repository_is_rejected_before_creation(self):
        path = self.outside / "not-created/update.lock"
        with self.assertRaisesRegex(common.PipelineError, "inside the current repository"):
            with common.update_lock(path):
                self.fail("Outside lock should not be acquired")
        self.assertFalse(path.parent.exists())


if __name__ == "__main__":
    unittest.main()
