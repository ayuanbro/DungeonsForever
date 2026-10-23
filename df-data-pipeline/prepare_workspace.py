"""Copy official data into a fresh, disposable workspace for standalone tools."""
import argparse
import os
from pathlib import Path
import shutil
import stat
import sys


PACKAGE = Path(__file__).resolve().parent
REPO = PACKAGE.parent
SOURCE = REPO / 'Core/Data'
DESTINATION = PACKAGE / 'Core/Data'


class WorkspaceError(ValueError):
    pass


def checked_path(value):
    """Keep both the lexical path and every existing ancestor in this checkout."""
    path = Path(os.path.abspath(Path(value).expanduser()))
    if not path.is_relative_to(REPO) or not path.resolve().is_relative_to(REPO):
        raise WorkspaceError('path must stay inside the current repository: %s' % path)
    current = REPO
    for part in path.relative_to(REPO).parts:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise WorkspaceError('workspace paths must not contain symlinks or junctions: %s' % current)
    return path


def source_files(source):
    files = []

    def fail(error):
        raise error

    for directory, directories, filenames in os.walk(source, followlinks=False, onerror=fail):
        checked_path(directory)
        for name in directories:
            checked_path(Path(directory) / name)
        for name in filenames:
            path = checked_path(Path(directory) / name)
            if not path.is_file():
                raise WorkspaceError('source must contain only regular files: %s' % path)
            files.append(path)
    return sorted(files)


def remove_created_workspace(destination, identity):
    """Never follow a substituted directory or link when rolling back a failed copy."""
    checked_path(destination)
    info = destination.stat()
    if (info.st_dev, info.st_ino) != identity:
        raise WorkspaceError('workspace changed during copying; refusing cleanup: %s' % destination)
    source_files(destination)  # Validate the whole tree before recursive removal.
    shutil.rmtree(destination)


def prepare_workspace(destination=None, *, source=None):
    """Return the number of copied files; refuse any existing destination.

    Overrides are useful for repository-local tests and review workspaces. They
    cannot escape this checkout or overlap the read-only source tree.
    """
    source = checked_path(source if source is not None else SOURCE)
    destination = checked_path(destination if destination is not None else DESTINATION)
    if not source.is_dir():
        raise WorkspaceError('source data directory is missing: %s' % source)
    if source.is_relative_to(destination) or destination.is_relative_to(source):
        raise WorkspaceError('source and destination must not overlap')
    if destination.exists():
        raise WorkspaceError('destination already exists; choose a fresh workspace: %s' % destination)
    files = source_files(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    checked_path(destination)
    destination.mkdir()  # A competing creator must fail without any cleanup.
    info = destination.stat()
    identity = (info.st_dev, info.st_ino)
    try:
        for original in files:
            original = checked_path(original)
            target = checked_path(destination / original.relative_to(source))
            target.parent.mkdir(parents=True, exist_ok=True)
            checked_path(target)
            with original.open('rb') as reader, target.open('xb') as writer:
                shutil.copyfileobj(reader, writer)
            shutil.copystat(original, target, follow_symlinks=False)
    except BaseException:
        remove_created_workspace(destination, identity)
        raise
    return len(files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        count = prepare_workspace()
    except (OSError, WorkspaceError) as error:
        print('prepare_workspace: %s' % error, file=sys.stderr)
        return 2
    print('Prepared %d files in %s' % (count, DESTINATION))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
