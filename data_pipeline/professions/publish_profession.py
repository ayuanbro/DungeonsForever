"""Publish one freshly generated profession while retaining other shipped facts.

This is an artifact merge, NOT a source collector or missing-field fallback.
The selected profession is replaced in full from the new generated provider.
Other professions are carried through unchanged and verified after encoding.
Useful when independent source-policy work is present in a shared checkout.
"""
from pathlib import Path
import argparse
import json

from .build import emit_lua
from .model import PROFESSIONS, canonical, sha256, write_json, SourceError


def read_provider(source):
    from lupa.lua51 import LuaRuntime
    runtime = LuaRuntime(unpack_returned_tuples=True)
    runtime.execute('ns={IsForever=true}')
    runtime.execute("assert(loadstring(...))('DungeonsForever',ns)", source.decode('utf-8-sig'))
    runtime.execute('out={};for _,slug in ipairs(...)do out[slug]={};for spell,r in ns.ProfLearningSources.Each(slug)do out[slug][spell]=ns.ProfLearningSources.Materialize(r)end end', runtime.table_from(sorted(PROFESSIONS.values())))

    def plain(value, field=None):
        if not hasattr(value, 'items'):
            return value
        keys = list(value.keys())
        if keys and set(keys) == set(range(1, len(keys) + 1)):
            return [plain(value[i]) for i in range(1, len(keys) + 1)]
        if not keys and field not in ('acquisition', 'meta'):
            return []
        return {key: plain(child, key) for key, child in value.items()}
    facts = {slug: {int(spell): plain(record) for spell, record in records.items()}
             for slug, records in runtime.globals().out.items()}
    return facts, plain(runtime.globals().ns.ProfLearningSources.meta, 'meta')


def publish(target, generated, profession, report):
    original = target.read_bytes()
    incoming = generated.read_bytes()
    old, old_meta = read_provider(original)
    new, new_meta = read_provider(incoming)
    if old_meta['build'] != new_meta['build'] or old_meta['product'] != new_meta['product']:
        raise SourceError('scoped publication requires matching product and build')
    if not new.get(profession):
        raise SourceError('selected profession has no newly generated records')
    merged = dict(old)
    merged[profession] = new[profession]
    fingerprint = sha256(canonical({'build': new_meta['build'], 'professions': merged}).encode('utf-8'))
    output = emit_lua(merged, {'build': new_meta['build'], 'fingerprint': fingerprint})
    actual, _ = read_provider(output)
    if actual != merged:
        raise SourceError('publication changed decoded facts')
    # Guard against another chat publishing between our read and write.
    if target.read_bytes() != original:
        raise SourceError('target changed during scoped publication')
    target.write_bytes(output)
    write_json(report, {'operation': 'scoped-artifact-publication', 'profession': profession,
        'build': new_meta['build'], 'recordCount': len(new[profession]),
        'sourceProviderSHA256': sha256(incoming), 'previousProviderSHA256': sha256(original),
        'outputSHA256': sha256(output), 'fingerprint': fingerprint,
        'previousFingerprint': old_meta['fingerprint'], 'generatedFingerprint': new_meta['fingerprint'],
        'otherProfessionsChanged': [],
        'note': 'Selected records come only from the new source build; other shipped records are retained verbatim as decoded facts.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--generated', type=Path, required=True)
    parser.add_argument('--profession', choices=sorted(PROFESSIONS.values()), required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    publish(args.target, args.generated, args.profession, args.report)


if __name__ == '__main__':
    main()
