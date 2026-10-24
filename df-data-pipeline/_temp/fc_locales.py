"""Render only profession locale overlays, preserving reviewed baseline text.

This module never publishes from render_locales. Maintenance records are keyed by
Lua table paths, with recipe IDs and trainer identities replacing array positions.
Enchant/BIS identities survive list reordering. A reviewed source revision must
match exactly before its preserved translation can be reused.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MAINTENANCE = HERE / "_fc/maintenance/locales.json"
FILES = (
    "Data_Professions.lua", "Data_ProfRecipes.lua", "Data_ProfLeveling.lua",
    "Data_ProfGathering.lua", "Data_ProfVendors.lua", "Data_ProfTrainers.lua",
)
LOCALES = ("enUS", "zhTW")
ROOT_TABLE = re.compile(
    r"(?P<name>ns\.\w+|PARTS\[\"[^\"]+\"\]|local\s+HAND)\s*=\s*"
    r"(?:function\s*\(\s*\)\s*return\s*)?(?P<brace>\{)"
)
NUMBER = re.compile(r"-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
IDENTIFIER = re.compile(r"[A-Za-z_]\w*")
BLOCK_COMMENT = re.compile(r"--\[(=*)\[")


class LocaleError(ValueError):
    def __init__(self, message, invalidated=None):
        super().__init__(message)
        self.invalidated = invalidated or []


@dataclass
class Token:
    kind: str
    raw: str
    start: int
    end: int
    value: object = None


@dataclass
class Table:
    fields: list


def _unquote(raw):
    text, out, i = raw[1:-1], [], 0
    escapes = {"a": "\a", "b": "\b", "f": "\f", "n": "\n",
               "r": "\r", "t": "\t", "v": "\v"}
    while i < len(text):
        if text[i] != "\\":
            out.append(text[i]); i += 1; continue
        i += 1
        if i == len(text):
            raise LocaleError("Unterminated Lua escape")
        if text[i].isdigit():
            m = re.match(r"\d{1,3}", text[i:])
            number = int(m[0])
            if number > 255:
                raise LocaleError("Lua decimal escape exceeds 255")
            out.append(chr(number)); i += len(m[0]); continue
        out.append(escapes.get(text[i], text[i])); i += 1
    return "".join(out)


def _quote(value, quote='"'):
    out = []
    for char in value:
        if char == "\\" or char == quote:
            out.append("\\" + char)
        elif char == "\n": out.append("\\n")
        elif char == "\r": out.append("\\r")
        elif char == "\t": out.append("\\t")
        elif ord(char) < 32: out.append("\\%03d" % ord(char))
        else: out.append(char)
    return quote + "".join(out) + quote


def _tokens(text):
    result, i = [], 0
    while i < len(text):
        if text[i].isspace(): i += 1; continue
        if text.startswith("--", i):
            block = BLOCK_COMMENT.match(text, i)
            if block:
                end = text.find("]" + block[1] + "]", i + len(block[0]))
                if end < 0: raise LocaleError("Unterminated Lua block comment")
                i = end + len(block[1]) + 2
            else:
                end = text.find("\n", i)
                i = len(text) if end < 0 else end + 1
            continue
        start = i
        if text[i] in "\"'":
            quote = text[i]; i += 1
            while i < len(text) and text[i] != quote:
                i += 2 if text[i] == "\\" else 1
            if i >= len(text): raise LocaleError("Unterminated Lua string")
            i += 1
            raw = text[start:i]
            result.append(Token("string", raw, start, i, _unquote(raw)))
            continue
        number = NUMBER.match(text, i)
        ident = IDENTIFIER.match(text, i)
        if number:
            i += len(number[0]); raw = number[0]
            result.append(Token("number", raw, start, i, raw)); continue
        if ident:
            i += len(ident[0]); raw = ident[0]
            result.append(Token("identifier", raw, start, i, raw)); continue
        i += 1
        result.append(Token("punct", text[start:i], start, i, text[start:i]))
    return result


def _parse_table(tokens, pos):
    fields, index = [], 1
    if tokens[pos].raw != "{": raise LocaleError("Expected Lua table")
    pos += 1
    while tokens[pos].raw != "}":
        key = index
        if tokens[pos].raw == "[":
            item = tokens[pos + 1]
            if item.kind not in ("string", "number") or tokens[pos + 2].raw != "]" or tokens[pos + 3].raw != "=":
                raise LocaleError("Unsupported dynamic Lua table key")
            key = ("key", item.value); pos += 4
        elif tokens[pos].kind == "identifier" and tokens[pos + 1].raw == "=":
            key = ("field", tokens[pos].value); pos += 2
        else:
            index += 1
        if tokens[pos].raw == "{":
            value, pos = _parse_table(tokens, pos)
        else:
            value = tokens[pos]
            if value.kind not in ("string", "number", "identifier"):
                raise LocaleError("Unsupported expression in profession data table")
            pos += 1
        fields.append((key, value))
        if tokens[pos].raw in (",", ";"): pos += 1
        elif tokens[pos].raw != "}": raise LocaleError("Unsupported Lua table expression")
    return Table(fields), pos + 1


def _roots(text):
    tokens = _tokens(text)
    positions = {token.start: i for i, token in enumerate(tokens)}
    roots = []
    for match in ROOT_TABLE.finditer(text):
        at = match.start("brace")
        if at not in positions: continue  # Matches inside comments/string literals.
        tree, _ = _parse_table(tokens, positions[at])
        roots.append((re.sub(r"\s+", "", match["name"]), tree))
    if not roots: raise LocaleError("No supported profession data tables found")
    return roots


def _identity(table, parent_path, identity_version=2):
    fields = dict(table.fields)
    def named(label):
        return fields.get(("field", label), fields.get(("key", label)))
    for label in ("id", "spell", "itemID", "npcID"):
        value = named(label)
        if isinstance(value, Token) and value.kind == "number":
            return label + "=" + str(value.value)
    en = named("en")
    if isinstance(en, Token) and en.kind == "string":
        parts = ["en=" + en.value]
        for label in ("rng", "map", "fac"):
            value = named(label)
            if isinstance(value, Token): parts.append(label + "=" + str(value.value))
        return "|".join(parts)
    first = fields.get(1)
    if identity_version >= 2:
        if parent_path.endswith("/enchants") and isinstance(first, Token) and first.kind == "string":
            return "enchant=" + first.value
        if "/enchants/" in parent_path and parent_path.endswith("/[13]"):
            second = fields.get(2)
            if all(isinstance(value, Token) and value.kind == "string" for value in (first, second)):
                return "bis=" + first.value + ":" + second.value
    if isinstance(first, Token) and first.kind == "number":
        return "id=" + str(first.value)
    if parent_path.endswith("/groups") and isinstance(first, Token) and first.kind == "string" and first.value.isascii():
        return "key=" + first.value
    return None


def _segment(key):
    if isinstance(key, tuple): return str(key[1])
    return "[" + str(key) + "]"


def _records(text, identity_version=2):
    records = {}
    def walk(table, path):
        identities = {}
        for key, value in table.fields:
            part = _segment(key)
            if isinstance(value, Table) and isinstance(key, int):
                identity = _identity(value, path, identity_version)
                if identity is not None:
                    count = identities.get(identity, 0) + 1
                    identities[identity] = count
                    if identity_version >= 2 and count > 1 and identity.startswith(("enchant=", "bis=")):
                        raise LocaleError("Ambiguous stable locale identity: " + path + "/" + identity)
                    part = "@" + identity + ("#" + str(count) if count > 1 else "")
            child = path + "/" + part.replace("~", "~0").replace("/", "~1")
            if isinstance(value, Table): walk(value, child)
            elif value.kind == "string":
                if child in records: raise LocaleError("Duplicate locale record: " + child)
                records[child] = value
    for name, tree in _roots(text): walk(tree, name)
    return records


def _text(raw):
    return raw.decode("utf-8-sig")


def _hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def capture_maintenance(baseline_dir: Path):
    """Read the six current source/locale triples without modifying any file."""
    result = {"schemaVersion": 2, "identityVersion": 2, "files": {}}
    baseline_dir = Path(baseline_dir)
    for name in FILES:
        source = baseline_dir / name
        if not source.exists(): continue
        records = _records(_text(source.read_bytes()))
        entries = {}
        for locale in LOCALES:
            path = baseline_dir / locale / name
            if not path.exists(): continue
            translated = _records(_text(path.read_bytes()))
            if records.keys() != translated.keys():
                raise LocaleError("Locale/source structure differs during maintenance capture: " + str(path))
            for key, token in records.items():
                other = translated[key]
                # Identical Chinese text can be intentional reviewed terminology
                # (e.g. 背包), or a typed zh/tw trainer field. Preserve it too.
                if other.value == token.value and not re.search(r"[\u3400-\u9fff]|BOSS", token.value): continue
                entry = entries.setdefault(key, {"source": token.value, "sourceSHA256": _hash(token.value), "translations": {}})
                entry["translations"][locale] = other.value
        result["files"][name] = entries
    return result


def migrate_maintenance(value, baseline_dir):
    """Rekey schema 1 records using their original baseline; preserve all text."""
    if value.get("schemaVersion") == 2:
        if value.get("identityVersion") != 2:
            raise LocaleError("Unsupported locale identity version")
        return copy.deepcopy(value)
    if value.get("schemaVersion") != 1:
        raise LocaleError("Unsupported locale maintenance schema")
    result = copy.deepcopy(value)
    for name, entries in value["files"].items():
        text = _text((Path(baseline_dir) / name).read_bytes())
        previous, current = _records(text, 1), _records(text, 2)
        current_by_offset = {token.start: key for key, token in current.items()}
        migrated = {}
        for key, entry in entries.items():
            if key not in previous or previous[key].value != entry["source"]:
                raise LocaleError("Legacy locale identity migration requires its matching baseline: " + name + ":" + key)
            new_key = current_by_offset[previous[key].start]
            if new_key in migrated:
                raise LocaleError("Locale identity migration collision: " + name + ":" + new_key)
            migrated[new_key] = copy.deepcopy(entry)
        result["files"][name] = migrated
    result["schemaVersion"], result["identityVersion"] = 2, 2
    return result


def _versions(entry):
    return [entry] + entry.get("history", [])


def _maintenance(path, baseline_dir):
    path = Path(path) if path is not None else MAINTENANCE
    if not path.exists(): return capture_maintenance(baseline_dir)
    result = json.loads(path.read_text(encoding="utf-8-sig"))
    if result.get("schemaVersion") not in (1, 2) or not isinstance(result.get("files"), dict):
        raise LocaleError("Unsupported locale maintenance schema: " + str(path))
    result = migrate_maintenance(result, baseline_dir)
    for name, entries in result["files"].items():
        if name not in FILES: raise LocaleError("Unowned locale maintenance file: " + name)
        for key, entry in entries.items():
            sources = set()
            for version in _versions(entry):
                if _hash(version["source"]) != version.get("sourceSHA256"):
                    raise LocaleError("Locale source hash mismatch: " + name + ":" + key)
                if version["source"] in sources:
                    raise LocaleError("Duplicate reviewed locale source revision: " + name + ":" + key)
                sources.add(version["source"])
                if not isinstance(version.get("translations"), dict) or any(
                        locale not in LOCALES or not isinstance(text, str)
                        for locale, text in version["translations"].items()):
                    raise LocaleError("Invalid reviewed locale translations: " + name + ":" + key)
    return result


def render_locales(base_outputs: dict[str, bytes], baseline_dir: Path,
                   maintenance_path=None) -> dict[str, bytes]:
    """Render owned overlays only. No directories or files are written here."""
    unknown = set(base_outputs) - set(FILES)
    if unknown: raise LocaleError("Locale generation does not own: " + ", ".join(sorted(unknown)))
    import fc_pipeline_common  # Registers the repository-local dependency directory.
    from gen_enus_data import translate
    from gen_zhtw import to_tw, require_opencc
    try:
        require_opencc()
    except (ImportError, RuntimeError) as exc:
        raise LocaleError("zhTW generation requires OpenCC; install the declared pipeline dependency: " + str(exc)) from exc
    maintenance = _maintenance(maintenance_path, baseline_dir)
    outputs, invalidated = {}, []
    for name, raw in sorted(base_outputs.items()):
        text = _text(raw)
        records = _records(text)
        preserved = maintenance["files"].get(name, {})
        for locale in LOCALES:
            replacements = []
            for key, token in records.items():
                entry = preserved.get(key)
                matched = next((version for version in _versions(entry) if version["source"] == token.value), None) if entry else None
                prior = matched["translations"].get(locale) if matched else None
                if entry and matched is None and locale in entry["translations"]:
                    invalidated.append({"file": name, "locale": locale, "record": key,
                                        "previousSource": entry["source"], "source": token.value,
                                        "previousTranslation": entry["translations"][locale]})
                    continue
                value = prior if prior is not None else (translate(token.value, name) if locale == "enUS" else to_tw(token.value))
                if value != token.value:
                    replacements.append((token.start, token.end, _quote(value, token.raw[0])))
            body = text
            for start, end, replacement in reversed(replacements):
                body = body[:start] + replacement + body[end:]
            newline = "\r\n" if "\r\n" in text else "\n"
            if locale == "enUS":
                head = 'local _, ns = ...\n\nif (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end\n'
            else:
                head = "local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'\nif gl ~= 'zhTW' then return end\n\n"
            outputs[locale + "/" + name] = (head.replace("\n", newline) + body).encode("utf-8")
    if invalidated:
        raise LocaleError("Existing translations have changed source text; update locale maintenance before publishing:\n" +
                          json.dumps(invalidated, ensure_ascii=False, indent=2), invalidated)
    return outputs


def _repo_output(path):
    path = Path(path).resolve()
    if not path.is_relative_to(REPO):
        raise LocaleError("Locale output must stay inside the Git checkout: " + str(path))
    return path


def locale_cli(locale, argv=None):
    parser = argparse.ArgumentParser(description="Render the six owned profession locale files only")
    parser.add_argument("--source-root", type=Path, default=REPO / "Core/Data", help="Directory containing base Data_Prof*.lua files")
    parser.add_argument("--output-root", type=Path, default=HERE.parent / "Core/Data", help="Data output directory; locale subdirectory is appended")
    parser.add_argument("--files", nargs="+", choices=FILES, default=list(FILES))
    parser.add_argument("--maintenance", type=Path, default=MAINTENANCE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        destination = _repo_output(args.output_root)
        sources = {name: (args.source_root / name).read_bytes() for name in args.files}
        outputs = render_locales(sources, REPO / "Core/Data", args.maintenance)
        pending = {}
        for relative, content in outputs.items():
            if not relative.startswith(locale + "/"): continue
            path = _repo_output(destination / relative)
            pending[path] = content
            print(("[DRY-RUN] " if args.dry_run else "[OK] ") + str(path))
        if not args.dry_run:
            from fc_pipeline_common import publish_batch
            publish_batch(pending)
    except (LocaleError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    locale_cli("enUS")
