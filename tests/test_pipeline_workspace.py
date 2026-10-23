"""Disposable data workspaces preserve official bytes and repository boundaries."""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('prepare_workspace', ROOT / 'df-data-pipeline/prepare_workspace.py')
workspace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workspace)


def snapshot(directory):
    return {str(path.relative_to(directory)): (hashlib.sha256(path.read_bytes()).hexdigest(),
                                              path.stat().st_mtime_ns)
            for path in directory.rglob('*') if path.is_file()}


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        runtime = ROOT / '.pipeline-runtime'
        runtime.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='workspace-test-', dir=runtime)
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.source = self.base / 'source'
        self.source.mkdir()
        for name, content in [('Data_Example.lua', b'base\r\n\x00'),
                              ('enUS/Data_Example.lua', b'english\n'),
                              ('zhTW/Data_Example.lua', '繁體\r\n'.encode('utf-8'))]:
            path = self.source / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(content)
        self.target = self.base / 'review/Core/Data'

    def link_directory(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError as error:
            if os.name != 'nt':
                self.skipTest('directory links unavailable: %s' % error)
            result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)],
                                    capture_output=True)
            if result.returncode:
                self.skipTest('directory links unavailable: %s' % result.stderr)
        self.addCleanup(lambda: link.unlink() if link.is_symlink() else link.rmdir())

    def test_copies_full_official_tree_and_preserves_sources(self):
        source = ROOT / 'Core/Data'
        before = snapshot(source)
        self.assertEqual(workspace.prepare_workspace(self.target), len(before))
        self.assertEqual(snapshot(self.target), before)
        self.assertEqual(snapshot(source), before)
        self.assertTrue(any(name.startswith('enUS') for name in before))
        self.assertTrue(any(name.startswith('zhTW') for name in before))
        self.assertFalse((self.target / 'Data_VendorPrices.lua').exists())

    def test_existing_destination_is_never_overwritten(self):
        self.target.mkdir(parents=True)
        marker = self.target / 'mine.txt'
        marker.write_bytes(b'keep my output')
        before = snapshot(self.target)
        with self.assertRaisesRegex(workspace.WorkspaceError, 'already exists'):
            workspace.prepare_workspace(self.target, source=self.source)
        self.assertEqual(snapshot(self.target), before)

    def test_failed_copy_removes_only_the_new_workspace(self):
        before = snapshot(self.source)
        neighbor = self.base / 'review/keep.txt'
        neighbor.parent.mkdir()
        neighbor.write_bytes(b'keep')
        copy = workspace.shutil.copyfileobj
        calls = 0

        def fail_second(reader, writer):
            nonlocal calls
            calls += 1
            if calls == 2:
                writer.write(b'partial')
                raise OSError('injected copy failure')
            return copy(reader, writer)

        with patch.object(workspace.shutil, 'copyfileobj', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'injected copy failure'):
                workspace.prepare_workspace(self.target, source=self.source)
        self.assertFalse(self.target.exists())
        self.assertEqual(neighbor.read_bytes(), b'keep')
        self.assertEqual(snapshot(self.source), before)

    def test_outside_and_overlapping_paths_are_rejected(self):
        for target, source in [(ROOT.parent / 'forbidden-workspace', self.source),
                               (self.target, ROOT.parent),
                               (self.source / 'nested', self.source),
                               (self.base, self.source)]:
            with self.subTest(target=target, source=source):
                with self.assertRaises(workspace.WorkspaceError):
                    workspace.prepare_workspace(target, source=source)
        self.assertFalse(self.target.exists())

    def test_destination_junction_cannot_escape_repository(self):
        link = self.base / 'outside'
        self.link_directory(link, ROOT.parent)
        with self.assertRaises(workspace.WorkspaceError):
            workspace.prepare_workspace(link / 'forbidden-workspace', source=self.source)

    def test_link_inside_source_is_rejected_before_target_creation(self):
        self.link_directory(self.source / 'outside', ROOT.parent)
        with self.assertRaises(workspace.WorkspaceError):
            workspace.prepare_workspace(self.target, source=self.source)
        self.assertFalse(self.target.exists())

    def test_cli_failure_is_actionable_and_does_not_replace_output(self):
        self.target.mkdir(parents=True)
        with patch.object(workspace, 'DESTINATION', self.target):
            with patch('sys.stderr') as stderr:
                self.assertEqual(workspace.main([]), 2)
        self.assertIn('already exists', ''.join(call.args[0] for call in stderr.write.call_args_list))
        self.assertTrue(self.target.is_dir())


if __name__ == '__main__':
    unittest.main()
