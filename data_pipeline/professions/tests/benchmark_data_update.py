"""Paired warmed Capture benchmark with immutable native Data (Lua5.1 mocks)."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import statistics
import time

from benchmark_delivery import native


def benchmark(before, after, output, iterations=150, allow_code_changes=False):
    supplement = 'Core/Data/Data_ProfLearningSources.lua'
    roots = [Path(before).resolve(), Path(after).resolve()]
    hashes = []
    for root in roots:
        paths = [root / 'DungeonsForever.toc'] + list((root / 'Core').rglob('*.lua')) + list((root / 'Locales').rglob('*.lua'))
        hashes.append({path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})
    assert hashes[0].keys() == hashes[1].keys(), 'benchmark source tree file sets differ'
    changed = sorted(key for key in hashes[0] if hashes[0][key] != hashes[1][key])
    if allow_code_changes:
        assert all(key == supplement or key.startswith('Core/Prof') and not key.startswith('Core/Data/')
                   or key.startswith('Locales/') for key in changed), 'native Data/TOC or unrelated code differs'
    else:
        assert all(key == supplement for key in changed), 'benchmark source trees differ beyond supplement'
    rows = []
    for slug in ('alchemy', 'blacksmithing', 'leatherworking'):
        for learned in (True, False):
            vms = [native(source_root=root, profession=slug, learned=learned) for root in roots]
            callbacks = [vm.eval("function() return ns.ProfEconomy.Capture(" + json.dumps(slug) + ",{start=1,target=75}) end") for vm in vms]
            for callback in callbacks:
                for _ in range(15):
                    callback()
            samples = [[], []]
            for iteration in range(iterations):
                for index in ((0, 1) if iteration % 2 == 0 else (1, 0)):
                    gc.collect()
                    started = time.perf_counter()
                    callbacks[index]()
                    samples[index].append((time.perf_counter() - started) * 1000)
            p95 = [sorted(values)[int(.95 * (len(values) - 1))] for values in samples]
            row = {'profession': slug, 'learned': learned, 'iterations': iterations,
                   'beforeP95Ms': p95[0], 'afterP95Ms': p95[1], 'regressionPercent': (p95[1] / p95[0] - 1) * 100,
                   'beforeMedianMs': statistics.median(samples[0]), 'afterMedianMs': statistics.median(samples[1])}
            rows.append(row)
            print(json.dumps(row), flush=True)
    result = {'offline': True, 'environment': 'Lua5.1 mocks, paired alternating warmed Capture',
              'scope': 'capture target 75 only; excludes solving, UI, callbacks, initial load and real client',
              'sameNativeDataAndCode': all(key == supplement for key in changed),
              'sameNativeDataAndTOC': True, 'changedFiles': changed,
              'beforeSourceSHA256': hashes[0], 'beforeDataSHA256': hashes[0][supplement],
              'afterDataSHA256': hashes[1][supplement], 'sourceSHA256': hashes[1],
              'observations': rows, 'p95BudgetPercent': 10,
              'passed': all(row['regressionPercent'] <= 10 for row in rows)}
    Path(output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--iterations', type=int, default=150)
    parser.add_argument('--allow-code-changes', action='store_true',
                        help='Compare the complete profession fix; native Data and TOC must still match exactly.')
    args = parser.parse_args()
    if args.iterations < 20:
        parser.error('at least 20 observations required')
    result = benchmark(args.before, args.after, args.output, args.iterations, args.allow_code_changes)
    raise SystemExit(0 if result['passed'] else 1)
