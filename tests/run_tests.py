"""Run the complete suite with repository-local dependencies and temporary files."""
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.pipeline-runtime/lib'
TEMPORARY = ROOT / '.pipeline-runtime/tmp'
TEMPORARY.mkdir(parents=True, exist_ok=True)
os.environ['TEMP'] = os.environ['TMP'] = os.environ['TMPDIR'] = str(TEMPORARY)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['PYTHONPATH'] = str(RUNTIME) + os.pathsep + os.environ.get('PYTHONPATH', '')
sys.dont_write_bytecode = True
sys.path.insert(0, str(RUNTIME))
# Some historical tests prepend an older interpreter-specific dependency path.
# Load the current interpreter's extension before those helpers are imported.
from lupa.lua51 import LuaRuntime
from opencc import OpenCC

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
