"""Accept same-build verified raw observations without altering request history."""
from collections import Counter
import json
from pathlib import Path

from .fetch import accepted_reuse, checkpoint, now, update_web_run
from .model import PRODUCT, SourceError, checked_bytes, load_tables, parse_page, sha256


def reuse_verified(raw, report):
    raw, report = Path(raw).resolve(), Path(report).resolve()
    path = raw / 'manifest.json'
    if report == path or report.is_relative_to(raw / 'responses'):
        raise SourceError('reuse report must not overwrite raw response evidence or manifest')
    original = path.read_bytes()
    manifest = json.loads(original)
    build = manifest.get('buildInfo', {})
    after = manifest.get('latestAfter', {})
    if (manifest.get('product') != PRODUCT or not manifest.get('fetchComplete')
            or build.get('version') != manifest.get('build') or not build.get('build_config')
            or (build.get('version'), build.get('build_config')) != (after.get('version'), after.get('build_config'))):
        raise SourceError('reuse requires a closed same-build snapshot with final build verification')
    load_tables(raw, manifest)
    run = manifest['webRun']
    records = {r['key']: r for r in manifest['responses']}
    entries = {}
    for key in run['targets']:
        record = records.get(key, {})
        if record.get('webRunID') == run['id'] or record.get('status') != 'verified':
            continue
        if not record.get('webRunID') or not record.get('fetchedAt'):
            continue
        _, kind, entity = key.split(':')
        parse_page(checked_bytes(raw, record), kind, int(entity), record['finalUrl'])
        entries[key] = {'sha256': record['sha256'], 'sourceWebRunID': record['webRunID']}
    run['reuse'] = {'policy': 'same-build-verified-v1', 'build': manifest['build'],
                    'buildConfig': build['build_config'], 'acceptedAt': now(), 'records': entries}
    targets = {(key.split(':')[1], int(key.split(':')[2])) for key in run['targets']}
    update_web_run(manifest, targets, records)
    gaps, uncovered = [], []
    for key in run['targets']:
        record = records.get(key, {})
        row = {field: record.get(field) for field in ('key', 'status', 'httpStatus', 'url', 'finalUrl', 'error', 'path', 'sha256', 'webRunID', 'fetchedAt')}
        row['key'] = key
        if record.get('status') != 'verified':
            gaps.append(row)
        if not (record.get('webRunID') == run['id'] and record.get('attempted') is True) and not accepted_reuse(manifest, record):
            uncovered.append(row)
    manifest['sourceCoverageComplete'] = not gaps
    result = {'schema': 1, 'offline': True, 'build': manifest['build'], 'webRunID': run['id'],
              'policy': run['reuse']['policy'], 'summary': {key: run[key] for key in
                  ('targetCount', 'newlyRequested', 'notAttempted', 'reused', 'covered', 'uncovered',
                   'statuses', 'effectiveStatuses', 'requestCoverageComplete', 'acquisitionCoverageComplete')},
              'reusedRecords': [{field: records[key].get(field) for field in
                  ('key', 'url', 'finalUrl', 'status', 'path', 'sha256', 'webRunID', 'fetchedAt')} for key in sorted(entries)],
              'sourceGapCounts': dict(sorted(Counter(row['status'] for row in gaps).items())),
              'sourceGaps': gaps, 'notNewlyRequestedAndNotReused': uncovered,
              'originalManifestSHA256': sha256(original)}
    backup = raw / ('manifest.before-reuse.' + sha256(original) + '.json')
    if not backup.exists():
        backup.write_bytes(original)
    report.parent.mkdir(parents=True, exist_ok=True)
    checkpoint(report, result)
    checkpoint(path, manifest)
    return result
