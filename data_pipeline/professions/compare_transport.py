"""Explicit, gated online transport experiment. Never used as generation input."""
from __future__ import annotations

from collections import Counter
import json
import math
import os
from pathlib import Path
import time
from urllib.parse import urlsplit

from .browser_transport import BrowserTransport
from .fetch import WowheadTransport, latest, response_record
from .model import SourceError, sha256, write_json


def completion_gate(raw, proc=Path('/proc')):
    """Fail before any network request or output writes if collection is active."""
    raw = Path(raw).resolve()
    if raw.with_name(raw.name + '.partial').exists():
        raise SourceError('collection partial still exists; online comparison deferred')
    manifest = json.loads((raw / 'manifest.json').read_text(encoding='utf8'))
    run = manifest.get('webRun', {})
    if not manifest.get('fetchComplete') or not run.get('requestCoverageComplete'):
        raise SourceError('collection is not complete; online comparison deferred')
    records = {r['key']: r for r in manifest['responses']}
    targets = run.get('targets', [])
    if not targets or len(set(targets)) != run.get('targetCount') or any(
        records.get(k, {}).get('webRunID') != run.get('id') or
        records.get(k, {}).get('attempted') is not True for k in targets
    ):
        raise SourceError('full request coverage is inconsistent')
    if not proc.is_dir():
        raise SourceError('online comparison requires Linux /proc to exclude active collectors')
    for process in proc.iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            args = (process / 'cmdline').read_bytes().split(b'\0')
        except FileNotFoundError:
            continue
        except PermissionError as error:
            raise SourceError('cannot inspect active processes; comparison deferred') from error
        if b'data_pipeline.professions' in args and any(x in args for x in (b'fetch', b'probe', b'compare')):
            raise SourceError('another collector/comparison is running; comparison deferred')
    archive = raw.with_suffix('.zip')
    if not archive.is_file():
        raise SourceError('collection archive is not published yet')
    import zipfile
    with zipfile.ZipFile(archive) as package:
        if package.read('manifest.json') != (raw / 'manifest.json').read_bytes():
            raise SourceError('archive publication is incomplete')
    return manifest


def select_sample(manifest, limit):
    # Include entity types and real failures, not just hand-picked easy 200s.
    buckets = {}
    for row in manifest['responses']:
        if not row['key'].startswith('web:') or not row.get('attempted'):
            continue
        kind = row['key'].split(':')[1]
        buckets.setdefault((kind, row['status']), []).append(row)
    for rows in buckets.values():
        rows.sort(key=lambda r: sha256(r['key'].encode()))
    selected = []
    while buckets and len(selected) < limit:
        for key in sorted(list(buckets)):
            selected.append(buckets[key].pop(0))
            if not buckets[key]:
                del buckets[key]
            if len(selected) == limit:
                break
    return selected


def compare(raw, out, limit=12, interval=2.0, rounds=2):
    if not 4 <= limit <= 40 or not 1 <= rounds <= 3 or not math.isfinite(interval) or interval < 2:
        raise SourceError('comparison needs 4..40 entities, 1..3 rounds and interval >= 2 seconds')
    raw, out = Path(raw).resolve(), Path(out).resolve()
    manifest = completion_gate(raw)
    if out.exists() or out.is_relative_to(raw) or raw.is_relative_to(out):
        raise SourceError('comparison output must be a new, separate directory')
    before = latest()
    if (before['version'], before['build_config']) != (manifest['build'], manifest['buildInfo']['build_config']):
        raise SourceError('latest build changed; finish a new full collection before comparing')
    sample = select_sample(manifest, limit)
    out.mkdir(parents=True)
    results, facts, observations = [], {}, {}
    browser = None
    active_arm = None
    records = []
    started = time.monotonic()
    variants = [('navigation', 'all'), ('fetch', 'all'), ('navigation', 'light')]
    write_json(out / 'experiment.json', {'generationInput': False, 'build': manifest['build'],
        'sampleKeys': [r['key'] for r in sample], 'interval': interval, 'rounds': rounds,
        'variants': variants, 'sourceManifestSHA256': sha256((raw / 'manifest.json').read_bytes()),
        'baseline': 'native navigation, all assets, same scheduler and parser',
        'scope': 'transport A/B only; not an end-to-end old/new pipeline speed claim'})
    try:
        for trial in range(rounds):
            # Reverse arm order to reduce the systematic cold/time-order bias.
            order = variants if trial % 2 == 0 else list(reversed(variants))
            for mode, assets in order:
                arm = out / f'{trial}-{mode}-{assets}'
                active_arm = arm.name
                arm.mkdir()
                browser = BrowserTransport(request_mode=mode, assets=assets, collect_metrics=True, diagnostics=True)
                transport = WowheadTransport(interval=interval, mode='browser', browser_factory=lambda: browser,
                                             recoveries=0)
                started = time.monotonic()
                records = []
                with transport:
                    # Repeated warm pass measures the cost of routing disabling cache.
                    for pass_id in (0, 1):
                        for source in sample:
                            key = source['key']; _, kind, identity = key.split(':')
                            url = source.get('url', '')
                            if urlsplit(url).netloc != 'www.wowhead.com' or not urlsplit(url).path.startswith('/forever/'):
                                raise SourceError('comparison source URL is not a Forever entity')
                            parsed = {}
                            start = time.monotonic()
                            row = response_record(arm, key, url, transport.get, entity=(kind, int(identity)), parsed_sink=parsed)
                            row.update(passID=pass_id, seconds=time.monotonic() - start)
                            records.append(row)
                            observations.setdefault(key, []).append({'arm': arm.name, 'pass': pass_id, 'status': row['status']})
                            if row['status'] == 'verified':
                                normalized = json.dumps(parsed, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
                                facts.setdefault(key, []).append({'arm': arm.name, 'pass': pass_id, 'sha256': sha256(normalized.encode())})
                            write_json(arm / 'responses.json', records)
                            if row['status'] in ('sourceBlocked', 'sourceError'):
                                # Do not improve a benchmark score by cycling identities.
                                raise SourceError('comparison stopped on refusal/transport error; partial evidence saved')
                elapsed = time.monotonic() - started
                counts = Counter(r['status'] for r in records)
                results.append({'arm': arm.name, 'mode': mode, 'assets': assets, 'seconds': elapsed,
                    'statuses': dict(counts), 'verifiedPerMinute': counts['verified'] * 60 / max(elapsed, .001),
                    'verifiedRate': counts['verified'] / max(len(records), 1),
                    'blockedRate': counts['sourceBlocked'] / max(len(records), 1),
                    'network': browser.metrics, 'identity': browser.identity,
                    'trafficScope': 'page-target CDP events including subresources; excludes other targets and protocol overhead',
                    'host': transport.metrics, 'requests': len(records)})
        after = latest()
        if (after['version'], after['build_config']) != (before['version'], before['build_config']):
            raise SourceError('latest changed during comparison; results are not accepted')
        mismatches = {k: v for k, v in facts.items() if len({x['sha256'] for x in v}) > 1}
        status_mismatches = {k: v for k, v in observations.items()
                             if len(v) != rounds * len(variants) * 2 or len({x['status'] for x in v}) != 1}
        report = {'complete': True, 'generationInput': False, 'build': before['version'],
                  'results': results, 'factMismatches': mismatches,
                  'factsEqual': bool(facts) and not mismatches and not status_mismatches, 'facts': facts,
                  'statusMismatches': status_mismatches, 'observations': observations,
                  'challengeObserved': any(r['network'].get('navigationStatuses', {}).get('202', 0) or
                                           r['network'].get('fetchStatuses', {}).get('202', 0) for r in results),
                  'note': 'No automatic promotion. A changed page or missing/unequal coverage needs review.'}
        write_json(out / 'report.json', report)
        return report
    except BaseException as error:
        elapsed = time.monotonic() - started
        counts = Counter(r['status'] for r in records)
        write_json(out / 'report.json', {'complete': False, 'generationInput': False, 'results': results,
                   'error': type(error).__name__ + ': ' + str(error), 'facts': facts,
                   'interruptedArm': active_arm, 'observations': observations,
                   'interruptedNetwork': browser.metrics if browser else None,
                   'interruptedResult': {'statuses': dict(counts), 'seconds': elapsed,
                       'requests': len(records), 'verifiedPerMinute': counts['verified'] * 60 / max(elapsed, .001),
                       'verifiedRate': counts['verified'] / max(len(records), 1),
                       'blockedRate': counts['sourceBlocked'] / max(len(records), 1)}})
        raise
