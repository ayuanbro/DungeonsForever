"""Evidence-backed regular material vendors; callers own final publication.

ItemSparse prices never imply availability. Discovery is deliberately bounded to
the documented seed items: a newly introduced merchant selling none of these
items needs an explicit registry entry. NPC shelves, including rejected rows,
are retained for audit. A failed refresh never reuses yesterday's eligibility.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
import argparse
import csv
import io
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

from fc_pipeline_common import (HERE, REPO, PipelineError, json_bytes,
                                publish_batch, require_repo_path, update_lock)
from fc_specialization_fetch import _Scripts, _listview_data, _challenge

SCHEMA_VERSION = 1
ORIGIN = "https://www.wowhead.com"
USER_AGENT = "DungeonsForeverDataPipeline/1.0"
SEEDS = (2320, 2324, 2604, 2678, 2880, 3371, 4289, 4399, 6217)
ROLES = frozenset(("profession_supply", "trade_supply", "reagent_supply",
                   "general_goods", "cooking_supply", "fishing_supply"))
MAX_BYTES = 16 * 1024 * 1024
DEFAULT_CONFIG = HERE / "_fc/maintenance/material-vendors.json"
DEFAULT_SNAPSHOT = HERE / "_fc/data/material-vendors.json"
DEFAULT_CACHE = HERE / "_fc/cache/material-vendors"
DEFAULT_LUA = REPO / "Core/Data/Data_ProfMaterialSupply.lua"
DEFAULT_PRICES = HERE / "_fc/inputs/client/item-buy-prices.csv"
DEFAULT_CATALOG = HERE / "_fc/data/catalog"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def digest(content):
    return sha256(content).hexdigest()


def integer(value, minimum=0):
    return type(value) is int and minimum <= value <= 2147483647


def read_input(path, options):
    path = require_repo_path(path)
    overrides = getattr(options, "input_overrides", {}) or {}
    content = overrides.get(path, overrides.get(str(path)))
    return content if content is not None else path.read_bytes() if path.exists() else None


def atomic_write(path, content):
    path = require_repo_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_nlink > 1:
        raise PipelineError("material cache must not be a hard link: %s" % path)
    temporary = require_repo_path(path.with_name(path.name + ".%s.tmp" % os.getpid()))
    if temporary.exists() and temporary.stat().st_nlink > 1:
        raise PipelineError("material cache temporary path must not be a hard link")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_url(url, kind=None, entity=None):
    parsed = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(parsed.path)
    if parsed.scheme != "https" or parsed.netloc != "www.wowhead.com" or parsed.query or parsed.fragment:
        raise PipelineError("material source must use fixed Wowhead HTTPS origin")
    if path == "/robots.txt" and kind is None:
        return
    match = re.fullmatch(r"/forever/(item|npc)=(\d+)(?:/[a-z0-9-]+)?/?", path)
    if not match or kind and match[1] != kind or entity and int(match[2]) != entity:
        raise PipelineError("unexpected material source URL: %s" % url)


def entity_url(kind, entity):
    if kind not in ("item", "npc") or not integer(entity, 1):
        raise PipelineError("invalid material entity")
    return ORIGIN + "/forever/%s=%s" % (kind, entity)


def page_meta(html, kind, entity):
    if not isinstance(html, str) or _challenge(html.encode("utf-8")):
        raise PipelineError("robot verification or invalid material source page")
    if not re.search(r"</html\s*>", html, re.I):
        raise PipelineError("truncated material source HTML")
    scripts = _Scripts()
    scripts.feed(html)
    metas = [text for attrs, text in scripts.scripts if attrs.get("id") == "data.pageMeta"]
    if len(metas) != 1:
        raise PipelineError("material source page metadata missing or duplicated")
    try:
        meta = json.loads(metas[0])
        env = meta["dataEnv"]["env"]
    except (ValueError, TypeError, KeyError) as exc:
        raise PipelineError("invalid material source page metadata") from exc
    if env != 16 or meta.get("page") != kind:
        raise PipelineError("material source is not the requested Forever page")
    identity = re.search(r"\bvar\s+g_pageInfo\s*=\s*\{[^}]*\btypeId\s*:\s*(\d+)", html)
    if not identity or int(identity[1]) != entity:
        raise PipelineError("material source entity mismatch")
    return scripts, {"gameFlavor": "forever", "sourceBuild": "",
                     "sourcePatch": str(meta.get("dataEnv", {}).get("versions", {}).get("16", "")),
                     "serverTime": str(meta.get("serverTime", ""))}


def listview(html, kind, entity, list_id, template):
    scripts, meta = page_meta(html, kind, entity)
    try:
        rows = _listview_data(scripts.scripts, list_id, template)
    except (ValueError, RuntimeError) as exc:
        raise PipelineError("invalid material Listview: %s" % exc) from exc
    if rows is None:
        raise PipelineError("material Listview %s missing (not a confirmed empty shelf)" % list_id)
    # A Listview containing a valid prefix of a capped server result is not full.
    for _, script in scripts.scripts:
        if re.search(r"\bid\s*:\s*['\"]%s['\"]" % re.escape(list_id), script):
            for match in re.finditer(r"\b(?:totalCount|totalItems|nItems|total)\s*:\s*(\d+)", script):
                if int(match[1]) > len(rows):
                    raise PipelineError("material Listview is a truncated result")
    if re.search(r"\d[\d,]*\s+\w+\s+found\s*\([^)]*displayed\)|Try filtering your results", html, re.I):
        raise PipelineError("material source reports capped results")
    return rows, meta


def role_from_tag(tag, aliases=None):
    tag = re.sub(r"\s+", " ", unescape(str(tag or ""))).strip().lower()
    if aliases is not None:
        return next((role for role, values in aliases.items() if tag in [x.strip().lower() for x in values]), None)
    if re.fullmatch(r"(?:alchemy|blacksmithing|engineering|enchanting|leatherworking|tailoring|mining|herbalism)(?:\s*&\s*(?:tailoring|leatherworking))?\s+(?:supplies|supplier)", tag):
        return "profession_supply"
    if tag in ("trade supplies", "trade supplier", "trade goods", "trade goods supplies", "general trade goods merchant", "general & trade supplies"):
        return "trade_supply"
    if tag in ("reagents", "reagent vendor", "reagent supplies", "reagent supplier"):
        return "reagent_supply"
    if tag in ("general goods", "general supplies", "general goods merchant", "general supplier"):
        return "general_goods"
    if tag in ("cooking supplies", "cooking supplier"):
        return "cooking_supply"
    if tag in ("fishing supplies", "fishing supplier"):
        return "fishing_supply"
    return None


def side_from_react(react):
    if not isinstance(react, list) or len(react) != 2 or any(x is not None and type(x) not in (int, float) for x in react):
        return None
    friendly = [type(x) in (int, float) and x > 0 for x in react]
    return "n" if all(friendly) else "a" if friendly[0] else "h" if friendly[1] else None


def discovery_page(html, item_id):
    rows, meta = listview(html, "item", item_id, "sold-by", "npc")
    found = []
    for row in rows:
        if not integer(row.get("id"), 1):
            raise PipelineError("invalid discovered material NPC ID")
        found.append({"id": row["id"], "name": str(row.get("name") or row.get("displayName") or ""),
                      "tag": str(row.get("tag") or ""), "side": side_from_react(row.get("react")),
                      "seedItemID": item_id})
    return found, meta


def npc_metadata(html, npc_id):
    pattern = r"\$\.extend\(g_npcs\[%d\],\s*" % npc_id
    match = re.search(pattern, html)
    if not match:
        raise PipelineError("NPC source properties are missing")
    try:
        value, _ = json.JSONDecoder().raw_decode(html[match.end():])
    except ValueError as exc:
        raise PipelineError("NPC source properties are invalid") from exc
    if not isinstance(value, dict) or value.get("id") != npc_id:
        raise PipelineError("NPC source property identity mismatch")
    return value


def cost_info(value):
    if value in (None, []):
        return "unknown", None
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], list) or not 1 <= len(value[0]) <= 3:
        return "unknown", None
    option = value[0]
    if any(not isinstance(x, list) for x in option[1:]):
        return "unknown", None
    if any(bool(x) for x in option[1:]):
        return "mixed" if integer(option[0], 1) else "token", None
    return ("gold", option[0]) if integer(option[0], 0) else ("unknown", None)


def same_source_bundle(row):
    stack = row.get("stack")
    # NPC sells embeds exactly one transaction quantity. Multiple alternatives
    # and unknown quantities must never be paired with a convenient price.
    return stack[0] if isinstance(stack, list) and len(stack) == 1 and integer(stack[0], 1) else None


def restrictions(record):
    reasons = []
    if "standing" in record and record["standing"] not in (0, None):
        reasons.append("reputation_requirement")
    for key in ("condition", "conditions", "requirements", "restrictions", "requiredQuest", "requiredQuestID", "quest", "event", "holiday", "requiredFaction", "requiredSkill", "reqskill", "reqskillrank", "reqclass", "reqrace"):
        if record.get(key) not in (None, False, 0, "", [], {}):
            reasons.append("condition:" + key)
    return reasons


def shelf_page(html, npc_id, override=None, role_aliases=None):
    rows, meta = listview(html, "npc", npc_id, "sells", "item")
    npc = npc_metadata(html, npc_id)
    tag, role = str(npc.get("tag") or ""), role_from_tag(npc.get("tag"), role_aliases)
    override = override or {}
    if override.get("role"):
        if override["role"] not in ROLES or not str(override.get("reason") or "").strip():
            raise PipelineError("manual NPC role requires an allowed role and evidence reason")
        role = override["role"]
    metadata = {"id": npc_id, "name": str(npc.get("name") or npc.get("displayName") or ""),
                "tag": tag, "role": role, "roleEvidence": "manual_registry" if override.get("role") else "npc_page_tag",
                "side": side_from_react(npc.get("react")), "location": npc.get("location", []),
                "rawReact": npc.get("react"),
                "conditions": restrictions(npc), **meta}
    ids = set()
    for row in rows:
        if not integer(row.get("id"), 1) or row["id"] in ids:
            raise PipelineError("invalid or duplicate material shelf item")
        ids.add(row["id"])
    return metadata, rows


def read_prices(content):
    if content is None:
        raise PipelineError("material client price CSV is missing")
    result = {}
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    required = {"ItemID", "BuyPriceCopper", "VendorStackCount", "PriceStatus"}
    if not required.issubset(reader.fieldnames or []):
        raise PipelineError("material client price CSV columns missing")
    for raw in reader:
        try:
            item_id = int(raw["ItemID"])
        except (TypeError, ValueError) as exc:
            raise PipelineError("invalid material client item ID") from exc
        if item_id in result or not integer(item_id, 1):
            raise PipelineError("duplicate/invalid material client item ID")
        price = quantity = None
        if raw["PriceStatus"] == "priced":
            try:
                price, quantity = int(raw["BuyPriceCopper"]), int(raw["VendorStackCount"])
            except (TypeError, ValueError):
                pass
        result[item_id] = {"price": price if integer(price, 1) else None,
                           "quantity": quantity if integer(quantity, 1) else None,
                           "build": raw.get("Build", ""), "hotfixBuild": raw.get("HotfixBuild", "")}
    return result


def eligible_offers(snapshot, prices):
    offers, rejected = {}, {}
    for key, shelf in sorted(snapshot.get("shelves", {}).items(), key=lambda kv: int(kv[0])):
        npc_id = int(key)
        if shelf.get("status") != "ok":
            continue
        npc, evidence = shelf.get("npc", {}), shelf.get("evidence", {})
        for row in shelf.get("rows", []):
            item_id = row.get("id")
            reasons = list(npc.get("conditions") or []) + restrictions(row)
            if npc.get("role") not in ROLES:
                reasons.append("unrecognized_supplier_role")
            if npc.get("side") not in ("a", "h", "n"):
                reasons.append("unknown_npc_access")
            side = npc.get("side")
            if "react" in row:
                row_side = side_from_react(row["react"])
                allowed = {"a", "h"} if side == "n" else {side}
                allowed &= {"a", "h"} if row_side == "n" else {row_side}
                allowed.discard(None)
                if not allowed:
                    reasons.append("item_access_not_friendly")
                else:
                    side = "n" if len(allowed) == 2 else next(iter(allowed))
            # In the sells JSON source contract, standing=0 explicitly states
            # no reputation threshold. Missing/null is unknown, never zero.
            if type(row.get("standing")) is not int or row.get("standing") != 0:
                reasons.append("unknown_or_restricted_standing")
            if row.get("avail") != -1 or type(row.get("avail")) is not int:
                reasons.append("limited_or_unknown_stock")
            quantity = same_source_bundle(row)
            if quantity is None:
                reasons.append("unknown_same_source_bundle")
            kind, price = cost_info(row.get("cost"))
            price_source = "wowhead_npc_bundle"
            explicit_gold = (row.get("goldOnly") is True and row.get("cost") in (None, [])) or (
                isinstance(row.get("cost"), list) and len(row["cost"]) == 1
                and isinstance(row["cost"][0], list) and len(row["cost"][0]) == 3
                and row["cost"][0][0] is None and row["cost"][0][1:] == [[], []])
            if kind == "unknown" and explicit_gold:
                client = prices.get(item_id, {})
                # The shelf still must explicitly establish no token cost;
                # a known empty currency/item pair permits client fallback.
                if quantity is not None and quantity == client.get("quantity"):
                    price, kind = client.get("price"), "gold"
                    price_source = "client_base_bundle"
            if kind != "gold" or not integer(price, 0):
                reasons.append("non_gold_or_unknown_price")
            if not all(evidence.get(k) for k in ("sourceURL", "verifiedAt", "evidenceHash")):
                reasons.append("missing_provenance")
            if reasons:
                rejected["%s:%s" % (npc_id, item_id)] = sorted(set(reasons))
                continue
            offer = {"eligible": True, "stockState": "unlimited", "costKind": "gold", "access": "unconditional",
                     "role": npc["role"], "side": side, "price": price, "quantity": quantity,
                     "priceSource": price_source, "sourceURL": evidence["sourceURL"],
                     "verifiedAt": evidence["verifiedAt"], "evidenceHash": evidence["evidenceHash"]}
            offers.setdefault(item_id, {"offers": {}})["offers"][npc_id] = offer
    return offers, rejected


def validate_snapshot(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get("schemaVersion") != 1 or snapshot.get("gameFlavor") != "forever":
        raise PipelineError("unsupported material snapshot schema/environment")
    if not isinstance(snapshot.get("registry"), dict) or not isinstance(snapshot.get("shelves"), dict):
        raise PipelineError("material snapshot registry/shelves missing")
    for key, entry in snapshot["registry"].items():
        if not isinstance(key, str) or not key.isdigit() or not integer(int(key), 1) or not isinstance(entry, dict) or entry.get("id") != int(key):
            raise PipelineError("invalid material snapshot registry identity")
    for key, shelf in snapshot["shelves"].items():
        if not isinstance(key, str) or not key.isdigit() or not integer(int(key), 1) or not isinstance(shelf, dict):
            raise PipelineError("invalid material snapshot NPC")
        if shelf.get("status") not in ("ok", "failed", "disabled"):
            raise PipelineError("invalid material snapshot shelf status")
        if key not in snapshot["registry"]:
            raise PipelineError("material shelf NPC missing from registry")
        if shelf["status"] != "ok":
            if not isinstance(shelf.get("reason"), str) or not shelf["reason"].strip():
                raise PipelineError("failed/disabled material shelf requires a reason")
            continue
        npc, evidence = shelf.get("npc"), shelf.get("evidence")
        if not isinstance(npc, dict) or npc.get("id") != int(key) or not isinstance(evidence, dict):
            raise PipelineError("material snapshot NPC/evidence identity mismatch")
        validate_url(evidence.get("sourceURL", ""), "npc", int(key))
        if not isinstance(npc.get("conditions"), list) or any(not isinstance(x, str) for x in npc["conditions"]):
            raise PipelineError("invalid material snapshot condition evidence")
        if not isinstance(evidence.get("verifiedAt"), str):
            raise PipelineError("invalid material snapshot verification time")
        try:
            datetime.fromisoformat(evidence["verifiedAt"].replace("Z", "+00:00"))
        except (KeyError, ValueError, TypeError) as exc:
            raise PipelineError("invalid material snapshot verification time") from exc
        if not re.fullmatch(r"[0-9a-f]{64}", str(evidence.get("evidenceHash", ""))):
            raise PipelineError("invalid material snapshot evidence hash")
        if evidence.get("rawPath") is not None:
            if not isinstance(evidence["rawPath"], str):
                raise PipelineError("invalid material raw evidence reference")
            require_repo_path(REPO / evidence["rawPath"])
        rows = shelf.get("rows")
        if not isinstance(rows, list) or any(not isinstance(row, dict) or not integer(row.get("id"), 1) for row in rows):
            raise PipelineError("invalid material snapshot rows")
        if len({row["id"] for row in rows}) != len(rows):
            raise PipelineError("duplicate material snapshot row")
    return snapshot


def reparse_snapshot(snapshot, config):
    """Reapply parser/alias changes to authenticated raw bytes without requests.

    Exported normalized snapshots remain replayable when raw cache is absent;
    when raw bytes are present their declared SHA must match before reuse.
    """
    for key, shelf in snapshot.get("shelves", {}).items():
        if shelf.get("status") != "ok":
            continue
        evidence = shelf.get("evidence", {})
        raw_ref = evidence.get("rawPath")
        if not raw_ref:
            continue
        raw_path = require_repo_path(REPO / raw_ref)
        if not raw_path.exists():
            continue
        content = raw_path.read_bytes()
        if digest(content) != evidence.get("evidenceHash"):
            raise PipelineError("material raw evidence hash mismatch: %s" % raw_path)
        npc, rows = shelf_page(content.decode("utf-8"), int(key), config.get("npcs", {}).get(key), config.get("roleAliases"))
        shelf["npc"], shelf["rows"] = npc, rows
        snapshot["registry"][key].update({name: npc[name] for name in ("name", "tag", "role", "side", "rawReact", "location")})
        snapshot["registry"][key].update({"status": "ok", "lastSuccessAt": evidence["verifiedAt"],
                                           "lastEvidenceHash": evidence["evidenceHash"]})
    return snapshot


def lua_value(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "nil"
    if type(value) is int:
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        return "{" + ",".join("[%s]=%s" % (lua_value(k), lua_value(v)) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))) + "}"
    raise PipelineError("unsupported material Lua value")


def generate(snapshot, prices):
    offers, rejected = eligible_offers(snapshot, prices)
    semantic = {str(item): {str(npc): {k: v for k, v in offer.items() if k not in ("verifiedAt", "evidenceHash")}
                            for npc, offer in row["offers"].items()} for item, row in offers.items()}
    fingerprint = digest(json_bytes(semantic))
    meta = {"schemaVersion": 1, "fingerprint": fingerprint, "gameFlavor": "forever",
            "scope": "seed_discovered_and_manually_registered_regular_suppliers", "complete": False}
    lines = ["-- Generated by fc_material_vendors.py; do not edit.", "local _, ns = ...",
             "ns.ProfMaterialSupplyMeta = " + lua_value(meta), "ns.ProfMaterialSupply = {"]
    lines += ["  [%d] = %s," % (item, lua_value(row)) for item, row in sorted(offers.items())]
    lines += ["}", ""]
    snapshot["eligibility"] = {"fingerprint": fingerprint, "items": len(offers),
                               "offers": sum(len(x["offers"]) for x in offers.values()), "rejected": rejected,
                               "offerPrices": {"%s:%s" % (item, npc): {"price": offer["price"], "quantity": offer["quantity"], "priceSource": offer["priceSource"]}
                                               for item, row in offers.items() for npc, offer in row["offers"].items()}}
    return "\n".join(lines).encode("utf-8")


class PageClient:
    """Sequential, bounded public-page requests; never stealth or challenge solving."""
    def __init__(self, cache_root, provider="auto", proxy=None, delay=3.0, chrome_profile=None,
                 chrome_cdp_url=None, headless=True, channel="chrome"):
        self.root = require_repo_path(cache_root)
        self.provider, self.proxy, self.delay = provider, proxy, max(3.0, float(delay))
        self.profile = require_repo_path(chrome_profile or self.root / "chrome-profile")
        if provider not in ("auto", "http", "chrome"):
            raise PipelineError("unknown material source provider")
        if chrome_cdp_url:
            parsed = urllib.parse.urlsplit(chrome_cdp_url)
            if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost") or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
                raise PipelineError("existing material Chrome must use a local debugging endpoint")
        if channel not in ("chrome", "msedge"):
            raise PipelineError("material browser channel must be chrome or msedge")
        self.cdp_url, self.headless, self.channel, self.owned_context = chrome_cdp_url, headless, channel, True
        self.last_request, self.blocked, self.robots = 0.0, None, None
        self.context = self.browser = self.playwright = self.page = None

    def _http(self, url):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args):
                return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy} if self.proxy else {}), NoRedirect())
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/plain" if url.endswith("robots.txt") else "text/html"})
        with opener.open(request, timeout=35) as response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise PipelineError("material source response exceeds size limit")
            return raw.decode("utf-8-sig"), response.geturl()

    def _browser(self, url):
        if self.page is None:
            from playwright.sync_api import sync_playwright
            self.playwright = sync_playwright().start()
            if self.cdp_url:
                self.browser = self.playwright.chromium.connect_over_cdp(self.cdp_url)
                self.context = self.browser.contexts[0]
                self.owned_context = False
            else:
                self.profile.mkdir(parents=True, exist_ok=True)
                kwargs = {"channel": self.channel, "headless": self.headless, "viewport": {"width": 1280, "height": 900}}
                if not self.headless:
                    kwargs["args"] = ["--window-position=3200,0", "--window-size=1280,900", "--no-first-run", "--no-default-browser-check"]
                if self.proxy:
                    kwargs["proxy"] = {"server": self.proxy}
                self.context = self.playwright.chromium.launch_persistent_context(str(self.profile), **kwargs)
            self.page = self.context.new_page()
            self.page.route("**/*", lambda route: route.abort() if route.request.resource_type in ("image", "font", "media") else route.continue_())
        response = self.page.goto(url, wait_until="domcontentloaded", timeout=45000)
        self.page.wait_for_timeout(1200)
        if response and response.status in (403, 429):
            self.blocked = "material source HTTP %s; remainder of batch downgraded without challenge bypass" % response.status
            raise PipelineError(self.blocked)
        return self.page.content(), self.page.url

    def _wait(self):
        wait = self.last_request + self.delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.last_request = time.monotonic()

    def fetch(self, kind, entity):
        url = entity_url(kind, entity)
        if self.blocked:
            raise PipelineError(self.blocked)
        if self.robots is None:
            try:
                text, _ = self._http(ORIGIN + "/robots.txt")
            except Exception as exc:
                self.blocked = "material source robots policy unavailable: %s" % exc
                raise PipelineError(self.blocked) from exc
            if "user-agent:" not in text.lower() or "<html" in text.lower():
                raise PipelineError("material source robots policy unavailable")
            self.robots = urllib.robotparser.RobotFileParser()
            self.robots.parse(text.splitlines())
            self.delay = max(self.delay, float(self.robots.crawl_delay(USER_AGENT) or 0))
        if not self.robots.can_fetch(USER_AGENT, url):
            raise PipelineError("material source robots policy disallows page")
        self._wait()
        provider = self.provider
        if provider == "auto":
            try:
                import playwright.sync_api
                provider = "chrome"
            except ImportError:
                provider = "http"
        try:
            html, final = self._browser(url) if provider == "chrome" else self._http(url)
            validate_url(final, kind, entity)
            if _challenge(html.encode("utf-8")):
                self.blocked = "material source robot verification; remainder of batch downgraded"
                raise PipelineError(self.blocked)
            content = html.encode("utf-8")
            evidence_hash = digest(content)
            raw_path = require_repo_path(self.root / "raw" / (evidence_hash + ".html"))
            if not raw_path.exists():
                atomic_write(raw_path, content)
            evidence = {"sourceURL": url, "verifiedAt": now(), "evidenceHash": evidence_hash,
                        "rawPath": str(raw_path.relative_to(REPO)), "transport": provider,
                        "gameFlavor": "forever", "sourceBuild": ""}
            return html, evidence
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429):
                self.blocked = "material source HTTP %s; remainder of batch downgraded" % exc.code
            raise PipelineError(str(exc)) from exc

    def close(self):
        if self.context is not None and self.owned_context:
            self.context.close()
        elif self.page is not None:
            self.page.close()
        if self.playwright is not None:
            self.playwright.stop()


def validate_config(config):
    allowed = {"schemaVersion", "gameFlavor", "provider", "channel", "headless", "proxy", "chromeCDPURL", "requestDelaySeconds", "seedItemIDs", "npcs", "roleAliases", "notes"}
    if set(config) - allowed:
        raise PipelineError("unknown material maintenance fields: %s" % sorted(set(config) - allowed))
    if config.get("schemaVersion") != 1 or config.get("gameFlavor") != "forever":
        raise PipelineError("unsupported material vendor maintenance schema")
    seeds = config.get("seedItemIDs", list(SEEDS))
    if not isinstance(seeds, list) or not seeds or any(not integer(x, 1) for x in seeds) or len(seeds) != len(set(seeds)):
        raise PipelineError("invalid material discovery seed list")
    npcs = config.get("npcs", {})
    if not isinstance(npcs, dict):
        raise PipelineError("material NPC maintenance entries must be keyed by ID")
    for key, entry in npcs.items():
        if not key.isdigit() or not integer(int(key), 1) or not isinstance(entry, dict):
            raise PipelineError("invalid material maintenance NPC")
        if "role" in entry and (entry["role"] not in ROLES or not isinstance(entry.get("reason"), str) or not entry["reason"].strip()):
            raise PipelineError("material maintenance role requires a reason")
        if set(entry) - {"enabled", "role", "reason", "name", "sourceURL"}:
            raise PipelineError("unknown material maintenance NPC fields")
        if "enabled" in entry and type(entry["enabled"]) is not bool:
            raise PipelineError("material maintenance enabled must be boolean")
        if entry.get("enabled") is False and (not isinstance(entry.get("reason"), str) or not entry["reason"].strip()):
            raise PipelineError("disabled material NPC requires a reason")
        if "sourceURL" in entry:
            validate_url(entry["sourceURL"], "npc", int(key))
    aliases = config.get("roleAliases")
    if aliases is not None:
        if not isinstance(aliases, dict) or set(aliases) != ROLES:
            raise PipelineError("material role aliases must define exactly the six allowed roles")
        seen = set()
        for role, tags in aliases.items():
            if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag.strip() for tag in tags):
                raise PipelineError("invalid material role alias")
            for tag in tags:
                tag = tag.strip().lower()
                if tag in seen:
                    raise PipelineError("duplicate material role alias")
                seen.add(tag)
    return config


def evidence_observations(snapshot):
    observed = {}
    records = list(snapshot.get("discovery", {}).values()) + list(snapshot.get("shelves", {}).values())
    for record in records:
        evidence = record.get("evidence", {}) if record.get("status") == "ok" else record.get("failedEvidence", {})
        raw_ref = evidence.get("rawPath")
        if not raw_ref:
            continue
        if not isinstance(raw_ref, str):
            raise PipelineError("invalid material raw evidence reference")
        path = require_repo_path(REPO / raw_ref)
        if not path.is_file():
            continue
        content = path.read_bytes()
        if digest(content) != evidence.get("evidenceHash"):
            raise PipelineError("material raw evidence changed during preparation: %s" % path)
        observed[path] = {"role": "material_raw_evidence", "path": str(path), "sha256": digest(content)}
    return list(observed.values())


def offer_delta(previous, current, prices):
    def flatten(value):
        offers, _ = eligible_offers(value, prices)
        return {"%s:%s" % (item, npc): {"price": offer["price"], "quantity": offer["quantity"], "priceSource": offer["priceSource"]}
                for item, row in offers.items() for npc, offer in row["offers"].items()}
    old = previous.get("eligibility", {}).get("offerPrices")
    old = old if isinstance(old, dict) else flatten(previous)
    new = flatten(current)
    return {"addedOffers": sorted(set(new) - set(old)), "removedOffers": sorted(set(old) - set(new)),
            "changedPrices": [{"offer": key, "before": old[key], "after": new[key]}
                              for key in sorted(set(old) & set(new)) if old[key] != new[key]]}


def collect(config, previous, client, report=None):
    snapshot = {"schemaVersion": 1, "generatedAt": now(), "gameFlavor": "forever", "sourceBuild": "",
                "discovery": {}, "registry": dict(previous.get("registry", {})), "shelves": {},
                "coverage": {"complete": False, "scope": "seed_items_and_manual_npcs", "failedSeeds": [], "failedNPCs": []}}
    for item_id in config.get("seedItemIDs", SEEDS):
        evidence = None
        try:
            html, evidence = client.fetch("item", item_id)
            rows, meta = discovery_page(html, item_id)
            snapshot["discovery"][str(item_id)] = {"status": "ok", "npcIDs": [row["id"] for row in rows], "evidence": {**evidence, **meta}}
            for row in rows:
                key = str(row["id"])
                old = snapshot["registry"].get(key, {})
                snapshot["registry"][key] = {**old, **row, "firstSeenAt": old.get("firstSeenAt") or evidence["verifiedAt"],
                                             "discoveredFrom": sorted(set(old.get("discoveredFrom", []) + [item_id]))}
        except Exception as exc:
            snapshot["discovery"][str(item_id)] = {"status": "failed", "reason": str(exc)[:500]}
            if evidence:
                snapshot["discovery"][str(item_id)]["failedEvidence"] = evidence
            snapshot["coverage"]["failedSeeds"].append(item_id)
        if callable(report):
            report("material discovery item %s: %s" % (item_id, snapshot["discovery"][str(item_id)]["status"]))
    for key in config.get("npcs", {}):
        snapshot["registry"].setdefault(key, {"id": int(key), "discoveredFrom": [], "manual": True})
    for key in sorted(snapshot["registry"], key=int):
        npc_id = int(key)
        override = config.get("npcs", {}).get(key, {})
        snapshot["registry"][key]["lastAttemptAt"] = now()
        if override.get("enabled", True) is False:
            snapshot["shelves"][key] = {"status": "disabled", "reason": override.get("reason", "maintenance disabled")}
            snapshot["registry"][key]["status"] = "disabled"
            snapshot["registry"][key]["disabledReason"] = override.get("reason", "maintenance disabled")
            continue
        snapshot["registry"][key].pop("disabledReason", None)
        evidence = None
        try:
            html, evidence = client.fetch("npc", npc_id)
            metadata, rows = shelf_page(html, npc_id, override, config.get("roleAliases"))
            snapshot["shelves"][key] = {"status": "ok", "npc": metadata, "rows": rows, "evidence": evidence}
            snapshot["registry"][key].update({k: metadata[k] for k in ("name", "tag", "role", "side", "rawReact", "location")})
            snapshot["registry"][key].update({"status": "ok", "lastSuccessAt": evidence["verifiedAt"], "lastEvidenceHash": evidence["evidenceHash"]})
        except Exception as exc:
            old = previous.get("shelves", {}).get(key, {})
            snapshot["shelves"][key] = {"status": "failed", "reason": str(exc)[:500],
                                        "previousEvidence": old.get("evidence") or old.get("previousEvidence"),
                                        "previousRowCount": len(old.get("rows", [])) or old.get("previousRowCount", 0)}
            if evidence:
                snapshot["shelves"][key]["failedEvidence"] = evidence
            snapshot["coverage"]["failedNPCs"].append(npc_id)
            snapshot["registry"][key]["status"] = "failed"
        if callable(report):
            report("material NPC %s: %s" % (npc_id, snapshot["shelves"][key]["status"]))
    snapshot["coverage"].update({"registeredNPCs": len(snapshot["registry"]),
                                   "successfulNPCs": sum(x["status"] == "ok" for x in snapshot["shelves"].values())})
    return snapshot


def prepare_batch(options, report=None):
    """Return ({absolute destination: bytes}, input observations), no final writes."""
    paths = {"config": require_repo_path(getattr(options, "material_config", None) or DEFAULT_CONFIG),
             "snapshot": require_repo_path(getattr(options, "material_snapshot", None) or DEFAULT_SNAPSHOT),
             "prices": require_repo_path(getattr(options, "prices_csv", None) or DEFAULT_PRICES),
             "lua": require_repo_path(getattr(options, "material_output_lua", None) or DEFAULT_LUA),
             "cache": require_repo_path(getattr(options, "material_cache_root", None) or DEFAULT_CACHE)}
    if len(set(paths.values())) != len(paths):
        raise PipelineError("material inputs/outputs/cache must be distinct")
    contents = {key: read_input(paths[key], options) for key in ("config", "snapshot", "prices")}
    if contents["config"] is None:
        raise PipelineError("material maintenance config is missing")
    try:
        config = validate_config(json.loads(contents["config"]))
        previous = json.loads(contents["snapshot"]) if contents["snapshot"] is not None else {}
    except (ValueError, TypeError) as exc:
        raise PipelineError("invalid material config/snapshot JSON") from exc
    if previous:
        validate_snapshot(previous)
    previous_baseline = json.loads(json.dumps(previous))
    prices = read_prices(contents["prices"])
    if getattr(options, "offline", False):
        if not previous:
            raise PipelineError("offline material update requires a normalized snapshot")
        snapshot = reparse_snapshot(previous, config)
    else:
        supplied = getattr(options, "material_client", None)
        client = supplied or PageClient(paths["cache"],
            getattr(options, "material_provider", None) or config.get("provider", "auto"),
            getattr(options, "material_proxy", None) or config.get("proxy"),
            config.get("requestDelaySeconds", 3), getattr(options, "material_chrome_profile", None),
            getattr(options, "material_chrome_cdp_url", None) or config.get("chromeCDPURL"),
            config.get("headless", os.name != "nt") if getattr(options, "material_headless", None) is None else options.material_headless,
            getattr(options, "material_channel", None) or config.get("channel", "chrome"))
        with update_lock(paths["cache"] / ".collect.lock"):
            try:
                progress = getattr(options, "material_progress", None)
                snapshot = collect(config, previous, client, progress if callable(progress) else report)
            finally:
                if not supplied:
                    try:
                        client.close()
                    except Exception as exc:
                        if "snapshot" in locals():
                            snapshot["coverage"]["cleanupWarning"] = str(exc)[:200]
    validate_snapshot(snapshot)
    # Maintenance exclusions also apply to explicitly requested offline replay.
    for key, override in config.get("npcs", {}).items():
        if override.get("enabled", True) is False and key in snapshot["shelves"]:
            snapshot["shelves"][key] = {"status": "disabled", "reason": override.get("reason", "maintenance disabled")}
    lua = generate(snapshot, prices)
    delta = offer_delta(previous_baseline, snapshot, prices)
    raw_observations = evidence_observations(snapshot)
    coverage_observations = []
    if getattr(options, "data_dir", None) is not None:
        from fc_material_coverage import reagent_coverage
        coverage, coverage_observations = reagent_coverage(require_repo_path(options.data_dir), eligible_offers(snapshot, prices)[0])
    else:
        coverage = {"status": "not_evaluated", "reason": "catalog not supplied"}
    snapshot.setdefault("coverage", {})["reagents"] = coverage
    snapshot_bytes = json_bytes(snapshot)
    if not getattr(options, "offline", False):
        history = paths["cache"] / "history" / (snapshot["generatedAt"].replace(":", "") + "-" + digest(snapshot_bytes)[:12] + ".json")
        atomic_write(history, snapshot_bytes)
    observations = [{"role": "material_" + key, "path": str(paths[key]), "sha256": digest(content) if content is not None else None}
                    for key, content in contents.items()]
    observations.extend(raw_observations)
    observations.extend(coverage_observations)
    outputs = {paths["snapshot"]: snapshot_bytes, paths["lua"]: lua}
    if isinstance(report, dict):
        report.update({"coverage": snapshot.get("coverage", {}), "eligibility": snapshot["eligibility"],
                       "sourceEnvironment": "forever", "sourceBuild": "", "snapshot": str(paths["snapshot"]),
                       "offline": bool(getattr(options, "offline", False)), "delta": delta,
                       "registry": snapshot.get("registry", {}), "reagentCoverage": coverage})
    return outputs, observations


def parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--material-config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--material-snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    ap.add_argument("--material-cache-root", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--material-output-lua", type=Path, default=DEFAULT_LUA)
    ap.add_argument("--prices-csv", type=Path, default=DEFAULT_PRICES)
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--material-provider", choices=("http", "chrome", "auto"))
    ap.add_argument("--material-proxy")
    ap.add_argument("--material-chrome-profile", type=Path)
    ap.add_argument("--material-chrome-cdp-url")
    ap.add_argument("--material-headless", action=argparse.BooleanOptionalAction, default=None)
    ap.add_argument("--material-channel", choices=("chrome", "msedge"))
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--apply", action="store_true")
    return ap


def main(argv=None):
    options = parser().parse_args(argv)
    outputs, _ = prepare_batch(options, print)
    snapshot = json.loads(outputs[options.material_snapshot.resolve()])
    print(json.dumps({"coverage": {k: v for k, v in snapshot["coverage"].items() if k != "reagents"},
                      "eligibleItems": snapshot["eligibility"]["items"], "eligibleOffers": snapshot["eligibility"]["offers"]}, ensure_ascii=False))
    if options.apply:
        publish_batch(outputs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
