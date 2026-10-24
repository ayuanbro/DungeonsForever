"""Read names from the verified Forever WDC5 Faction layout; never infer NPC side."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ("ID", "Name_enUS", "Name_zhCN", "Name_zhTW")
LOCALE_MASKS = {"enUS": 1, "zhCN": 16, "zhTW": 32}
DEFINITION = "https://github.com/wowdev/WoWDBDefs/blob/master/definitions/Faction.dbd"


def decode(data: bytes) -> tuple[dict[int, str], dict]:
    """Decode all readable IDs, including copies, for layout 6D443C38 only.

    This is deliberately a small name reader, not a general DB2 decoder. The
    checked layout places Name_lang first, uncompressed, with a relative int32
    string offset and an external ID list. Unknown layouts fail closed.
    """
    if len(data) < 204 or data[:4] != b"WDC5":
        raise ValueError("A complete WDC5 Faction file is required")
    header = struct.unpack_from("<9I2H7I", data, 136)
    records, fields, size, strings, table, layout, _, _, locale, flags, _, total, _, _, storage, common, pallet, count = header
    if table != 0x06F624D7 or layout != 0x6D443C38:
        raise ValueError("Unsupported Faction table/layout hash")
    if flags & 1 or not flags & 4 or fields != 21 or total != 21 or size != 20 or storage != fields * 24 or not count:
        raise ValueError("Unsupported Faction record/index structure")
    language = next((name for name, mask in LOCALE_MASKS.items() if locale == mask), None)
    if language is None:
        raise ValueError("Faction locale must identify exactly enUS, zhCN, or zhTW")
    section_end = 204 + count * 40
    metadata_end = section_end + fields * 4 + storage + common + pallet
    if metadata_end > len(data):
        raise ValueError("Truncated Faction metadata")
    if struct.unpack_from("<hH", data, section_end) != (0, 0):
        raise ValueError("Unexpected Name_lang field metadata")
    if struct.unpack_from("<HHII", data, section_end + fields * 4) != (0, 32, 0, 0):
        raise ValueError("Name_lang is not an uncompressed int32 offset")
    sections = [struct.unpack_from("<Q8I", data, 204 + i * 40) for i in range(count)]
    if sum(section[2] for section in sections) != records or sum(section[3] for section in sections) != strings:
        raise ValueError("Faction section totals disagree with the header")
    encrypted_ids = []
    cursor = metadata_end
    for key, *_ in sections:
        if not key:
            continue
        if cursor + 4 > len(data):
            raise ValueError("Truncated encrypted ID metadata")
        amount = struct.unpack_from("<I", data, cursor)[0]
        cursor += 4
        if cursor + 4 * amount > len(data):
            raise ValueError("Truncated encrypted ID list")
        encrypted_ids.extend(struct.unpack_from(f"<{amount}I", data, cursor))
        cursor += 4 * amount
    global_strings = bytearray()
    for _, offset, amount, string_size, _, _, _, _, _ in sections:
        start = offset + amount * size
        if offset < cursor or start + string_size > len(data):
            raise ValueError("Faction section is outside the file")
        global_strings.extend(data[start:start + string_size])
    names: dict[int, str] = {}
    copies = []
    skipped = []
    previous = 0
    for key, offset, amount, string_size, _, id_size, relation_size, maps, copy_count in sections:
        id_start = offset + amount * size + string_size
        copy_start = id_start + id_size
        end = copy_start + copy_count * 8 + maps * 10 + relation_size
        if id_size != amount * 4 or maps or end > len(data):
            raise ValueError("Unsupported or truncated Faction ID/copy data")
        record_data = data[offset:offset + amount * size]
        if key and not any(record_data) and not any(data[id_start:copy_start]):
            skipped.append(f"{key:016X}")
            previous += amount
            continue
        ids = struct.unpack_from(f"<{amount}I", data, id_start)
        for index, row_id in enumerate(ids):
            if not row_id or row_id in names:
                raise ValueError("Invalid or duplicate Faction ID")
            relative = struct.unpack_from("<i", data, offset + index * size)[0]
            string_index = (previous + index - records) * size + relative
            if relative == 0:
                name = ""
            else:
                if not 0 <= string_index < len(global_strings):
                    raise ValueError("Name_lang offset is outside the string tables")
                terminator = global_strings.find(0, string_index)
                if terminator < 0:
                    raise ValueError("Unterminated Faction name")
                name = global_strings[string_index:terminator].decode("utf-8", errors="strict")
            names[row_id] = name
        copies.extend(struct.unpack_from("<2I", data, copy_start + i * 8) for i in range(copy_count))
        previous += amount
    pending = copies[:]
    while pending:
        remaining = []
        for target, source in pending:
            if not target or target in names:
                raise ValueError("Invalid or duplicate Faction copy ID")
            if source in names:
                names[target] = names[source]
            else:
                remaining.append((target, source))
        if len(remaining) == len(pending):
            break
        pending = remaining
    return names, {"tableHash": f"{table:08X}", "layoutHash": f"{layout:08X}",
        "schemaString": data[8:136].rstrip(b"\0").decode("ascii"), "localeMask": locale,
        "locale": language, "localeVerified": True, "readableRows": len(names),
        "encryptedRecordIDs": encrypted_ids, "skippedEncryptedSections": skipped,
        "unresolvedCopies": pending, "definition": DEFINITION}


def export(input_path: Path, output_directory: Path, build: str) -> dict:
    output_directory = output_directory.resolve()
    if not output_directory.is_relative_to(ROOT.resolve()):
        raise ValueError("Output must stay inside the repository")
    if output_directory.exists():
        raise ValueError("Use a new output directory; frozen evidence is never overwritten")
    parts = build.split(".")
    if len(parts) != 4 or any(not part.isdigit() for part in parts):
        raise ValueError("Build must have four numeric components")
    data = input_path.read_bytes()
    names, evidence = decode(data)
    schema = "wowstatic_camelot_" + "_".join(parts[:3])
    if evidence["schemaString"] != schema:
        raise ValueError("Build and Faction schemaString disagree")
    output_directory.mkdir(parents=True)
    output_path = output_directory / "factions.csv"
    raw_file = "raw/faction_" + evidence["locale"] + ".db2"
    (output_directory / "raw").mkdir()
    (output_directory / raw_file).write_bytes(data)
    with output_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({"ID": row_id, "Name_" + evidence["locale"]: name} for row_id, name in sorted(names.items()))
    with (output_directory / "npc-factions.csv").open("x", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerow(("npc_id", "faction_id", "status", "faction_template_ids", "creature_difficulty_ids"))
    report = {"schema": 1, "producer": "DungeonsForever.FactionNameDecoder", "build": build,
        "buildEvidence": "Declared build; validated schema family. Exact build is not embedded in WDC5.",
        "input": {"file": str(input_path.resolve()), "rawFile": raw_file, "sha256": hashlib.sha256(data).hexdigest(), **evidence},
        "output": {"file": output_path.name, "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(), "rows": len(names)},
        "hotfix": {"requested": False, "reason": "Raw DB2 only; no hotfixes applied"},
        "limitations": ["No NPC association or player A/H/N access is inferred.", "Unreadable encrypted sections are reported, not fabricated."]}
    report["files"] = {str(path.relative_to(output_directory)).replace("\\", "/"):
        {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
        for path in sorted(output_directory.rglob("*")) if path.is_file()}
    (output_directory / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--build", required=True)
    args = parser.parse_args()
    try:
        result = export(args.input, args.output_dir, args.build)
    except (OSError, ValueError, struct.error) as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps(result, ensure_ascii=True))
