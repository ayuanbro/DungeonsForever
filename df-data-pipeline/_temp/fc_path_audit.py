"""Inventory fixed filesystem paths without executing historical tools."""
import argparse
import json
from pathlib import Path
import re
from fc_pipeline_common import HERE, PACKAGE, REPO, json_bytes, require_repo_path

ACTIVE = {
    'fc_update.py', 'fc_pipeline.py', 'fc_pipeline_common.py', 'fc_gen.py', 'fc_maintenance.py',
    'fc_locales.py', 'fc_fetch.py', 'fc_parse.py', 'fc_zones.py', 'fc_fields.py', 'fc_i18n.py',
    'gen_enus_data.py', 'gen_zhtw_data.py', 'gen_zhtw.py', 'strip_comments.py',
    'fc_prof_items.py', 'fc_prof_specializations.py', 'fc_refresh_specializations.py',
    'fc_specialization_fetch.py', 'fc_recipe_item_audit.py', 'fc_recipe_item_web_audit.py',
    'fc_recipe_catalog_fetch.py', 'fc_path_audit.py', 'fc_pipeline_paths.py', 'fc_package.py', 'fc_legacy_audit.py',
}
DRIVE = re.compile(r'(?<![A-Za-z0-9_])[A-Za-z]:[\\/][^\r\n\"\'<>]*')


def inventory():
    findings = []
    roots = [PACKAGE, REPO / 'df-prof-pipeline-v1.0', REPO / 'scripts', REPO / 'tests']
    for root in roots:
        for path in sorted(root.rglob('*')):
            if path.suffix.lower() not in ('.py', '.ps1', '.bat', '.md') or not path.is_file():
                continue
            if any(part in ('__pycache__', 'cache', 'reports', '.implementation-backup') for part in path.parts):
                continue
            relative = str(path.relative_to(REPO)).replace('\\', '/')
            active = path.parent == HERE and path.name in ACTIVE
            category = 'active' if active else 'archived' if 'df-prof-pipeline-v1.0' in relative else 'historical' if path.is_relative_to(PACKAGE) else 'support'
            for number, line in enumerate(path.read_text(encoding='utf-8-sig', errors='replace').splitlines(), 1):
                for match in DRIVE.finditer(line):
                    comment = line.lstrip().startswith(('#', '--', '*', '"""', 'r"""'))
                    findings.append({'file': relative, 'line': number, 'path': match.group(0).strip(),
                                     'category': category, 'comment': comment,
                                     'actionable': active and not comment})
    return {'schemaVersion': 1, 'fixedPaths': findings,
            'activeFailures': [item for item in findings if item['actionable']]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / '_fc/reports/path-audit.json')
    args = parser.parse_args(argv)
    destination = require_repo_path(args.output)
    result = inventory()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(json_bytes(result))
    print('%d fixed-path references; %d active failures; %s' % (len(result['fixedPaths']), len(result['activeFailures']), destination))
    return 1 if result['activeFailures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
