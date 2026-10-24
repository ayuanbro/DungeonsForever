"""Read the fixed wuxianwow recipe catalog with reproducible cached provenance.

Catalog ``id`` identifies a catalog record, ``spell`` identifies a recipe spell,
and ``products`` describes crafted output. None establishes which item teaches
that spell. The provider does not declare a complete client build.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
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
import uuid


URL = "https://wuxianwow.com/data/recipes.json"
ROBOTS_URL = "https://wuxianwow.com/robots.txt"
USER_AGENT = "DungeonsForeverDataPipeline/1.0"
POLICY_DIR = Path(__file__).resolve().parent / "_fc/cache/recipe-catalog/.network-state"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024


class CatalogFetchError(RuntimeError):
    """The caller must preserve its previous generated outputs on this failure."""


class CatalogValidationError(CatalogFetchError):
    pass


class CatalogCooldownError(CatalogFetchError):
    pass


def _now():
    return time.time()


def _iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp(value):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("timezone missing")
        return stamp.timestamp()
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise CatalogValidationError("Invalid cache provenance timestamp.") from exc


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _atomic_write(path, data):
    path = require_repo_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def _positive(value, label):
    if type(value) is not int or value <= 0:
        raise CatalogValidationError("%s must be a positive integer." % label)


def validate_catalog(raw):
    """Validate the documented catalog shape without inventing teaching links."""
    try:
        rows = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise CatalogValidationError("Catalog response is not UTF-8 JSON.") from exc
    if not isinstance(rows, list) or not rows:
        raise CatalogValidationError("Catalog must be a nonempty JSON list.")
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise CatalogValidationError("Catalog row %s is not an object." % index)
        for key in ("id", "spell", "skill"):
            _positive(row.get(key), "row %s %s" % (index, key))
        if row["id"] in seen:
            raise CatalogValidationError("Duplicate catalog record id %s." % row["id"])
        seen.add(row["id"])
        products = row.get("products")
        if not isinstance(products, list):
            raise CatalogValidationError("Catalog products must be a list.")
        for product in products:
            if not isinstance(product, list) or len(product) != 2:
                raise CatalogValidationError("Product must be [item ID, count].")
            _positive(product[0], "product item ID")
            _positive(product[1], "product count")
    # Duplicate spell IDs are allowed: existing catalog rows can share a spell.
    return rows


def _load_cache(cache_dir):
    """Invalid/mismatched pairs are not returned as usable cache."""
    path = Path(cache_dir) / "recipes.json"
    try:
        raw = path.read_bytes()
        source = json.loads((Path(cache_dir) / "source.json").read_text(encoding="utf-8-sig"))
        if not isinstance(source, dict) or source.get("url") != URL:
            raise CatalogValidationError("Wrong cached catalog URL.")
        if source.get("sha256") != sha256(raw).hexdigest():
            raise CatalogValidationError("Cached catalog hash does not match source.json.")
        if source.get("sourceBuild", "") != "":
            raise CatalogValidationError("Catalog provenance cannot assert an undeclared build.")
        _timestamp(source["fetchedAt"])
        _timestamp(source.get("checkedAt", source["fetchedAt"]))
        if not isinstance(source.get("headers", {}), dict):
            raise CatalogValidationError("Invalid cached HTTP headers.")
        rows = validate_catalog(raw)
    except (OSError, KeyError, TypeError, ValueError, CatalogValidationError):
        return None
    # Keep the existing manifest format; checkedAt was absent in older caches.
    source = dict(source, sourceBuild="")
    return {"path": str(path.resolve()), "source": source, "rows": rows}


def _publish(cache_dir, raw, source):
    """Validate first, then replace both compatibility files with rollback."""
    validate_catalog(raw)
    paths = (Path(cache_dir) / "recipes.json", Path(cache_dir) / "source.json")
    previous = [path.read_bytes() if path.exists() else None for path in paths]
    completed = []
    try:
        for path, data in zip(paths, (raw, _json_bytes(source))):
            _atomic_write(path, data)
            completed.append(path)
    except OSError as exc:
        recovery_errors = []
        for path, old in zip(paths, previous):
            if path not in completed:
                continue
            try:
                if old is None:
                    path.unlink(missing_ok=True)
                else:
                    _atomic_write(path, old)
            except OSError as recovery:
                recovery_errors.append(str(recovery))
        if recovery_errors:
            raise CatalogFetchError("Cache publication and rollback failed: " +
                                    "; ".join(recovery_errors)) from exc
        raise CatalogFetchError("Cache publication failed; old cache was restored.") from exc


@contextmanager
def _network_lock():
    require_repo_path(POLICY_DIR)
    for name in ('fetch.lock', 'cooldown.json', 'request-clock.json', 'robots.json'):
        require_repo_path(POLICY_DIR / name)
    POLICY_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = require_repo_path(POLICY_DIR / "fetch.lock")
    if lock_path.exists() and lock_path.stat().st_nlink > 1:
        raise CatalogFetchError('network lock must not be a hard link')
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
            raise CatalogFetchError("Another wuxianwow catalog fetch is running.") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _allowed_url(url):
    if url not in (URL, ROBOTS_URL):
        raise CatalogFetchError("Only the fixed catalog URL and its robots.txt may be requested.")


class _NoAutomaticRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


def _transport(url, headers):
    """Exactly one request; the client accounts for redirects and retries."""
    _allowed_url(url)
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoAutomaticRedirect()
    )
    try:
        response = opener.open(urllib.request.Request(url, headers=headers), timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise CatalogFetchError("Response exceeded the size limit.")
        return {
            "status": response.code, "url": response.geturl(), "body": raw,
            "headers": {key.lower(): value for key, value in response.headers.items()},
        }


def _is_challenge(raw):
    # Catalog arrays can contain these words in names/descriptions. An error
    # object, unlike an array, is never a valid catalog and can be a challenge.
    text = raw.decode("utf-8", errors="replace").lstrip("\ufeff \t\r\n")
    if text.startswith("["):
        return False
    text = text.lower().replace("\u2019", "'")
    return any(marker in text for marker in (
        "captcha", "not a robot", "verify you are human", "verify that you are human",
        "javascript is disabled", "gokuprops", "challenge-platform", "cf-chl-",
        "window.awswafintegration", "access denied", "request blocked",
        "enable javascript and cookies to continue",
    ))


def _retry_after(value):
    if value:
        try:
            return max(0.0, float(value))
        except (ValueError, TypeError):
            try:
                return max(0.0, parsedate_to_datetime(value).timestamp() - _now())
            except (ValueError, TypeError, OverflowError):
                pass
    return 86400.0


class _Client:
    def __init__(self):
        self.robot_policy = None
        self.minimum_delay = 3.0

    def _block(self, message, headers):
        until = _now() + _retry_after(headers.get("retry-after"))
        _atomic_write(POLICY_DIR / "cooldown.json", _json_bytes({
            "until": until, "recordedAt": _iso(_now()), "reason": message,
        }))
        raise CatalogCooldownError("%s; requests paused until %s." % (message, _iso(until)))

    def request(self, url, headers=None):
        _allowed_url(url)
        request_headers = dict(headers or {})
        request_headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/plain" if url == ROBOTS_URL else "application/json",
        })
        attempt, redirects = 0, 0
        while True:
            cooldown = _read_json(POLICY_DIR / "cooldown.json") or {}
            if cooldown.get("until", 0) > _now():
                raise CatalogCooldownError("wuxianwow cooldown until %s: %s" % (
                    _iso(cooldown["until"]), cooldown.get("reason", "blocked")))
            clock = _read_json(POLICY_DIR / "request-clock.json") or {}
            delay = self.minimum_delay * (2 ** attempt) + random.uniform(0, 2)
            remaining = clock.get("lastRequestAt", 0) + delay - _now()
            if remaining > 0:
                time.sleep(remaining)
            _atomic_write(POLICY_DIR / "request-clock.json",
                          _json_bytes({"lastRequestAt": _now()}))
            try:
                result = _transport(url, request_headers)
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as exc:
                if attempt < 2:
                    attempt += 1
                    continue
                raise CatalogFetchError("Catalog request failed after two retries.") from exc
            _allowed_url(result.get("url", url))
            code, body = result["status"], result["body"]
            if code in (403, 429) or (code == 202 and not body.strip()) or _is_challenge(body):
                self._block("HTTP %s or verification page at %s" % (code, url),
                            result["headers"])
            if code in (301, 302, 303, 307, 308):
                location = result["headers"].get("location")
                target = urllib.parse.urljoin(url, location or "")
                if not location or target != url or redirects >= 3:
                    raise CatalogFetchError("Unexpected or repeated catalog redirect.")
                if url == URL:
                    self.check_robots()
                redirects += 1
                continue
            if 500 <= code < 600:
                if attempt < 2:
                    attempt += 1
                    continue
                raise CatalogFetchError("HTTP %s after two catalog retries." % code)
            return result

    def check_robots(self):
        if self.robot_policy is None:
            cached = _read_json(POLICY_DIR / "robots.json")
            if not cached or _now() - cached.get("checkedAt", 0) >= 86400:
                result = self.request(ROBOTS_URL)
                if result["status"] == 404:
                    policy = "User-agent: *\nDisallow:\n"
                elif result["status"] == 200:
                    try:
                        policy = result["body"].decode("utf-8-sig")
                    except UnicodeDecodeError as exc:
                        raise CatalogFetchError("Invalid robots.txt encoding.") from exc
                    if "<html" in policy.lower() or "user-agent:" not in policy.lower():
                        raise CatalogFetchError("Response is not a robots.txt policy.")
                else:
                    raise CatalogFetchError("Cannot read robots.txt: HTTP %s." % result["status"])
                cached = {"checkedAt": _now(), "body": policy}
                _atomic_write(POLICY_DIR / "robots.json", _json_bytes(cached))
            self.robot_policy = urllib.robotparser.RobotFileParser()
            self.robot_policy.parse(cached["body"].splitlines())
            rate = self.robot_policy.request_rate(USER_AGENT)
            if rate and rate.requests <= 0:
                raise CatalogFetchError("Invalid robots request-rate policy.")
            self.minimum_delay = max(
                3.0, float(self.robot_policy.crawl_delay(USER_AGENT) or 0),
                rate.seconds / rate.requests if rate else 0,
            )
        if not self.robot_policy.can_fetch(USER_AGENT, URL):
            raise CatalogFetchError("robots.txt disallows the catalog for %s." % USER_AGENT)


def _fresh(cached, max_age_days):
    source = cached["source"]
    return _now() - _timestamp(source.get("checkedAt", source["fetchedAt"])) < max_age_days * 86400


def _result(cached, state):
    return dict(cached, cacheState=state)


def collect_catalog(cache_dir, offline=False, refresh=False, max_age_days=7):
    """Return path/source/rows/cacheState; never silently use stale data on error.

    The existing recipes.json + source.json format is accepted. Offline reads
    validate its hash and rows, then allow any age. Online reads prefer seven-day
    validated cache; stale/refresh requests use ETag and Last-Modified if present.
    Failures raise CatalogFetchError and preserve previous valid cache contents.
    """
    if max_age_days < 0:
        raise ValueError("max_age_days must be nonnegative.")
    cache_dir = require_repo_path(cache_dir)
    require_repo_path(POLICY_DIR)
    for name in ('recipes.json', 'source.json'):
        require_repo_path(cache_dir / name)
    cached = _load_cache(cache_dir)
    if offline:
        if cached is None:
            raise CatalogFetchError("Offline catalog cache is missing or invalid.")
        return _result(cached, "offline")
    if cached and not refresh and _fresh(cached, max_age_days):
        return _result(cached, "fresh")
    with _network_lock():
        # A prior process might have replaced the cache before this lock.
        cached = _load_cache(cache_dir)
        if cached and not refresh and _fresh(cached, max_age_days):
            return _result(cached, "fresh")
        client = _Client()
        client.check_robots()
        headers = {}
        if cached:
            old_headers = {key.lower(): value for key, value in cached["source"].get("headers", {}).items()}
            for old, conditional in (("etag", "If-None-Match"),
                                     ("last-modified", "If-Modified-Since")):
                if old_headers.get(old):
                    headers[conditional] = old_headers[old]
        response = client.request(URL, headers)
        if response["status"] == 304 and cached:
            source = dict(cached["source"], checkedAt=_iso(_now()), sourceBuild="")
            # A check date is not a new content-fetch date or a client build.
            _atomic_write(Path(cache_dir) / "source.json", _json_bytes(source))
            cached["source"] = source
            return _result(cached, "revalidated")
        if response["status"] != 200:
            raise CatalogFetchError("Unexpected catalog HTTP %s." % response["status"])
        raw = response["body"]
        rows = validate_catalog(raw)
        source = {
            "url": URL, "fetchedAt": _iso(_now()), "checkedAt": _iso(_now()),
            "sha256": sha256(raw).hexdigest(), "sourceBuild": "",
            "headers": response["headers"],
        }
        _publish(cache_dir, raw, source)
        return {
            "path": str((Path(cache_dir) / "recipes.json").resolve()),
            "source": source, "rows": rows, "cacheState": "fetched",
        }
