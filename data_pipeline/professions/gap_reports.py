"""Export readable gap lists from fresh audits; never a generation input."""
import argparse
import csv
import json
from pathlib import Path


def export(audit_path, source_output, learning_output, reuse_report=None):
    audit = json.loads(Path(audit_path).read_text(encoding='utf8'))
    uncovered = None
    if reuse_report is not None:
        reuse = json.loads(Path(reuse_report).read_text(encoding='utf8'))
        if reuse['build'] != audit['build'] or reuse['webRunID'] != audit['acquisition']['id']:
            raise ValueError('gap reports belong to different acquisitions')
        uncovered = {row['key'] for row in reuse['notNewlyRequestedAndNotReused']}
    source_output, learning_output = Path(source_output), Path(learning_output)
    if source_output.suffix.lower() != '.csv' or learning_output.suffix.lower() != '.csv':
        raise ValueError('gap reports must be CSV files; refusing to overwrite source or Lua files')
    if source_output.resolve() == learning_output.resolve():
        raise ValueError('source and learning gap outputs must differ')
    fields = ('key', 'status', 'httpStatus', 'error', 'url', 'finalUrl', 'webRunID', 'notNewlyRequestedAndNotReused')
    source_output.parent.mkdir(parents=True, exist_ok=True)
    learning_output.parent.mkdir(parents=True, exist_ok=True)
    with source_output.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in audit['sourceGaps']:
            writer.writerow({**{key: row.get(key, '') for key in fields},
                'notNewlyRequestedAndNotReused': row['key'] in uncovered if uncovered is not None else ''})
    with learning_output.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=('profession', 'spell', 'coverage', 'missingReasons', 'paths'))
        writer.writeheader()
        for row in audit['gaps']:
            writer.writerow({'profession': row['profession'], 'spell': row['spell'], 'coverage': row['coverage'],
                'missingReasons': ';'.join(row['missingReasons']),
                'paths': ';'.join(path['id'] + '=' + path['status'] for path in row['paths'])})
    return {'sourceGaps': len(audit['sourceGaps']), 'learningGaps': len(audit['gaps'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--source-output', type=Path, required=True)
    parser.add_argument('--learning-output', type=Path, required=True)
    parser.add_argument('--reuse-report', type=Path)
    args = parser.parse_args()
    print(export(args.audit, args.source_output, args.learning_output, args.reuse_report))
