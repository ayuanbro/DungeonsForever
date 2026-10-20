"""Fetch observable Forever trainer requirements without inferring missing ones.

Only public Wowhead pages are read. The encoded URLs are the public URLs verified
during source research; a denial never triggers an alternate URL or identity.
The website identifies a patch, not an exact client build. Its evidence must not
be presented as a matching-build client observation.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import random
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

from fc_pipeline_common import require_repo_path


ORIGIN = "https://www.wowhead.com"
USER_AGENT = "DungeonsForeverDataPipeline/1.0"
POLICY_DIR = Path(__file__).resolve().parent / "_fc/cache/specializations/.network-state"
DEFAULT_SKILLS = {
    171: "alchemy", 164: "blacksmithing", 333: "enchanting",
    202: "engineering", 182: "herbalism", 165: "leatherworking",
    186: "mining", 393: "skinning", 197: "tailoring",
    185: "cooking", 129: "first-aid", 356: "fishing",
}
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
CACHE_VERSION = 1


class FetchError(RuntimeError):
    """No replacement output should be published after this exception."""


class ValidationError(FetchError):
    pass


class CooldownError(FetchError):
    pass


def _now():
    return time.time()


def _iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _atomic_json(path, value):
    path = require_repo_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".%s.tmp" % os.getpid())
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


@contextmanager
def _network_lock():
    """OS releases this origin-wide lock after process exit, including crashes."""
    require_repo_path(POLICY_DIR)
    for name in ('fetch.lock', 'cooldown.json', 'request-clock.json', 'robots.json'):
        require_repo_path(POLICY_DIR / name)
    POLICY_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = require_repo_path(POLICY_DIR / "fetch.lock")
    if lock_path.exists() and lock_path.stat().st_nlink > 1:
        raise FetchError('network lock must not be a hard link')
    with lock_path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise FetchError("Another Wowhead specialization fetch is running.") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class _Scripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.scripts = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.current = [dict(attrs), []]

    def handle_data(self, data):
        if self.current is not None:
            self.current[1].append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.scripts.append((self.current[0], "".join(self.current[1])))
            self.current = None


def _js_segments(text, start=0, stop_at_closing=False):
    """Split top-level JS properties; do not interpret or execute their values."""
    stack, quote, escaped = [], None, False
    segment, i = start, start
    while i < len(text):
        char = text[i]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif text.startswith("//", i):
            newline = text.find("\n", i + 2)
            i = len(text) if newline < 0 else newline
            continue
        elif text.startswith("/*", i):
            closing = text.find("*/", i + 2)
            if closing < 0:
                raise ValidationError("Unterminated JavaScript comment.")
            i = closing + 2
            continue
        elif char in "\"'`":
            quote = char
        elif char in "[{(":
            stack.append({"[": "]", "{": "}", "(": ")"}[char])
        elif char in "]})":
            if not stack:
                if stop_at_closing and char == "}":
                    yield text[segment:i]
                    return
                raise ValidationError("Unbalanced Listview object.")
            if stack.pop() != char:
                raise ValidationError("Mismatched Listview delimiters.")
        elif char == "," and not stack:
            yield text[segment:i]
            segment = i + 1
        i += 1
    if quote or stack or stop_at_closing:
        raise ValidationError("Incomplete Listview object.")
    yield text[segment:]


def _listview_data(scripts, list_id, template):
    found = []
    for _, script in scripts:
        for match in re.finditer(r"\bnew\s+Listview\s*\(\s*\{", script):
            properties = {}
            for segment in _js_segments(script, match.end(), True):
                prop = re.match(r"""\s*(?:["']([^"']+)["']|([\w$]+))\s*:\s*(.*)\Z""",
                                segment, re.S)
                if prop:
                    properties[prop[1] or prop[2]] = prop[3].strip()
            if properties.get("id", "").strip("'\"") != list_id:
                continue
            if properties.get("template", "").strip("'\"") != template:
                raise ValidationError("Unexpected template for Listview %s." % list_id)
            try:
                rows = json.loads(properties["data"])
            except (KeyError, ValueError) as exc:
                raise ValidationError("Listview %s does not contain a JSON array." % list_id) from exc
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ValidationError("Invalid Listview rows.")
            found.append(rows)
    if len(found) > 1:
        raise ValidationError("Duplicate Listview %s." % list_id)
    return found[0] if found else None


def _positive_id(value, label):
    if type(value) is not int or value <= 0:
        raise ValidationError("Invalid %s: %r" % (label, value))
    return value


def parse_page(html, kind, entity_id):
    """Validate a page and extract only structured recipe/trainer records."""
    parser = _Scripts()
    parser.feed(html)
    metadata = [body for attrs, body in parser.scripts if attrs.get("id") == "data.pageMeta"]
    if len(metadata) != 1:
        raise ValidationError("Expected one Wowhead page metadata object.")
    try:
        meta = json.loads(metadata[0])
        env = meta["dataEnv"]
        patch = env["versions"]["16"]
        if (env["env"] != 16 or env["tree"] != 16 or not isinstance(patch, str)
                or not re.fullmatch(r"1\.60\.\d+", patch)):
            raise ValueError("wrong environment")
        identity = urllib.parse.unquote(meta["page"]).split("/", 1)[0]
        if identity != "%s=%s" % (kind, entity_id):
            raise ValueError("wrong page identity")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError("Page is not the requested Forever %s %s." % (kind, entity_id)) from exc
    result = {
        "patch": patch, "build": "", "server_time": meta.get("serverTime", ""),
        "active_db_changed": meta.get("activeDbChanged", {}).get("16"),
        "recipes": [], "npc_ids": [], "trainer_list_present": False,
        "taught_spell_ids": [], "teaches_list_present": False,
    }
    if kind == "skill":
        rows = _listview_data(parser.scripts, "recipes", "spell")
        if rows is None:
            # Gathering pages can legitimately have no recipe tab. An explicit
            # spells tab establishes that this is still a parsed skill page.
            if _listview_data(parser.scripts, "spells", "spell") is None:
                raise ValidationError("Skill page has neither recipes nor spells Listview.")
            rows = []
        seen = set()
        for row in rows:
            recipe_id = _positive_id(row.get("id"), "recipe spell ID")
            if recipe_id in seen:
                raise ValidationError("Duplicate recipe spell ID %s." % recipe_id)
            seen.add(recipe_id)
            skill_ids = row.get("skill")
            if not isinstance(skill_ids, list) or entity_id not in skill_ids:
                raise ValidationError("Recipe is not associated with the requested skill.")
            for skill_id in skill_ids:
                _positive_id(skill_id, "skill ID")
            specialization = row.get("specialization")
            if specialization is not None:
                if type(specialization) is not int or specialization < 0:
                    raise ValidationError("Invalid recipe specialization.")
            source = row.get("source")
            if source is not None:
                if not isinstance(source, list):
                    raise ValidationError("Invalid recipe source list.")
                for source_id in source:
                    _positive_id(source_id, "source category")
            if row.get("learnedat") is not None and (
                type(row["learnedat"]) is not int or row["learnedat"] < 0
            ):
                raise ValidationError("Invalid learnedat value.")
        result["recipes"] = rows
    elif kind == "spell":
        rows = _listview_data(parser.scripts, "taught-by-npc", "npc")
        result["trainer_list_present"] = rows is not None
        result["npc_ids"] = sorted({
            _positive_id(row.get("id"), "trainer NPC ID") for row in (rows or [])
        })
    elif kind == "item":
        rows = _listview_data(parser.scripts, "teaches", "spell")
        result["teaches_list_present"] = rows is not None
        result["taught_spell_ids"] = sorted({
            _positive_id(row.get("id"), "taught spell ID") for row in (rows or [])
        })
    else:
        raise ValidationError("Unsupported page kind.")
    return result


def _validate_url(url, robots=False):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "www.wowhead.com" or parsed.fragment:
        raise FetchError("Only the fixed Wowhead HTTPS origin is allowed.")
    path = urllib.parse.unquote(parsed.path)
    allowed = path == "/robots.txt" if robots else bool(
        re.fullmatch(r"/forever/(?:skill|spell|item)=\d+(?:/[a-z0-9-]+)?/?", path)
    )
    if not allowed or parsed.query:
        raise FetchError("Unexpected Wowhead request path.")


class _NoAutomaticRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        # _Client follows a bounded redirect itself so every HTTP request gets
        # the same clock, delay, origin checks, and robots policy.
        return None


def _transport(url, headers):
    """Exactly one HTTP request, without automatic redirects or proxies."""
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoAutomaticRedirect()
    )
    request = urllib.request.Request(url, headers=headers)
    try:
        response = opener.open(request, timeout=30)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise FetchError("Response exceeds the size limit.")
        return {
            "status": response.code,
            "headers": {key.lower(): value for key, value in response.headers.items()},
            "body": body,
            "url": response.geturl(),
        }


def _challenge(body):
    text = body.decode("utf-8", errors="replace").lower().replace("\u2019", "'")
    if re.search(r"""id\s*=\s*["']data\.pagemeta["']""", text):
        return False
    return any(marker in text for marker in (
        "verify you are human", "verify that you are human",
        "challenge-platform", "cf-chl-", "awswaf-captcha",
        "window.awswafintegration", "enable javascript and cookies to continue",
        "not a robot", "javascript is disabled", "gokuprops",
        "captcha", "access denied", "request blocked", "cdn error",
    ))


class _Client:
    def __init__(self, cache_dir, offline, refresh, max_age_days):
        self.cache_dir = require_repo_path(cache_dir)
        require_repo_path(POLICY_DIR)
        self.offline, self.refresh = offline, refresh
        self.max_age = max_age_days * 86400
        self.sources = []
        self.missing = []
        self.robots = None
        self.minimum_delay = 3.0

    def _cache_path(self, url):
        return require_repo_path(self.cache_dir / (sha256(url.encode("utf-8")).hexdigest() + ".json"))

    def _cooldown(self, reason, retry_after=None):
        seconds = 86400.0
        if retry_after:
            try:
                seconds = max(0.0, float(retry_after))
            except (ValueError, TypeError):
                try:
                    seconds = max(0.0, parsedate_to_datetime(retry_after).timestamp() - _now())
                except (ValueError, TypeError, OverflowError):
                    pass
        state = {"until": _now() + seconds, "reason": reason, "recorded_at": _iso(_now())}
        _atomic_json(POLICY_DIR / "cooldown.json", state)
        raise CooldownError("%s; requests paused until %s." % (reason, _iso(state["until"])))

    def _request(self, url, headers=None, robots=False):
        _validate_url(url, robots)
        original_entity = urllib.parse.unquote(urllib.parse.urlsplit(url).path).split("/")[2] if not robots else None
        headers = dict(headers or {})
        headers.update({"User-Agent": USER_AGENT, "Accept": "text/plain" if robots else "text/html"})
        attempt, redirects = 0, 0
        while True:
            cooldown = _read_json(POLICY_DIR / "cooldown.json")
            if cooldown and cooldown.get("until", 0) > _now():
                raise CooldownError("Wowhead cooldown: %s (until %s)." % (
                    cooldown.get("reason", "blocked"), _iso(cooldown["until"])))
            clock = _read_json(POLICY_DIR / "request-clock.json") or {}
            delay = self.minimum_delay * (2 ** attempt) + random.uniform(0, 2)
            remaining = clock.get("last_request_at", 0) + delay - _now()
            if remaining > 0:
                time.sleep(remaining)
            _atomic_json(POLICY_DIR / "request-clock.json", {"last_request_at": _now()})
            try:
                response = _transport(url, headers)
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as exc:
                if attempt < 2:
                    attempt += 1
                    continue
                raise FetchError("Wowhead request failed after two retries: %s" % url) from exc
            status, body = response["status"], response["body"]
            _validate_url(response.get("url", url), robots)
            if status in (403, 429) or (status == 202 and not body.strip()) or _challenge(body):
                self._cooldown("HTTP %s or robot verification at %s" % (status, url),
                               response["headers"].get("retry-after"))
            if status in (301, 302, 303, 307, 308):
                location = response["headers"].get("location")
                if not location or redirects >= 3:
                    raise FetchError("Missing redirect location or more than three redirects.")
                target = urllib.parse.urljoin(url, location)
                _validate_url(target, robots)
                if not robots:
                    entity = urllib.parse.unquote(urllib.parse.urlsplit(target).path).split("/")[2]
                    if entity != original_entity:
                        raise FetchError("Redirect changed the requested entity.")
                    self._check_robots(target)
                url = target
                redirects += 1
                continue
            if 500 <= status < 600:
                if attempt < 2:
                    attempt += 1
                    continue
                raise FetchError("Wowhead returned HTTP %s after two retries." % status)
            return response

    def _check_robots(self, url):
        if self.robots is None:
            cached = _read_json(POLICY_DIR / "robots.json")
            if not cached or _now() - cached.get("checked_at", 0) > 86400:
                response = self._request(ORIGIN + "/robots.txt", robots=True)
                if response["status"] == 404:
                    text = "User-agent: *\nDisallow:\n"
                elif response["status"] == 200:
                    try:
                        text = response["body"].decode("utf-8-sig")
                    except UnicodeDecodeError as exc:
                        raise FetchError("Invalid robots.txt encoding.") from exc
                    if "<html" in text.lower() or "user-agent:" not in text.lower():
                        raise FetchError("Response is not a valid robots.txt policy.")
                else:
                    raise FetchError("Cannot read robots.txt (HTTP %s)." % response["status"])
                cached = {"checked_at": _now(), "body": text}
                _atomic_json(POLICY_DIR / "robots.json", cached)
            self.robots = urllib.robotparser.RobotFileParser()
            self.robots.parse(cached["body"].splitlines())
            crawl_delay = self.robots.crawl_delay(USER_AGENT)
            rate = self.robots.request_rate(USER_AGENT)
            self.minimum_delay = max(3.0, float(crawl_delay or 0),
                                     rate.seconds / rate.requests if rate else 0)
        if not self.robots.can_fetch(USER_AGENT, url):
            raise FetchError("robots.txt disallows this URL for %s: %s" % (USER_AGENT, url))

    def page(self, url, kind, entity_id):
        _validate_url(url)
        cache_path = self._cache_path(url)
        cached = _read_json(cache_path)
        parsed = None
        if cached:
            try:
                if cached.get("version") != CACHE_VERSION or cached["url"] != url:
                    raise ValidationError("Wrong cache identity.")
                if sha256(cached["html"].encode("utf-8")).hexdigest() != cached["sha256"]:
                    raise ValidationError("Cache content hash mismatch.")
                _timestamp(cached["fetched_at"])
                _timestamp(cached["checked_at"])
                parsed = parse_page(cached["html"], kind, entity_id)
            except (KeyError, TypeError, ValueError, FetchError):
                cached = None
        cache_state = "offline" if self.offline else "fresh"
        if self.offline and not cached:
            self.missing.append(url)
            self.sources.append({"SourceURL": url, "Status": "missing_cache", "Kind": kind,
                                 "EntityID": entity_id, "SourceEnvironment": "forever"})
            return None, None
        if not self.offline and (
            not cached or self.refresh or _now() - _timestamp(cached["checked_at"]) > self.max_age
        ):
            self._check_robots(url)
            headers = {}
            if cached:
                for key, header in (("etag", "If-None-Match"), ("last_modified", "If-Modified-Since")):
                    if cached.get(key):
                        headers[header] = cached[key]
            response = self._request(url, headers)
            if response["status"] == 304 and cached:
                cached["checked_at"] = _iso(_now())
                cache_state = "revalidated"
            elif response["status"] == 200:
                try:
                    html = response["body"].decode("utf-8-sig")
                except UnicodeDecodeError as exc:
                    raise ValidationError("Invalid HTML encoding.") from exc
                parsed = parse_page(html, kind, entity_id)
                cached = {
                    "version": CACHE_VERSION, "url": url, "html": html,
                    "sha256": sha256(html.encode("utf-8")).hexdigest(),
                    "fetched_at": _iso(_now()), "checked_at": _iso(_now()),
                    "etag": response["headers"].get("etag", ""),
                    "last_modified": response["headers"].get("last-modified", ""),
                }
                cache_state = "fetched"
            else:
                raise FetchError("Unexpected HTTP %s for %s." % (response["status"], url))
            _atomic_json(cache_path, cached)
        source = {
            "SourceURL": url, "SourcePatch": parsed["patch"], "SourceBuild": "",
            "SourceEnvironment": "forever", "SourceFetchedAt": cached["fetched_at"],
            "SourceCheckedAt": cached["checked_at"], "SourceSHA256": cached["sha256"],
            "SourceServerTime": parsed["server_time"],
            "SourceActiveDBChanged": parsed["active_db_changed"],
            "Kind": kind, "EntityID": entity_id, "Status": cache_state,
            "RowCount": len(parsed[{
                "skill": "recipes", "spell": "npc_ids", "item": "taught_spell_ids",
            }[kind]]),
        }
        self.sources.append(source)
        return parsed, source


def _skill_pairs(skills):
    if skills is None:
        return list(DEFAULT_SKILLS.items())
    if isinstance(skills, dict):
        skills = list(skills.items())
    pairs = []
    for value in skills:
        if type(value) is int:
            if value not in DEFAULT_SKILLS:
                raise ValueError("Supply a slug for an unknown skill ID.")
            skill_id, slug = value, DEFAULT_SKILLS[value]
        elif isinstance(value, dict):
            skill_id, slug = value["id"], value["slug"]
        else:
            skill_id, slug = value
        _positive_id(skill_id, "skill ID")
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9-]+", slug):
            raise ValueError("Invalid skill URL slug.")
        if skill_id in [key for key, _ in pairs]:
            raise ValueError("Duplicate skill ID.")
        pairs.append((skill_id, slug))
    return pairs


def _collect(client, pairs):
    records, recipe_counts = [], {}
    supplemental = {}
    for skill_id, slug in pairs:
        url = ORIGIN + "/forever/skill%%3D%s/%s" % (skill_id, slug)
        page, source = client.page(url, "skill", skill_id)
        if page is None:
            continue
        recipe_counts[str(skill_id)] = len(page["recipes"])
        for recipe in page["recipes"]:
            ability = recipe.get("specialization") or 0
            trainer = 6 in (recipe.get("source") or [])
            if not trainer and not ability:
                continue
            npc_ids, trainer_source = [], None
            trainer_patch_mismatch = False
            reason = "trainer_specialization_missing" if trainer else "trainer_not_observed"
            if ability and not trainer and not recipe.get("source"):
                recipe_id = recipe["id"]
                if recipe_id not in supplemental:
                    name_slug = re.sub(r"[^a-z0-9]+", "-", str(
                        recipe.get("displayName") or recipe.get("name") or ""
                    ).lower()).strip("-")
                    spell_url = ORIGIN + "/forever/spell%%3D%s" % recipe_id
                    if name_slug:
                        spell_url += "/" + name_slug
                    supplemental[recipe_id] = client.page(spell_url, "spell", recipe_id)
                spell, trainer_source = supplemental[recipe_id]
                if spell is None:
                    reason = "trainer_page_cache_missing"
                else:
                    npc_ids = spell["npc_ids"]
                    trainer = bool(npc_ids)
                    trainer_patch_mismatch = trainer and spell["patch"] != page["patch"]
                    reason = "trainer_not_observed"
            if trainer and ability:
                reason = ("trainer_source_patch_mismatch" if trainer_patch_mismatch
                          else "explicit_specialization_and_trainer")
            record = {
                "RecipeSpellID": recipe["id"], "RequiredAbility": ability,
                "Status": "confirmed" if trainer and ability and not trainer_patch_mismatch else "pending",
                "Reason": reason, "SkillLineID": skill_id,
                "LearnedAt": recipe.get("learnedat", ""),
                "NPCIDs": npc_ids, "TrainerObserved": trainer,
                "SpecializationObserved": ability > 0,
                "Evidence": "Wowhead.recipes.specialization; " + (
                    "Wowhead.recipes.source=6" if 6 in (recipe.get("source") or [])
                    else "Wowhead.taught-by-npc" if trainer else "trainer_unconfirmed"
                ),
            }
            for key in ("SourceURL", "SourcePatch", "SourceBuild", "SourceEnvironment",
                        "SourceFetchedAt", "SourceSHA256"):
                record[key] = source[key]
            # The requirement originates in the skill page; any NPC observation
            # has separate provenance and must not replace that source.
            record["TrainerSourceURL"] = trainer_source["SourceURL"] if trainer_source else ""
            record["TrainerSourcePatch"] = trainer_source["SourcePatch"] if trainer_source else ""
            record["TrainerSourceBuild"] = trainer_source["SourceBuild"] if trainer_source else ""
            record["TrainerSourceSHA256"] = trainer_source["SourceSHA256"] if trainer_source else ""
            record["TrainerSourceFetchedAt"] = trainer_source["SourceFetchedAt"] if trainer_source else ""
            records.append(record)
    return {
        "records": sorted(records, key=lambda row: (row["RecipeSpellID"], row["SkillLineID"])),
        "sources": client.sources,
        "coverage": {
            "scope": "observed_only", "exact_build_known": False,
            "requested_skill_ids": [key for key, _ in pairs],
            "recipe_rows_by_skill": recipe_counts, "missing_pages": client.missing,
            "supplemental_spell_pages": len(supplemental),
            "confirmed_records": sum(row["Status"] == "confirmed" for row in records),
            "pending_records": sum(row["Status"] == "pending" for row in records),
            "complete": False,
        },
    }


def collect_trainers(cache_dir, offline=False, refresh=False, max_age_days=7, skills=None):
    """Return records, sources, coverage; online failure raises before returning.

    Missing/zero specialization never means unrestricted. Offline mode uses
    validated caches of any age and reports missing pages without network I/O.
    ``skills`` accepts known integer IDs, (ID, slug) pairs, an ID-to-slug mapping,
    or dictionaries with ``id`` and ``slug``. Twelve Classic professions are
    requested by default. Callers own all final CSV/Lua publication.
    """
    if max_age_days < 0:
        raise ValueError("max_age_days must be nonnegative.")
    client = _Client(cache_dir, offline, refresh, max_age_days)
    pairs = _skill_pairs(skills)
    if offline:
        return _collect(client, pairs)
    with _network_lock():
        return _collect(client, pairs)
