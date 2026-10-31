"""Paired cold/warm engineering capture and real currency selection benchmark."""
import argparse
import json
from pathlib import Path
import statistics
import time

from benchmark_delivery import native, memory


def stats(samples):
    return {'medianMs': statistics.median(samples), 'p95Ms': sorted(samples)[int(.95 * (len(samples) - 1))]}


def benchmark(before, after):
    roots = [Path(before), Path(after)]
    observations = []
    for learned in (False, True):
        samples = [[], []];resident = [[], []]
        for iteration in range(12):
            for i in ((0, 1) if iteration % 2 == 0 else (1, 0)):
                vm = native(source_root=roots[i], profession='engineering', learned=learned)
                start = time.perf_counter()
                vm.execute("ns.ProfEconomy.Capture('engineering',{start=1,target=75})")
                samples[i].append((time.perf_counter() - start) * 1000)
                resident[i].append(memory(vm))
        observations.append({'case': 'engineering-first-capture', 'learned': learned,
            'before': stats(samples[0]), 'after': stats(samples[1]),
            'retainedKiBDelta': statistics.median(resident[1]) - statistics.median(resident[0])})
    vms = [native(source_root=root, profession='alchemy', learned=False) for root in roots]
    callbacks = []
    for vm in vms:
        vm.execute('''
          r=ns.ProfEconomy.FindRecipe('alchemy',1251752)
          s={known={},prices={},formulaOffers={},offers={},nonAuctionable={},
            ownedTeachingItems={},professions={alchemy={cur=300,max=300}},
            allowBindOnPickupFormulas=false,allowCurrencyFormulas=true,allowLimitedFormulas=false,
            faction='A',classID=4,raceID=1,level=60,completedQuests={},reputations={},specializationAbilities={}}
        ''')
        callbacks.append(vm.eval('function() for i=1,500 do ns.ProfEconomy.SelectLearningRoute(r,s) end end'))
    samples = [[], []]
    for cb in callbacks:
        cb()
    for iteration in range(30):
        for i in ((0, 1) if iteration % 2 == 0 else (1, 0)):
            start = time.perf_counter();callbacks[i]()
            samples[i].append((time.perf_counter() - start) * 1000 / 500)
    observations.append({'case': 'alchemy-1251752-quote', 'before': stats(samples[0]), 'after': stats(samples[1]),
        'iterations': 15000, 'retainedKiBDelta': memory(vms[1]) - memory(vms[0])})
    return {'offline': True, 'scope': 'Lua5.1 simulated client; first engineering capture and currency quote only',
        'observations': observations}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', required=True);parser.add_argument('--after', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = benchmark(args.before, args.after)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
