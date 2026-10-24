"""Build an installable addon ZIP using validated in-memory data overrides."""
import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from fc_pipeline_common import REPO, PipelineError, fingerprint, require_repo_path, sha, ensure_unchanged

ASSETS = {'.blp', '.tga', '.png', '.jpg', '.jpeg', '.dds', '.ttf', '.otf',
          '.ogg', '.mp3', '.wav', '.m2', '.skin', '.anim', '.wmo'}


def runtime_files(root=None, snapshots=None, generated=None):
    root = require_repo_path(root or REPO)
    files = set()
    snapshots = {} if snapshots is None else snapshots
    generated = set(generated or ())

    def resolve(reference, directory):
        relative = Path(reference.replace('\\', '/'))
        if relative.is_absolute() or ':' in reference:
            raise PipelineError('absolute runtime reference: %s' % reference)
        for base in (directory, root):
            candidate = require_repo_path(base / relative, root)
            if candidate.is_file() or candidate in generated:
                return candidate
        raise PipelineError('missing runtime reference: %s' % reference)

    def add(path):
        path = require_repo_path(path, root)
        if not path.is_file() and path not in generated:
            raise PipelineError('missing package file: %s' % path)
        if path in files:
            return
        files.add(path)
        snapshots[path] = path.read_bytes() if path.is_file() else None
        if path.suffix.lower() == '.xml':
            for node in ET.fromstring(snapshots[path]).iter():
                if node.tag.rsplit('}', 1)[-1] in ('Include', 'Script') and node.get('file'):
                    add(resolve(node.get('file'), path.parent))

    toc = root / 'DungeonsForever.toc'
    add(toc)
    for line in snapshots[toc].decode('utf-8-sig').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            add(resolve(re.sub(r'\s+\[.*\]\s*$', '', line).strip(), root))
    add(root / 'LICENSE')
    media = require_repo_path(root / 'Media', root)
    if not media.is_dir():
        raise PipelineError('Media directory is missing')
    for path in media.rglob('*'):
        if path.is_file() and path.suffix.lower() in ASSETS:
            add(path)
    return sorted(files)


def build_install_zip(destination, overrides, expected=None):
    """Package validated data without replacing any checkout runtime file.

    Snapshot all other runtime bytes, verify their hashes after compression,
    then check every archive entry's bytes and CRC before creating the final ZIP.
    """
    destination = require_repo_path(destination)
    if destination.suffix.lower() != '.zip' or destination.exists():
        raise PipelineError('ZIP destination must be a new .zip file: %s' % destination)
    base = tuple('Data_%s.lua' % name for name in ('Professions', 'ProfRecipes', 'ProfLeveling',
                                                 'ProfGathering', 'ProfVendors', 'ProfTrainers'))
    allowed = {REPO / 'Core/Data' / name for name in base + ('Data_ProfItems.lua', 'Data_ProfSpecializations.lua',
                                                            'Data_ProfMaterialSupply.lua')}
    allowed.update(REPO / 'Core/Data' / locale / name for locale in ('enUS', 'zhTW') for name in base)
    snapshots = {}
    files = runtime_files(snapshots=snapshots, generated=allowed & overrides.keys())
    source_hashes = {}
    contents = {}
    for path in files:
        original = snapshots[path]
        source_hashes[path] = sha(original) if original is not None else None
        if expected is not None and path in expected and source_hashes[path] != expected[path]:
            raise PipelineError('runtime input changed before packaging: %s' % path)
        contents['DungeonsForever/' + path.relative_to(REPO).as_posix()] = overrides.get(path, original)
    invalid = sorted(set(overrides) & set(files) - allowed)
    if invalid:
        raise PipelineError('package override is outside profession data: %s' % invalid[0])
    omitted = {p for p in overrides if p in allowed and p not in files}
    if omitted:
        raise PipelineError('profession data override is absent from runtime manifest: %s' % sorted(omitted)[0])
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.df-preview-', suffix='.zip', dir=destination.parent,
                                         delete=False) as stream:
            temporary = Path(stream.name)
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, content in contents.items():
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, content)
        for path, digest in source_hashes.items():
            if fingerprint(path) != digest:
                raise PipelineError('runtime input changed during packaging: %s' % path)
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() or set(archive.namelist()) != set(contents) or len(archive.namelist()) != len(contents):
                raise PipelineError('installation ZIP manifest/CRC validation failed')
            for name, content in contents.items():
                if archive.read(name) != content:
                    raise PipelineError('installation ZIP bytes differ: %s' % name)
        # Exclusive creation prevents replacing an unrelated or concurrent ZIP.
        ensure_unchanged(expected or {})
        os.link(temporary, destination)
        return {'path': str(destination.relative_to(REPO)).replace('\\', '/'),
                'sha256': fingerprint(destination), 'files': len(contents),
                'bytes': destination.stat().st_size, 'published': False,
                'dataOverrides': [p.relative_to(REPO).as_posix() for p in sorted(allowed & overrides.keys())]}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
