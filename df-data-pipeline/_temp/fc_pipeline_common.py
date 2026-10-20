"""Repository-local paths, Lua validation and compensated batch publication."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
REPO = PACKAGE.parent
LOCK_PATH = HERE / '_fc/cache/.pipeline-state/update.lock'
RUNTIME = REPO / '.pipeline-runtime/lib'
if RUNTIME.is_dir():
    sys.path.insert(0, str(RUNTIME))


class PipelineError(ValueError):
    pass


def require_repo_path(path, root=None):
    path = Path(path).expanduser().resolve()
    root = Path(root or REPO).resolve()
    if not path.is_relative_to(root):
        raise PipelineError('path must stay inside the current repository: %s' % path)
    return path


def configured_path(name, default):
    return str(require_repo_path(os.environ.get(name, default)))


def sha(content):
    return hashlib.sha256(content).hexdigest()


def fingerprint(path):
    path = Path(path)
    return sha(path.read_bytes()) if path.is_file() else None


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def ensure_unchanged(expected):
    for path, digest in expected.items():
        if fingerprint(path) != digest:
            raise PipelineError('file changed during update: %s' % path)


@contextmanager
def update_lock(lock_path=None):
    path = require_repo_path(lock_path or LOCK_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_nlink > 1:
        raise PipelineError('update lock must not be a hard link')
    with path.open('a+b') as stream:
        stream.seek(0, os.SEEK_END)
        if not stream.tell():
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise PipelineError('another data pipeline update is running') from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def publish_batch(outputs, expected=None):
    """Prepare every replacement, then commit; keep recoverable originals on failure."""
    checked = {}
    for destination, content in outputs.items():
        path = require_repo_path(destination)
        if path in checked:
            raise PipelineError('duplicate publication destination: %s' % path)
        if path.exists() and not path.is_file():
            raise PipelineError('publication destination is not a file: %s' % path)
        checked[path] = bytes(content)
    for i, path in enumerate(checked):
        for other in list(checked)[:i]:
            if path.exists() and other.exists() and os.path.samefile(path, other):
                raise PipelineError('publication paths alias one file: %s / %s' % (path, other))
    observed = dict(expected or {})
    for path in checked:
        observed.setdefault(path, fingerprint(path))
    ensure_unchanged(observed)
    changed = {p: b for p, b in checked.items() if fingerprint(p) != sha(b)}
    if not changed:
        return []
    backup = require_repo_path(REPO / '.implementation-backup' / ('pipeline-publish-' + uuid.uuid4().hex))
    backup.mkdir(parents=True)
    staged, originals, committed = {}, {}, []
    try:
        for i, (path, content) in enumerate(changed.items()):
            path.parent.mkdir(parents=True, exist_ok=True)
            original = path.read_bytes() if path.exists() else None
            originals[path] = original
            if original is not None:
                (backup / ('%04d.bin' % i)).write_bytes(original)
            with tempfile.NamedTemporaryFile(prefix='.df-publish-', suffix='.tmp', dir=path.parent,
                                             delete=False) as stream:
                staged[path] = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        (backup / 'manifest.json').write_bytes(json_bytes({
            'files': [{'path': str(p.relative_to(REPO)), 'backup': '%04d.bin' % i,
                       'existed': originals[p] is not None, 'before': observed[p], 'after': sha(changed[p])}
                      for i, p in enumerate(changed)]}))
        ensure_unchanged(observed)
        for path, temporary in staged.items():
            require_repo_path(path)
            if fingerprint(path) != observed[path]:
                raise PipelineError('destination changed during publication: %s' % path)
            os.replace(temporary, path)
            committed.append(path)
        (backup / 'complete').write_text('committed\n', encoding='utf-8')
        return list(changed)
    except BaseException as error:
        failed = []
        for path in reversed(committed):
            try:
                require_repo_path(path)
                if fingerprint(path) != sha(changed[path]):
                    raise PipelineError('destination changed after replacement')
                if originals[path] is None:
                    path.unlink(missing_ok=True)
                else:
                    with tempfile.NamedTemporaryFile(prefix='.df-restore-', suffix='.tmp',
                                                     dir=path.parent, delete=False) as stream:
                        restore = Path(stream.name)
                        stream.write(originals[path])
                    os.replace(restore, path)
            except BaseException as rollback_error:
                failed.append('%s: %s' % (path, rollback_error))
        (backup / 'failure.json').write_bytes(json_bytes({'error': str(error), 'rollbackErrors': failed}))
        if failed:
            raise PipelineError('publication failed; recovery needed using %s: %s' % (backup, '; '.join(failed))) from error
        raise
    finally:
        for temporary in staged.values():
            if temporary.exists():
                temporary.unlink()


def lua_runtime():
    try:
        from lupa.lua51 import LuaRuntime
    except ImportError:
        # Existing local test runtime is a read-only dependency, never an output.
        for path in (Path.home() / 'AppData/Local/Temp/df-lua-runtime',):
            if path.is_dir():
                sys.path.insert(0, str(path))
        try:
            from lupa.lua51 import LuaRuntime
        except ImportError as error:
            raise PipelineError('Lua 5.1 validation requires lupa.lua51; install dependencies in .pipeline-runtime/lib') from error
    return LuaRuntime(unpack_returned_tuples=True)


def lua_value(value):
    if hasattr(value, 'items'):
        pairs = [(k, v) for k, v in value.items() if hasattr(v, 'items') or not callable(v)]
        if pairs and all(isinstance(k, (int, float)) and k == int(k) and k > 0 for k, _ in pairs):
            keys = {int(k) for k, _ in pairs}
            if keys == set(range(1, len(pairs) + 1)):
                return [lua_value(value[i]) for i in range(1, len(pairs) + 1)]
        return {k: lua_value(v) for k, v in pairs}
    return value


def raw_namespace(paths, locale='zhCN'):
    lua = lua_runtime()
    lua.globals().__pipeline_locale = locale
    lua.execute('function GetLocale() return __pipeline_locale end; function GetBuildInfo() return "1.60.1", "70338", "", 16000 end')
    ns = lua.table()
    ns.IsForever = True
    ns.LoadForeverPages = True
    execute = lua.eval('function(source, name, ns) local f,e=loadstring(source,name); if not f then error(e) end; return f("DungeonsForever",ns) end')
    for path in paths:
        if isinstance(path, tuple):
            name, content = path
            source = content.decode('utf-8-sig') if isinstance(content, bytes) else content
        else:
            name = str(path)
            source = Path(path).read_text(encoding='utf-8-sig')
        try:
            execute(source, str(name), ns)
        except Exception as error:
            raise PipelineError('Lua validation failed in %s: %s' % (name, error)) from error
    if ns.EnsureProfRecipes is not None:
        ns.EnsureProfRecipes()
    return lua, ns


def load_namespace(paths, locale='zhCN'):
    _, ns = raw_namespace(paths, locale)
    return lua_value(ns)
