"""Repository-local paths for saving edits against the maintained route baseline."""
import os
from pathlib import Path
import stat

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
REPO = PACKAGE.parent


def checked(path):
    path = Path(os.path.abspath(path))
    if not path.is_relative_to(REPO) or not path.resolve().is_relative_to(REPO):
        raise ValueError('route path must stay inside the current repository: %s' % path)
    current = REPO
    for part in path.relative_to(REPO).parts:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('route paths must not contain symlinks or junctions: %s' % current)
    return path.as_posix()


ROOT = checked(PACKAGE)
TEMP = checked(HERE)
PLAN = checked(HERE / '_route_plan')


def require_workspace():
    for name in ('Data_MapPins.lua', 'Data_NPCLoc.lua', 'Data_DungeonQuests.lua'):
        path = checked(PACKAGE / 'Core/Data' / name)
        if not Path(path).is_file():
            raise ValueError('请先运行 python -B df-data-pipeline/prepare_workspace.py 准备工具数据工作区')
    for relative in ('_route_plan/tune.html', '_route_plan/data/index.json',
                     '_route_override.json', '_route_qicon_override.json',
                     '_route_qtip_override.json', '_route_qi_hide.json'):
        checked(HERE / relative)
