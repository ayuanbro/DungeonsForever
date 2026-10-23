# -*- coding: utf-8 -*-
"""Merge local vendor, NPC and client-price CSVs; emit CSV and Lua data.

Defaults are relative to this script, independent of the working directory.
No input CSV is changed. Run with --dry-run to validate without publishing.
Use --from-csv DataProfItems.csv to regenerate only the items Lua file.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from datetime import date, datetime, timezone

from fc_pipeline_common import (
    HERE, PACKAGE, REPO, fingerprint, publish_batch, require_repo_path, sha,
)
COST_FIELDS = ('cost_copper', 'cost_text', 'currency_kind', 'currency_id', 'currency_amount')
VENDOR_FIELDS = ('item_id', 'npc_id', 'zone_id', 'side', 'name_en', 'name_locale',
                 'cost_copper', 'cost_text', 'currency_kind', 'currency_id',
                 'currency_amount', 'stock')
PRICE_FIELDS = ('ItemID', 'Name_enUS', 'Name_zhTW', 'Name_zhCN', 'BuyPriceCopper',
                'VendorStackCount', 'PriceStatus', 'Build', 'HotfixBuild')
NPC_FIELDS = ('npc_id', 'name_en', 'name_locale', 'zone_id', 'ui_map_id', 'x', 'y')
EXTRA_FIELDS = ('buy_count', 'stock_kind', 'conditions', 'source', 'price_source',
                'price_basis', 'verified_at', 'quantity_source')
CSV_FIELDS = ('item_id', 'npc_id', 'name_en', 'zone_id', 'side', 'cost_copper',
              'cost_text', 'currency_kind', 'currency_id', 'currency_amount', 'stock',
              'Name_enUS', 'Name_zhTW', 'Name_zhCN', 'VendorStackCount',
              'PriceStatus', 'Build', 'HotfixBuild', 'price_source')
ITEM_FIELDS = ('item_id', 'Name_enUS', 'Name_zhTW', 'Name_zhCN', 'VendorStackCount',
               'PriceStatus', 'Build', 'HotfixBuild')
OFFER_FIELDS = tuple(field for field in CSV_FIELDS if field not in ITEM_FIELDS)
INTEGER_FIELDS = {'item_id': 1, 'npc_id': 1, 'zone_id': 1, 'cost_copper': 0,
                  'currency_id': 0, 'currency_amount': 0, 'stock': -1, 'VendorStackCount': 1}
DEFAULT_VENDOR_FACTIONS = HERE / '_fc/inputs/vendors/npc-factions.json'


class DataError(ValueError):
    pass


def clean(value):
    return '' if value is None else str(value).strip()


def integer(value, label, minimum=0):
    value = clean(value)
    if not value:
        return None
    if not re.fullmatch(r'-?\d+', value):
        raise DataError('%s: expected integer, got %r' % (label, value))
    number = int(value)
    if number < minimum:
        raise DataError('%s: must be >= %d' % (label, minimum))
    return number


def required_id(value, label):
    number = integer(value, label, 1)
    if number is None:
        raise DataError('%s: missing ID' % label)
    return number


def read_csv(path, required):
    with path.open('r', encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)):
            raise DataError('%s: duplicate column names' % path)
        missing = set(required) - set(fields)
        if missing:
            raise DataError('%s: missing columns %s' % (path, ', '.join(sorted(missing))))
        rows = []
        for number, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise DataError('%s:%d: malformed CSV row' % (path, number))
            rows.append(row)
    return fields, rows


def copper_text(value):
    gold, remainder = divmod(value, 10000)
    silver, copper = divmod(remainder, 100)
    return ''.join('%d%s' % (n, unit) for n, unit in
                   ((gold, 'g'), (silver, 's'), (copper, 'c')) if n) or '0c'


def stock_kind(value):
    value = integer(value, 'stock', -1)
    return '' if value is None else ('unlimited' if value == -1 else 'limited')


def valid_date(value):
    value = clean(value)
    if value:
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError('date format')
            date.fromisoformat(value)
        except ValueError:
            raise DataError('verified_at: expected YYYY-MM-DD, got %r' % value)
    return value


def merge_rows(vendor_fields, vendors, prices, verified_at=''):
    """Return the joined CSV. Only a completely empty cost can use client price."""
    fields = list(vendor_fields)
    for field in PRICE_FIELDS[1:] + EXTRA_FIELDS:
        if field not in fields:
            fields.append(field)
    price_map = {}
    for row in prices:
        item = required_id(row['ItemID'], 'ItemID')
        integer(row['BuyPriceCopper'], 'BuyPriceCopper')
        integer(row['VendorStackCount'], 'VendorStackCount', 1)
        if item in price_map and price_map[item] != row:
            raise DataError('conflicting duplicate ItemID %d' % item)
        price_map[item] = row

    result, found, pairs = [], set(), set()
    filled = 0

    def complete(row, price, has_npc):
        nonlocal filled
        for field in PRICE_FIELDS[1:]:
            row[field] = price.get(field, '') if price else ''
        row['source'] = clean(row.get('source')) or ('wowhead' if has_npc else 'client')
        row['verified_at'] = valid_date(clean(row.get('verified_at')) or verified_at)
        row['conditions'] = row.get('conditions', '')
        row['stock_kind'] = stock_kind(row.get('stock'))
        count = integer(row.get('buy_count'), 'buy_count', 1)
        if count is None and price:
            count = integer(price['VendorStackCount'], 'VendorStackCount', 1)
            row['quantity_source'] = 'client' if count is not None else ''
        else:
            row['quantity_source'] = clean(row.get('quantity_source')) or ('wowhead' if count else '')
        row['buy_count'] = '' if count is None else str(count)
        empty = all(not clean(row.get(field)) for field in COST_FIELDS)
        amount = integer(price['BuyPriceCopper'], 'BuyPriceCopper') if price else None
        status = clean(price.get('PriceStatus')) if price else ''
        if empty and amount is not None and amount > 0 and status in ('', 'priced'):
            row['cost_copper'] = str(amount)
            row['cost_text'] = copper_text(amount)
            row['price_source'] = 'client'
            row['price_basis'] = 'client_base_bundle'
            filled += int(has_npc)
        elif not empty:
            row['price_source'] = clean(row.get('price_source')) or 'wowhead'
            row['price_basis'] = clean(row.get('price_basis')) or 'vendor_page'
        else:
            row['price_source'] = ''
            row['price_basis'] = ''
        # Validation never converts an unknown cost to gold or free goods.
        integer(row.get('cost_copper'), 'cost_copper')
        integer(row.get('currency_id'), 'currency_id')
        integer(row.get('currency_amount'), 'currency_amount')
        if clean(row.get('side')) not in ('', 'a', 'h', 'n', 'A', 'H', 'N'):
            raise DataError('unsupported side %r' % row['side'])
        return row

    for vendor in vendors:
        item = required_id(vendor['item_id'], 'item_id')
        npc = required_id(vendor['npc_id'], 'npc_id')
        pair = (item, npc)
        if pair in pairs:
            raise DataError('duplicate vendor pair item_id=%d npc_id=%d' % pair)
        pairs.add(pair)
        found.add(item)
        row = {field: vendor.get(field, '') for field in fields}
        row['item_id'], row['npc_id'] = str(item), str(npc)
        result.append(complete(row, price_map.get(item), True))
    for item, price in sorted(price_map.items()):
        # Keep the independent client base quote even when vendor rows carry
        # reputation discounts, barter costs or limited recipe stock. This root
        # row makes the fixed 19-column CSV sufficient for exact reconstruction.
        row = dict.fromkeys(fields, '')
        row['item_id'] = str(item)
        result.append(complete(row, price, False))
    mixed = [row for row in result
             if any(clean(row[field]) for field in COST_FIELDS[:2])
             and any(clean(row[field]) for field in COST_FIELDS[2:])]
    return CSV_FIELDS, result, {'vendorRows': len(vendors), 'clientItems': len(price_map),
                               'filledPrices': filled, 'appendedItems': len(price_map.keys() - found),
                               'clientPriceRows': len(price_map),
                               'csvRows': len(result), 'mixedCostRows': len(mixed),
                               'mixedCostItems': len({row['item_id'] for row in mixed})}


def lua_string(value):
    chars = []
    for char in value:
        if char in ('"', '\\'):
            chars.append('\\' + char)
        elif ord(char) < 32 or ord(char) == 127:
            chars.append('\\%03d' % ord(char))
        else:
            chars.append(char)
    return '"' + ''.join(chars) + '"'


def lua(value):
    if value is None:
        return 'nil'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, str):
        return lua_string(value)
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise DataError('non-finite Lua number')
        return str(value)
    if isinstance(value, (list, tuple)):
        return '{' + ','.join(lua(v) for v in value) + '}'
    if isinstance(value, dict):
        parts = []
        for key, val in value.items():
            if val is None or val == '':
                continue
            field = key if isinstance(key, str) and re.fullmatch(r'[A-Za-z_]\w*', key) \
                else '[' + lua(key) + ']'
            parts.append(field + '=' + lua(val))
        return '{' + ','.join(parts) + '}'
    raise DataError('unsupported Lua value %r' % (value,))


def csv_record(row, fields):
    """Use CSV names verbatim, with explicit numeric types and absent unknowns."""
    record = {}
    for field in fields:
        value = row[field]
        if field in INTEGER_FIELDS:
            value = integer(value, field, INTEGER_FIELDS[field])
        elif not clean(value):
            value = None
        if value is not None:
            record[field] = value
    return record


def vendor_factions(content):
    """Validate evidence-backed NPC affiliations, independently of A/H/N access.

    This optional JSON is deliberately separate from the frozen price CSVs.
    Missing evidence cannot establish a neutral vendor or an affiliation.
    """
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise DataError('vendor factions: duplicate key %s' % key)
            result[key] = value
        return result

    def evidence_value(value):
        if value is None or isinstance(value, (str, bool, int)):
            return
        if isinstance(value, float) and math.isfinite(value):
            return
        if isinstance(value, list):
            for entry in value:
                evidence_value(entry)
            return
        if isinstance(value, dict) and all(isinstance(key, str) for key in value):
            for entry in value.values():
                evidence_value(entry)
            return
        raise DataError('vendor factions: unsupported evidence value')

    try:
        data = json.loads(content.decode('utf-8-sig'), object_pairs_hook=object_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DataError('vendor factions: invalid JSON: %s' % error)
    if not isinstance(data, dict) or type(data.get('schemaVersion')) is not int \
            or data['schemaVersion'] != 1 or not isinstance(data.get('npcs'), dict):
        raise DataError('vendor factions: expected schemaVersion=1 and npcs object')
    result = {}
    for key, record in data['npcs'].items():
        npc = required_id(key, 'vendor factions NPC ID')
        if str(npc) != key or not isinstance(record, dict):
            raise DataError('vendor factions: invalid NPC record %s' % key)
        if set(record) - {'factionID', 'names', 'sources'}:
            raise DataError('vendor factions: unsupported fields for NPC %s' % key)
        names = record.get('names')
        if not isinstance(names, dict) or not names or set(names) - {'enUS', 'zhCN', 'zhTW'} \
                or not isinstance(names.get('enUS'), str) or not names['enUS'].strip() \
                or any(not isinstance(value, str) or not value.strip() for value in names.values()):
            raise DataError('vendor factions: invalid localized names for NPC %s' % key)
        sources = record.get('sources')
        if not isinstance(sources, list) or not sources:
            raise DataError('vendor factions: missing evidence for NPC %s' % key)
        for source in sources:
            if not isinstance(source, dict) or not isinstance(source.get('type'), str) \
                    or not source['type'].strip() \
                    or not any(isinstance(source.get(field), str) and source[field].strip()
                               for field in ('url', 'file')):
                raise DataError('vendor factions: invalid evidence for NPC %s' % key)
            evidence_value(source)
        output = {'names': {locale: value.strip() for locale, value in names.items()},
                  'sources': sources}
        if 'factionID' in record:
            faction = record['factionID']
            if type(faction) is not int or faction <= 0:
                raise DataError('vendor factions: factionID must be a positive integer')
            output['factionID'] = faction
        result[npc] = output
    return result


def build_items(rows, metadata, factions=None):
    items, pairs = {}, set()
    for row in rows:
        item = required_id(row['item_id'], 'item_id')
        npc = integer(row['npc_id'], 'npc_id', 1)
        if (item, npc) in pairs:
            raise DataError('duplicate CSV item/NPC pair %s/%s' % (item, npc))
        pairs.add((item, npc))
        common = csv_record(row, ITEM_FIELDS)
        if item not in items:
            items[item] = dict(common, offers={})
        elif any(items[item].get(field) != common.get(field) for field in ITEM_FIELDS):
            raise DataError('conflicting common CSV fields for item_id=%d' % item)
        offer = csv_record(row, OFFER_FIELDS)
        if npc is not None:
            items[item]['offers'][npc] = offer
        else:
            # The independent client base quote belongs to the item. NPC recipe
            # quotations retain their own costs, currency and stock in offers.
            items[item].update(offer)
    metadata = dict(metadata, schemaVersion=2, csvFields=list(CSV_FIELDS))
    lines = ['local _, ns = ...', '', 'ns.ProfItemsMeta = ' + lua(metadata), '', 'ns.ProfItems = {']
    lines.extend('    [%d] = %s,' % (item, lua(record)) for item, record in sorted(items.items()))
    lines.append('}')
    lines.extend(('', 'ns.ProfVendorFactions = {'))
    lines.extend('    [%d] = %s,' % (npc, lua(record))
                 for npc, record in sorted((factions or {}).items()))
    lines.append('}')
    return '\n'.join(lines) + '\n'


def table_span(text, name):
    """Find a balanced Lua table, skipping quoted/long strings and comments."""
    match = re.search(r'(?m)^ns\.' + re.escape(name) + r'\s*=\s*\{', text)
    if not match:
        return None
    start = text.index('{', match.start())
    i, depth = start, 0
    while i < len(text):
        if text.startswith('--', i):
            long = re.match(r'--\[(=*)\[', text[i:])
            if long:
                end = text.find(']' + long[1] + ']', i + len(long[0]))
                if end < 0:
                    raise DataError('unterminated Lua comment')
                i = end + len(long[1]) + 2
            else:
                end = text.find('\n', i)
                i = len(text) if end < 0 else end + 1
            continue
        if text[i] in ('"', "'"):
            quote = text[i]
            i += 1
            while i < len(text) and text[i] != quote:
                i += 2 if text[i] == '\\' else 1
            i += 1
            continue
        long = re.match(r'\[(=*)\[', text[i:]) if text[i] == '[' else None
        if long:
            end = text.find(']' + long[1] + ']', i + len(long[0]))
            if end < 0:
                raise DataError('unterminated Lua string')
            i = end + len(long[1]) + 2
            continue
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return match.start(), start, i + 1
        i += 1
    raise DataError('unterminated ns.%s table' % name)


def coordinate(value, label):
    value = clean(value)
    if not value:
        return None
    try:
        number = float(value)
    except ValueError:
        raise DataError('%s: invalid coordinate %r' % (label, value))
    if not math.isfinite(number) or not 0 <= number <= 100:
        raise DataError('%s: coordinate outside 0..100' % label)
    return int(number) if number.is_integer() else number


def replace_table(text, name, value, newline='\n'):
    span = table_span(text, name)
    if span is None:
        return text.rstrip() + newline * 2 + 'ns.%s = %s%s' % (name, value, newline)
    return text[:span[0]] + 'ns.%s = %s' % (name, value) + text[span[2]:]


def update_vendors(text, npcs):
    first_newline = re.search(r'\r?\n', text)
    newline = first_newline.group() if first_newline else '\n'
    existing = {}
    span = table_span(text, 'ProfVendors')
    if span:
        body = text[span[1] + 1:span[2] - 1]
        body = re.sub(r'--[^\n]*', '', body)
        pattern = r'\[(\d+)\]\s*=\s*\{([^{}]*)\}\s*,?'
        for match in re.finditer(pattern, body):
            tokens = [v.strip() for v in match[2].split(',') if v.strip()]
            keyed = [re.fullmatch(r'\[\s*([1-4])\s*\]\s*=\s*(.+)', token)
                     for token in tokens]
            if tokens and all(keyed):
                keys = [int(token[1]) for token in keyed]
                if len(keys) != len(set(keys)):
                    raise DataError('duplicate ProfVendors position for %s' % match[1])
                sparse = dict(zip(keys, (token[2].strip() for token in keyed)))
                tokens = [sparse.get(index, 'nil') for index in range(1, 5)]
            elif len(tokens) != 4 or any(keyed):
                raise DataError('unexpected ProfVendors row for %s' % match[1])
            values = []
            for i, value in enumerate(tokens):
                values.append(None if value == 'nil' else
                              (integer(value, 'existing location ID', 1) if i < 2 else coordinate(value, 'existing coordinate')))
            existing[int(match[1])] = values
        if re.sub(pattern, '', body).strip(' \r\n\t,'):
            raise DataError('unsupported ProfVendors table structure; refusing to discard content')
    grouped = {}
    for row in npcs:
        npc = required_id(row['npc_id'], 'npcs.npc_id')
        location = [integer(row['zone_id'], 'npcs.zone_id', 1),
                    integer(row['ui_map_id'], 'npcs.ui_map_id', 1),
                    coordinate(row['x'], 'npcs.x'), coordinate(row['y'], 'npcs.y')]
        ent = grouped.setdefault(npc, {'name_en': '', 'name_locale': '', 'locations': []})
        for key in ('name_en', 'name_locale'):
            if clean(row[key]) and not ent[key]:
                ent[key] = row[key]
        if any(v is not None for v in location) and location not in ent['locations']:
            ent['locations'].append(location)
    updated, unresolved = 0, 0
    for npc, ent in grouped.items():
        old = existing.get(npc, [None] * 4)
        for partial in ent['locations']:
            moved = any(partial[i] is not None and old[i] is not None and partial[i] != old[i]
                        for i in (0, 1))
            # Coordinates belong to a map. Never transplant an old point onto a
            # new map, or keep its old map ID when only the area changed.
            merged = partial if moved else \
                [new if new is not None else previous for new, previous in zip(partial, old)]
            if (merged[0] is not None or merged[1] is not None) and all(v is not None for v in merged[2:]):
                existing[npc] = merged
                updated += 1
                break
        else:
            unresolved += 1
    value = '{' + newline + ''.join('    [%d] = %s,%s' % (npc, lua(loc), newline)
                            for npc, loc in sorted(existing.items())) + '}'
    if not text:
        text = 'local _, ns = ...\n\nns.ProfNPCLocs = {}\n'
    text = replace_table(text, 'ProfVendors', value, newline)
    detail = '{' + newline + ''.join('    [%d] = %s,%s' % (npc, lua(ent), newline)
                             for npc, ent in sorted(grouped.items())) + '}'
    text = replace_table(text, 'ProfVendorDetails', detail, newline)
    return text, {'npcRows': len(npcs), 'npcLocationsUpdated': updated,
                  'npcLocationsUnresolved': unresolved, 'vendorLocations': len(existing)}


def csv_bytes(fields, rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\r\n')
    writer.writeheader()
    # Internal merged rows also carry Lua metadata. The public CSV has an exact,
    # fixed schema and must not leak input extension columns or internal fields.
    writer.writerows({field: row[field] for field in fields} for row in rows)
    return stream.getvalue().encode('utf-8-sig')


def items_csv_rows(content):
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig'), newline=''))
    if reader.fieldnames != list(CSV_FIELDS):
        raise DataError('DataProfItems CSV columns/order must be: %s' % ','.join(CSV_FIELDS))
    rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise DataError('DataProfItems CSV contains a malformed row')
    return rows


def _snapshot(path, expected, overrides):
    path = Path(path).resolve()
    expected.setdefault(path, fingerprint(path))
    if path in overrides:
        return overrides[path]
    content = path.read_bytes()
    if sha(content) != expected[path]:
        raise DataError('input changed while freezing bytes: %s' % path)
    return content


def _vendor_faction_bundle(faction_path, faction_content, factions, expected, overrides):
    """Freeze and verify every declared file and every NPC evidence reference."""
    bundle = json.loads(faction_content.decode('utf-8-sig')).get('sourceBundle')
    if bundle is None:
        return

    def valid_hash(value):
        return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None

    def relative_file(value):
        if not isinstance(value, str) or not value or any(char in value for char in ('\\', ':', '\0')) \
                or any(part in ('', '.', '..') for part in value.split('/')):
            raise DataError('vendor factions: evidence path must be canonical and relative')
        return value

    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise DataError('vendor factions: duplicate source manifest key %s' % key)
            result[key] = value
        return result

    if not isinstance(bundle, dict) or bundle.get('directory') != 'faction-sources' \
            or not valid_hash(bundle.get('manifestSHA256')):
        raise DataError('vendor factions: invalid source bundle')
    bundle_root = require_repo_path(faction_path.parent / bundle['directory'])
    manifest_path = bundle_root / 'manifest.json'
    manifest_content = _snapshot(manifest_path, expected, overrides)
    if sha(manifest_content) != bundle['manifestSHA256']:
        raise DataError('vendor factions: source manifest hash mismatch')
    try:
        manifest = json.loads(manifest_content.decode('utf-8-sig'), object_pairs_hook=object_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DataError('vendor factions: invalid source manifest JSON: %s' % error)
    if not isinstance(manifest, dict) or type(manifest.get('schemaVersion')) is not int \
            or manifest['schemaVersion'] != 1 or not isinstance(manifest.get('files'), dict):
        raise DataError('vendor factions: invalid source manifest')
    for relative, record in manifest['files'].items():
        relative_file(relative)
        if not isinstance(record, dict) or not valid_hash(record.get('sha256')) \
                or type(record.get('bytes')) is not int or record['bytes'] < 0:
            raise DataError('vendor factions: invalid source manifest file record: %s' % relative)
        path = require_repo_path(bundle_root / relative)
        if not path.is_relative_to(bundle_root) or path == manifest_path:
            raise DataError('vendor factions: evidence path escapes source bundle')
        content = _snapshot(path, expected, overrides)
        if sha(content) != record['sha256'] or len(content) != record['bytes']:
            raise DataError('vendor factions: evidence hash mismatch: %s' % relative)
    for npc, affiliation in factions.items():
        for source in affiliation['sources']:
            name = relative_file(source.get('file'))
            prefix = bundle['directory'] + '/'
            if not name.startswith(prefix) or not valid_hash(source.get('sha256')):
                raise DataError('vendor factions: NPC %s evidence must bind a bundled file and hash' % npc)
            relative = name[len(prefix):]
            record = manifest['files'].get(relative)
            if record is None or source['sha256'] != record['sha256']:
                raise DataError('vendor factions: NPC %s evidence is absent from or differs from manifest: %s'
                                % (npc, name))


def _csv_content(content, required, path):
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig'), newline=''))
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)):
        raise DataError('%s: duplicate column names' % path)
    missing = set(required) - set(fields)
    if missing:
        raise DataError('%s: missing columns %s' % (path, ', '.join(sorted(missing))))
    rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise DataError('%s: malformed CSV row' % path)
    return fields, rows


def _dated_items(rows, metadata, previous, factions=None):
    # Repeated updates with identical inputs retain the existing generation time.
    text = previous.decode('utf-8-sig') if previous else ''
    match = re.search(r'ns\.ProfItemsMeta\s*=\s*\{generatedAt="([^"\r\n]+)"', text)
    if match:
        stable = dict(metadata, generatedAt=match[1])
        candidate = build_items(rows, stable, factions).encode('utf-8')
        if candidate == previous:
            return previous
    return build_items(rows, metadata, factions).encode('utf-8')


def build_batch(args, report=None):
    """Build CSV/Lua bytes using optional frozen input overrides.

    ``input_overrides`` maps final input paths to prepared bytes, so a parent
    transaction can use new prices and vendor locations before publication.
    No output is written here; callers own locking and final publication.
    """
    expected = {}
    overrides = {Path(path).resolve(): bytes(content) for path, content in
                 (getattr(args, 'input_overrides', {}) or {}).items()}
    verified = valid_date(getattr(args, 'verified_at', ''))
    destination = require_repo_path(args.items_lua)
    expected[destination] = fingerprint(destination)
    previous = destination.read_bytes() if destination.is_file() else None
    faction_path = getattr(args, 'vendor_factions_json', None)
    faction_explicit = faction_path is not None
    faction_path = Path(faction_path if faction_explicit else DEFAULT_VENDOR_FACTIONS).resolve()
    factions, faction_source = {}, None
    if faction_explicit or faction_path.is_file() or faction_path in overrides:
        protected = {Path(getattr(args, field)).resolve() for field in
                     ('items_lua', 'vendors_lua', 'output_csv')}
        if faction_path in protected:
            raise DataError('vendor factions input must not overlap output paths')
        faction_content = _snapshot(faction_path, expected, overrides)
        factions = vendor_factions(faction_content)
        _vendor_faction_bundle(faction_path, faction_content, factions, expected, overrides)
        faction_source = {'file': faction_path.name, 'sha256': sha(faction_content),
                          'kind': 'npc_affiliation'}
    if getattr(args, 'from_csv', None) is not None:
        source = args.from_csv.resolve()
        protected = [source, args.vendors_csv.resolve(), args.npcs_csv.resolve(),
                     args.prices_csv.resolve(), args.vendors_lua.resolve(), args.output_csv.resolve()]
        if destination in protected:
            raise DataError('items Lua must not overwrite CSV inputs or vendor Lua')
        content = _snapshot(source, expected, overrides)
        rows = items_csv_rows(content)
        mixed = [row for row in rows if any(clean(row[k]) for k in COST_FIELDS[:2])
                 and any(clean(row[k]) for k in COST_FIELDS[2:])]
        stats = {'csvRows': len(rows),
                 'items': len({required_id(row['item_id'], 'item_id') for row in rows}),
                 'vendorOffers': sum(bool(clean(row['npc_id'])) for row in rows),
                 'mixedCostRows': len(mixed),
                 'mixedCostItems': len({row['item_id'] for row in mixed})}
        metadata = {'generatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                    'sources': {'csv': {'file': source.name, 'sha256': sha(content)}},
                    'stats': stats}
        if faction_source:
            metadata['sources']['vendorFactions'] = faction_source
        outputs = {destination: _dated_items(rows, metadata, previous, factions)}
    else:
        inputs = [args.vendors_csv.resolve(), args.npcs_csv.resolve(), args.prices_csv.resolve()]
        destinations = [require_repo_path(args.output_csv), destination, require_repo_path(args.vendors_lua)]
        if len(set(destinations)) != 3 or set(inputs) & set(destinations):
            raise DataError('output paths must be distinct and must not overwrite input CSVs')
        for path in destinations:
            expected.setdefault(path, fingerprint(path))
        contents = [_snapshot(path, expected, overrides) for path in inputs]
        hashes = [sha(content) for content in contents]
        vendor_fields, vendors = _csv_content(contents[0], VENDOR_FIELDS, inputs[0])
        _, npcs = _csv_content(contents[1], NPC_FIELDS, inputs[1])
        _, prices = _csv_content(contents[2], PRICE_FIELDS, inputs[2])
        fields, rows, stats = merge_rows(vendor_fields, vendors, prices, verified)
        vendor_path = destinations[2]
        vendor_text = (_snapshot(vendor_path, expected, overrides).decode('utf-8-sig')
                       if vendor_path.is_file() or vendor_path in overrides else '')
        vendor_output, npc_stats = update_vendors(vendor_text, npcs)
        stats.update(npc_stats)
        csv_content = csv_bytes(fields, rows)
        metadata = {'generatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                    'sources': {label: {'file': path.name, 'sha256': digest, 'kind': kind}
                                for label, path, digest, kind in zip(
                                    ('vendors', 'npcs', 'prices'), inputs, hashes,
                                    ('wowhead', 'wowhead', 'client'))}, 'stats': stats}
        metadata['sources']['csv'] = {'file': destinations[0].name, 'sha256': sha(csv_content)}
        if faction_source:
            metadata['sources']['vendorFactions'] = faction_source
        outputs = {destinations[0]: csv_content,
                   destination: _dated_items(items_csv_rows(csv_content), metadata, previous, factions),
                   vendor_path: vendor_output.encode('utf-8')}
    for path, digest in expected.items():
        if fingerprint(path) != digest:
            raise DataError('input or output changed during generation: %s' % path)
    if report is not None:
        report.update(stats)
    return outputs, expected


def generate_from_csv(args):
    outputs, expected = build_batch(args)
    if not args.dry_run:
        publish_batch(outputs, expected)
    return 0


def publish(outputs):
    """Compatibility helper; all destinations are repository-local."""
    return publish_batch(outputs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-csv', type=Path,
                        help='only regenerate items Lua from an existing 19-column CSV')
    from fc_pipeline_paths import CSV_INPUTS
    parser.add_argument('--vendors-csv', type=Path, default=CSV_INPUTS['vendors_csv'])
    parser.add_argument('--npcs-csv', type=Path, default=CSV_INPUTS['npcs_csv'])
    parser.add_argument('--prices-csv', type=Path, default=CSV_INPUTS['prices_csv'])
    parser.add_argument('--vendor-factions-json', type=Path,
                        help='optional evidence-backed NPC affiliations; defaults to the bundled snapshot')
    parser.add_argument('--output-csv', type=Path, default=HERE / '_fc/data/DataProfItems.csv')
    parser.add_argument('--items-lua', type=Path, default=PACKAGE / 'Core/Data/Data_ProfItems.lua')
    parser.add_argument('--vendors-lua', type=Path, default=PACKAGE / 'Core/Data/Data_ProfVendors.lua')
    parser.add_argument('--verified-at', default='',
                        help='legacy date validation (YYYY-MM-DD); not emitted in CSV or items Lua')
    parser.add_argument('--dry-run', action='store_true', help='validate/build in memory; do not write files')
    args = parser.parse_args(argv)
    try:
        stats = {}
        outputs, expected = build_batch(args, stats)
        if not args.dry_run:
            publish_batch(outputs, expected)
        print('[%s] %s' % ('CHECK' if args.dry_run else 'OK', json.dumps(stats, ensure_ascii=False)))
        for path, content in outputs.items():
            print('  %s (%d bytes)' % (path, len(content)))
        return 0
    except (OSError, ValueError, csv.Error) as error:
        print('fc_prof_items: %s' % error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
