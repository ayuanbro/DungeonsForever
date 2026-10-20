"""Package the real runtime manifest in a temporary Windows checkout."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = Path(os.environ.get("SystemRoot", "C:/Windows")) / (
    "System32/WindowsPowerShell/v1.0/powershell.exe")
WINDOWS_PACKAGER_AVAILABLE = (
    os.name == "nt" and shutil.which("cmd.exe") is not None and POWERSHELL.is_file())
ASSET_SUFFIXES = {
    ".blp", ".tga", ".png", ".jpg", ".jpeg", ".dds", ".ttf", ".otf",
    ".ogg", ".mp3", ".wav", ".m2", ".skin", ".anim", ".wmo",
}


def runtime_files(root):
    """Resolve TOC/XML references independently of the BAT's PowerShell code."""
    files = set()

    def resolve(reference, directory):
        relative = Path(reference.replace("\\", "/"))
        if relative.is_absolute():
            raise AssertionError("Absolute runtime reference: " + reference)
        for base in (directory, root):
            candidate = (base / relative).resolve()
            if candidate.is_relative_to(root) and candidate.is_file():
                return candidate
        raise AssertionError("Missing runtime reference: " + reference)

    def add(path):
        if path in files:
            return
        files.add(path)
        if path.suffix.lower() == ".xml":
            for node in ET.parse(path).iter():
                if (node.tag.rsplit("}", 1)[-1] in ("Script", "Include")
                        and node.get("file")):
                    add(resolve(node.get("file"), path.parent))

    toc = root / "DungeonsForever.toc"
    add(toc)
    for line in toc.read_text(encoding="utf-8-sig").splitlines():
        reference = line.strip()
        if reference and not reference.startswith("#"):
            reference = re.sub(r"\s+\[.*\]\s*$", "", reference).strip()
            add(resolve(reference, root))
    add(root / "LICENSE")
    for path in (root / "Media").rglob("*"):
        if path.is_file() and path.suffix.lower() in ASSET_SUFFIXES:
            add(path)
    return files


@unittest.skipUnless(
    WINDOWS_PACKAGER_AVAILABLE,
    "requires Windows cmd.exe and the Windows PowerShell used by package_addon.bat")
class PackageProfPricesTests(unittest.TestCase):
    def test_real_manifest_packages_current_price_module_without_orphan_lua(self):
        source = ROOT.resolve()
        files = runtime_files(source)
        expected = {"DungeonsForever/" + path.relative_to(source).as_posix()
                    for path in files}
        module_entry = "DungeonsForever/Core/ProfItemPrices.lua"
        self.assertIn(module_entry, expected)

        with tempfile.TemporaryDirectory(prefix="df-package-prof-prices-") as directory:
            temporary = Path(directory).resolve()
            self.assertEqual(temporary.parent, Path(tempfile.gettempdir()).resolve())
            self.assertTrue(temporary.name.startswith("df-package-prof-prices-"))
            checkout = temporary / "runtime"
            caller = temporary / "different-cwd"
            checkout.mkdir()
            caller.mkdir()
            for path in files:
                destination = checkout / path.relative_to(source)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
            packager = checkout / "package_addon.bat"
            shutil.copy2(source / "package_addon.bat", packager)
            orphan = checkout / "Core/UnusedQuotation.lua"
            orphan.write_text("return {quotedPrice=1}\n", encoding="utf-8")

            result = subprocess.run(
                [shutil.which("cmd.exe"), "/d", "/c", str(packager), "--no-pause"],
                cwd=caller, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            archives = list(checkout.glob("DungeonsForever-*.zip"))
            self.assertEqual(len(archives), 1, result.stdout + result.stderr)
            self.assertEqual(list(caller.glob("*.zip")), [])
            with zipfile.ZipFile(archives[0]) as archive:
                names = archive.namelist()
                self.assertEqual(len(names), len(expected))
                self.assertEqual(set(names), expected)
                self.assertEqual(names.count(module_entry), 1)
                self.assertNotIn("DungeonsForever/Core/UnusedQuotation.lua", names)
                self.assertTrue(all(name.startswith("DungeonsForever/") for name in names))
                self.assertEqual(archive.read(module_entry),
                                 (source / "Core/ProfItemPrices.lua").read_bytes())
                self.assertEqual(archive.read("DungeonsForever/DungeonsForever.toc"),
                                 (source / "DungeonsForever.toc").read_bytes())
                self.assertIsNone(archive.testzip())
        self.assertFalse(temporary.exists(), "temporary checkout and ZIP were not removed")


if __name__ == "__main__":
    unittest.main()
