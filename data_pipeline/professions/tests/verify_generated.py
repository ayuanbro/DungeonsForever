"""Compare every generated Lua public record with the fresh source audit.

This is an offline consumer check, never a source-generation input.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / '.pipeline-runtime/lib'))
from lupa.lua51 import LuaRuntime
from data_pipeline.professions.build import automatic_skill_rank, runtime_facts


def verify(data, audit, output):
    data, audit, output = Path(data), Path(audit), Path(output)
    source = data.read_text(encoding='utf8')
    report = json.loads(audit.read_text(encoding='utf8'))
    vm = LuaRuntime(unpack_returned_tuples=True)
    vm.execute('ns={IsForever=true};ns.ProfRecipes={sentinel=true};originalRecipes=ns.ProfRecipes')
    vm.execute("assert(loadstring(...,'@generated-learning-verification'))('DungeonsForever',ns)", source)
    provider = vm.globals().ns['ProfLearningSources']
    assert provider['meta']['fingerprint'] == report['fingerprint']
    assert provider['meta']['build'] == report['build']
    assert provider['meta']['rules'] == report['rules']
    same = vm.eval('''function(a,b)
      local function equal(a,b)
        if type(a)~=type(b) then error('generated type mismatch') end
        if type(a)~='table' then assert(a==b,'generated value mismatch');return end
        for key,value in pairs(a)do assert(b[key]~=nil,'extra field '..tostring(key));equal(value,b[key])end
        for key in pairs(b)do assert(a[key]~=nil,'missing field '..tostring(key))end
      end
      equal(a,b)
    end''')
    counts = {}
    for slug, records in runtime_facts(report['facts']).items():
        for spell, expected in records.items():
            actual = provider['Materialize'](provider['Get'](slug, int(spell)))
            same(actual, vm.table_from(expected, recursive=True))
            assert provider['AutomaticSkillRank'](slug, int(spell)) == automatic_skill_rank(expected)
        counts[slug] = len(records)
    vm.execute("assert(ns.ProfRecipes==originalRecipes and ns.ProfRecipes.sentinel)")
    assert provider['Get']('first-aid', 3275) is None
    other = LuaRuntime()
    other.execute('ns={IsForever=false}')
    other.execute("assert(loadstring(...,'@generated-learning-verification'))('DungeonsForever',ns)", source)
    assert other.globals().ns['ProfLearningSources'] is None
    result = {'offline': True, 'luaVersion': vm.eval('_VERSION'), 'build': report['build'],
              'rules': report['rules'], 'fingerprint': report['fingerprint'], 'recordsVerified': sum(counts.values()),
              'professions': counts, 'allPublicFieldsEqualFreshRuntimeProjection': True,
              'nativeRecipesUntouched': True, 'firstAidExcluded': True, 'foreverOnly': True,
              'dataSHA256': hashlib.sha256(data.read_bytes()).hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    verify(args.data, args.audit, args.output)
