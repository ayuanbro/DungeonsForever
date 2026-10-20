"""Verify the independent, hash-preserved professional-package migration history."""
import argparse
import json
from pathlib import Path
from fc_pipeline_common import HERE, PACKAGE, json_bytes, fingerprint, require_repo_path

MANIFEST = HERE / '_fc/maintenance/legacy-coverage.json'


def verify(manifest_path=MANIFEST, include_cache=True):
    manifest_path = require_repo_path(manifest_path)
    manifest = json.loads(manifest_path.read_bytes())
    checked, failures, skipped = [], [], []
    sources = set()
    for row in manifest['records']:
        if row['source'] in sources:
            raise ValueError('duplicate legacy source identity: %s' % row['source'])
        sources.add(row['source'])
        path = require_repo_path(PACKAGE / row['preservedAt'], PACKAGE)
        if not include_cache and row['status'] == 'immutable-cache-history':
            skipped.append(row['source'])
            continue
        if fingerprint(path) != row['sha256']:
            failures.append({'source': row['source'], 'path': row['preservedAt'],
                             'expected': row['sha256'], 'actual': fingerprint(path)})
        checked.append(row['source'])
    return {'schemaVersion': 1, 'sourcePackage': manifest['sourcePackage'],
            'checked': len(checked), 'skippedCaches': len(skipped), 'failures': failures,
            'excludedRebuildableBytecode': manifest['excludedRebuildableBytecode'],
            'readsOriginalPackage': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--without-caches', action='store_true', help='verify only history tracked with source')
    parser.add_argument('--output', type=Path, default=HERE / '_fc/reports/legacy-coverage.json')
    args = parser.parse_args(argv)
    result = verify(args.manifest, not args.without_caches)
    output = require_repo_path(args.output)
    if not output.is_relative_to(HERE / '_fc/reports'):
        raise ValueError('legacy audit output must be under pipeline reports')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(json_bytes(result))
    print('%d preserved files checked; %d failures; original package not read' %
          (result['checked'], len(result['failures'])))
    return int(bool(result['failures']))


if __name__ == '__main__':
    raise SystemExit(main())
