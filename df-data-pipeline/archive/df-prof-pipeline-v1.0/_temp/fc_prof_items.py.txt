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

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
REPO = PACKAGE.parent
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
        if item in found:
            continue
        row = dict.fromkeys(fields, '')
        row['item_id'] = str(item)
        result.append(complete(row, price, False))
    mixed = [row for row in result
             if any(clean(row[field]) for field in COST_FIELDS[:2])
             and any(clean(row[field]) for field in COST_FIELDS[2:])]
    return CSV_FIELDS, result, {'vendorRows': len(vendors), 'clientItems': len(price_map),
                               'filledPrices': filled, 'appendedItems': len(price_map.keys() - found),
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


def build_items(rows, metadata):
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
            # A client-only row still has a price, but does not identify a seller.
            # Keep it on the item rather than inventing an NPC or a base price.
            items[item].update(offer)
    metadata = dict(metadata, schemaVersion=2, csvFields=list(CSV_FIELDS))
    lines = ['local _, ns = ...', '', 'ns.ProfItemsMeta = ' + lua(metadata), '', 'ns.ProfItems = {']
    lines.extend('    [%d] = %s,' % (item, lua(record)) for item, record in sorted(items.items()))
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


def replace_table(text, name, value):
    span = table_span(text, name)
    if span is None:
        return text.rstrip() + '\n\nns.%s = %s\n' % (name, value)
    return text[:span[0]] + 'ns.%s = %s' % (name, value) + text[span[2]:]


def update_vendors(text, npcs):
    existing = {}
    span = table_span(text, 'ProfVendors')
    if span:
        body = text[span[1] + 1:span[2] - 1]
        body = re.sub(r'--[^\n]*', '', body)
        pattern = r'\[(\d+)\]\s*=\s*\{([^{}]*)\}\s*,?'
        for match in re.finditer(pattern, body):
            tokens = [v.strip() for v in match[2].split(',') if v.strip()]
            if len(tokens) != 4:
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
    value = '{\n' + ''.join('    [%d] = %s,\n' % (npc, lua(loc))
                            for npc, loc in sorted(existing.items())) + '}'
    if not text:
        text = 'local _, ns = ...\n\nns.ProfNPCLocs = {}\n'
    text = replace_table(text, 'ProfVendors', value)
    detail = '{\n' + ''.join('    [%d] = %s,\n' % (npc, lua(ent))
                             for npc, ent in sorted(grouped.items())) + '}'
    text = replace_table(text, 'ProfVendorDetails', detail)
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


def generate_from_csv(args):
    source = args.from_csv.resolve()
    destination = args.items_lua.resolve()
    protected = [source, args.vendors_csv.resolve(), args.npcs_csv.resolve(),
                 args.prices_csv.resolve(), args.vendors_lua.resolve(), args.output_csv.resolve()]
    if destination in protected:
        raise DataError('items Lua must not overwrite CSV inputs or vendor Lua')
    content = source.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    rows = items_csv_rows(content)
    mixed = [row for row in rows if any(clean(row[k]) for k in COST_FIELDS[:2])
             and any(clean(row[k]) for k in COST_FIELDS[2:])]
    stats = {'csvRows': len(rows), 'items': len({required_id(row['item_id'], 'item_id') for row in rows}),
             'vendorOffers': sum(bool(clean(row['npc_id'])) for row in rows),
             'mixedCostRows': len(mixed), 'mixedCostItems': len({row['item_id'] for row in mixed})}
    metadata = {'generatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'sources': {'csv': {'file': source.name, 'sha256': digest}}, 'stats': stats}
    output = build_items(rows, metadata).encode('utf-8')
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise DataError('input CSV changed during generation; no output published')
    if not args.dry_run:
        publish({destination: output})
    print('[%s] %s' % ('CHECK' if args.dry_run else 'OK', json.dumps(stats, ensure_ascii=False)))
    print('  %s (%d bytes)' % (destination, len(output)))
    return 0


def publish(outputs):
    """Stage every output first; roll back completed replacements on failure."""
    staged, originals, published = {}, {}, []
    try:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            originals[path] = path.read_bytes() if path.exists() else None
            with tempfile.NamedTemporaryFile(dir=str(path.parent), prefix='.' + path.name + '.',
                                             suffix='.tmp', delete=False) as stream:
                staged[path] = Path(stream.name)
                stream.write(content)
        for path, temporary in staged.items():
            os.replace(str(temporary), str(path))
            published.append(path)
    except BaseException:
        for path in reversed(published):
            if originals[path] is None:
                path.unlink()
            else:
                with tempfile.NamedTemporaryFile(dir=str(path.parent), delete=False) as stream:
                    restore = Path(stream.name)
                    stream.write(originals[path])
                try:
                    os.replace(str(restore), str(path))
                finally:
                    if restore.exists():
                        restore.unlink()
        raise
    finally:
        for temporary in staged.values():
            if temporary.exists():
                temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-csv', type=Path,
                        help='only regenerate items Lua from an existing 19-column CSV')
    parser.add_argument('--vendors-csv', type=Path, default=REPO / 'scripts/out/vendors.csv')
    parser.add_argument('--npcs-csv', type=Path, default=REPO / 'scripts/out/npcs.csv')
    parser.add_argument('--prices-csv', type=Path, default=REPO / 'scripts/export_buyprice/output/item-buy-prices.csv')
    parser.add_argument('--output-csv', type=Path, default=HERE / '_fc/data/DataProfItems.csv')
    parser.add_argument('--items-lua', type=Path, default=PACKAGE / 'Core/Data/Data_ProfItems.lua')
    parser.add_argument('--vendors-lua', type=Path, default=PACKAGE / 'Core/Data/Data_ProfVendors.lua')
    parser.add_argument('--verified-at', default='',
                        help='legacy date validation (YYYY-MM-DD); not emitted in CSV or items Lua')
    parser.add_argument('--dry-run', action='store_true', help='validate/build in memory; do not write files')
    args = parser.parse_args(argv)
    try:
        verified = valid_date(args.verified_at)
        if args.from_csv is not None:
            return generate_from_csv(args)
        inputs = [args.vendors_csv.resolve(), args.npcs_csv.resolve(), args.prices_csv.resolve()]
        destinations = [args.output_csv.resolve(), args.items_lua.resolve(), args.vendors_lua.resolve()]
        if len(set(destinations)) != 3 or set(inputs) & set(destinations):
            raise DataError('output paths must be distinct and must not overwrite input CSVs')
        # Hash the exact source snapshot used in this run, detecting concurrent replacement.
        hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs]
        vendor_fields, vendors = read_csv(args.vendors_csv, VENDOR_FIELDS)
        _, npcs = read_csv(args.npcs_csv, NPC_FIELDS)
        _, prices = read_csv(args.prices_csv, PRICE_FIELDS)
        fields, rows, stats = merge_rows(vendor_fields, vendors, prices, verified)
        vendor_text = args.vendors_lua.read_text(encoding='utf-8-sig') if args.vendors_lua.exists() else ''
        vendor_output, npc_stats = update_vendors(vendor_text, npcs)
        stats.update(npc_stats)
        csv_content = csv_bytes(fields, rows)
        metadata = {'generatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                    'sources': {label: {'file': path.name, 'sha256': digest, 'kind': kind}
                                for label, path, digest, kind in zip(
                                    ('vendors', 'npcs', 'prices'), inputs, hashes, ('wowhead', 'wowhead', 'client'))},
                    'stats': stats}
        metadata['sources']['csv'] = {'file': destinations[0].name,
                                      'sha256': hashlib.sha256(csv_content).hexdigest()}
        # Lua only sees the serialized 19-column CSV, never internal/raw fields.
        outputs = {destinations[0]: csv_content,
                   destinations[1]: build_items(items_csv_rows(csv_content), metadata).encode('utf-8'),
                   destinations[2]: vendor_output.encode('utf-8')}
        if hashes != [hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs]:
            raise DataError('input CSV changed during generation; no outputs published')
        if not args.dry_run:
            publish(outputs)
        print('[%s] %s' % ('CHECK' if args.dry_run else 'OK', json.dumps(stats, ensure_ascii=False)))
        for path, content in outputs.items():
            print('  %s (%d bytes)' % (path, len(content)))
        return 0
    except (OSError, ValueError, csv.Error) as error:
        print('fc_prof_items: %s' % error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
