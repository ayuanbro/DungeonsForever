"""Offline reclassification of immutable, checksum-verified response bytes."""
import collections
import copy
import json
from pathlib import Path

from .fetch import checkpoint, now, update_web_run
from .model import checked_bytes, parse_page, sha256


def reparse(raw, report):
    raw, report = Path(raw).resolve(), Path(report).resolve()
    path = raw / "manifest.json"
    original = path.read_bytes()
    manifest = json.loads(original)
    records = {r['key']: r for r in manifest['responses']}
    run = manifest['webRun']
    pending = [key for key in run['targets'] if records.get(key, {}).get('webRunID') != run['id']
               or records.get(key, {}).get('attempted') is not True]
    audit = {'schema': 1, 'offline': True, 'build': manifest['build'], 'parsedAt': now(),
             'originalManifestSHA256': sha256(original), 'pendingBefore': pending,
             'pendingPriorStates': dict(collections.Counter(records.get(k, {}).get('status', 'absent') for k in pending)),
             'changes': [], 'remainingErrors': []}
    # Validate every referenced byte before publishing any changed metadata.
    from .fetch import response_evidence
    for index, record in enumerate(response_evidence(manifest['responses'])):
        if 'path' in record:
            checked_bytes(raw, record)
        if index % 1000 == 0:
            print(f'verifying response {index}', flush=True)
    for record in manifest['responses']:
        if not record['key'].startswith('web:') or record.get('status') != 'parseError' or not record.get('path'):
            continue
        _, kind, entity = record['key'].split(':')
        before = copy.deepcopy(record)
        try:
            parsed = parse_page(checked_bytes(raw, record), kind, int(entity), record['finalUrl'])
            record['status'] = 'verified'
            record['entity'] = {'kind': kind, 'id': int(entity), 'title': parsed['title']}
            record.pop('error', None)
            record.pop('errorCode', None)
        except ValueError as error:
            record['status'], record['error'] = 'parseError', str(error)
            audit['remainingErrors'].append({'key': record['key'], 'error': str(error)})
        if record != before:
            audit['changes'].append({'key': record['key'], 'before': before['status'], 'after': record['status'],
                                     'previousError': before.get('error'), 'error': record.get('error')})
    targets = {(k.split(':')[1], int(k.split(':')[2])) for k in run['targets']}
    update_web_run(manifest, targets, records)
    manifest['sourceCoverageComplete'] = manifest['requestCoverageComplete'] and all(r['status'] == 'verified' for r in records.values())
    audit['statusesAfter'] = dict(collections.Counter(r['status'] for r in records.values() if r['key'].startswith('web:')))
    backup = raw / ('manifest.before-reparse.' + sha256(original) + '.json')
    if not backup.exists():
        backup.write_bytes(original)
    report.parent.mkdir(parents=True, exist_ok=True)
    checkpoint(report, audit)
    checkpoint(path, manifest)
    return audit
