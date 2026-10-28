"""Bounded online acquisition. Raw snapshots, never addon exports, are inputs."""
from __future__ import annotations

import concurrent.futures
import datetime
from email.utils import parsedate_to_datetime
import html
import json
import math
import os
from pathlib import Path
import re
import tempfile
import threading
import time
import urllib.error
import urllib.request
import unicodedata
from urllib.parse import urlsplit, parse_qs
import zipfile

from .model import (LATEST_URL, PRODUCT, TABLES, USER_AGENT, SourceError, checked_bytes, classify_response,
                    discover, integer, load_tables, parse_csv, parse_page, sha256, write_json)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def latest():
    request = urllib.request.Request(LATEST_URL, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("product") != PRODUCT or not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", result.get("version", "")):
        raise SourceError("invalid latest product response")
    if not re.fullmatch(r"[0-9a-f]{32}", result.get("build_config", "")):
        raise SourceError("latest response lacks build identity")
    return result


def retry_delay(headers, attempt, wall_time=None):
    """Honor both HTTP forms, case-insensitively, without shortening server waits."""
    value = next((str(v).strip() for k, v in headers.items() if k.lower() == "retry-after"), "")
    if value.isdigit():
        return int(value)
    try:
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            date = date.replace(tzinfo=datetime.timezone.utc)
        return max(0.0, date.timestamp() - (time.time() if wall_time is None else wall_time))
    except (TypeError, ValueError, OverflowError):
        return min(30.0, 2**attempt)


def ordinary_get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.status, response.read(), dict(response.headers), response.url
        except urllib.error.HTTPError as error:
            data = error.read()
            if error.code in (429, 500, 502, 503, 504) and attempt + 1 < retries:
                time.sleep(retry_delay(error.headers, attempt))
                continue
            return error.code, data, dict(error.headers), error.url
        except (OSError, TimeoutError):
            if attempt + 1 == retries:
                raise
            time.sleep(2**attempt)
    raise SourceError("request attempts exhausted")


class HostCircuitOpen(SourceError):
    attempted = False
    error_code = "hostCircuitOpen"


class TransportClosed(SourceError):
    attempted = False
    error_code = "transportClosed"


class WowheadTransport:
    """Two direct HTTP workers, with one persistent native-browser owner.

    Direct curl requests keep the impersonation profile's matching headers.
    JavaScript challenges switch to a browser session whose cookies stay there.
    """

    def __init__(self, interval=1.0, browser_factory=None, mode="auto", recoveries=0,
                 cooldown=120.0, browser_assets="all"):
        if mode not in ("auto", "browser", "browser-fetch"):
            raise SourceError("invalid web transport")
        if not isinstance(recoveries, int) or not 0 <= recoveries <= 3 or not math.isfinite(cooldown) or cooldown < 0 or not math.isfinite(interval) or interval < 0:
            raise SourceError("invalid recovery limits")
        self.mode = mode
        self.local = threading.local()
        self.lock = threading.Lock()
        self.pace_lock = threading.Lock()
        self.next_request = 0.0
        self.interval = interval
        self.blocked_episodes = 0
        self.circuit_open = False
        self.closed = False
        self._sessions = []
        self._browser_factory = browser_factory
        self._browser = None
        self.request_lock = threading.Lock()
        self.recovery_limit, self.cooldown = recoveries, cooldown
        self.browser_assets = browser_assets
        self.cooldown_until = 0.0
        self.metrics = {"requests": 0, "recoveries": 0, "waitSeconds": 0.0, "httpStatuses": {}}

    def _wait(self, seconds):
        self.metrics["waitSeconds"] += seconds
        time.sleep(seconds)

    def _recover(self):
        if not self.circuit_open:
            return
        if self.metrics["recoveries"] >= self.recovery_limit:
            raise HostCircuitOpen("bounded host recovery exhausted; no request was sent")
        self._wait(max(self.cooldown, self.cooldown_until - time.monotonic()))
        self.metrics["recoveries"] += 1
        self.circuit_open = False
        # One probe may proceed. Failure immediately reopens the circuit.
        self.blocked_episodes = 1

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def pace(self):
        with self.pace_lock:
            delay = max(0.0, self.next_request - time.monotonic())
            self.next_request = max(time.monotonic(), self.next_request) + self.interval
        if delay:
            self._wait(delay)

    def session(self):
        from curl_cffi import requests
        if not hasattr(self.local, "session"):
            with self.lock:
                if self.closed:
                    raise TransportClosed("HTTP transport is closed")
                # Each object belongs to one HTTP worker. Avoid an internal
                # thread-local curl handle so owner-independent close releases
                # the same native handle, after the worker pool has drained.
                session = requests.Session(impersonate="chrome", use_thread_local_curl=False)
                self._sessions.append(session)
                self.local.session = session
        return self.local.session

    @staticmethod
    def javascript_challenge(status, data):
        return status == 202 or status == 200 and any(marker in data[:12000].lower() for marker in
            (b"window.gokuprops", b"cf-chl-", b"just a moment"))

    def browser(self):
        with self.lock:
            if self.closed:
                raise TransportClosed("HTTP transport is closed")
            if self._browser is None:
                from .browser_transport import BrowserTransport
                self._browser = (self._browser_factory() if self._browser_factory else
                                 BrowserTransport(request_mode="fetch" if self.mode == "browser-fetch" else "navigation",
                                                  assets=self.browser_assets, diagnostics=True))
            return self._browser

    def get(self, url, retries=3):
        # One host-wide scheduler: another worker cannot bypass Retry-After or
        # a half-open probe. Parsing/writing the preceding response can overlap.
        with self.request_lock:
            return self._get_serial(url, retries)

    def _get_serial(self, url, retries):
        self.local.last_transport = None
        if self.closed:
            raise TransportClosed("HTTP transport is closed")
        self._recover()
        with self.lock:
            if self.closed:
                raise TransportClosed("HTTP transport is closed")
            if self.circuit_open:
                raise HostCircuitOpen("host circuit open after repeated failures; no request was sent")
        for attempt in range(retries):
            try:
                self.pace()
                if attempt == 0:
                    with self.lock:
                        if self.circuit_open:
                            raise HostCircuitOpen("host circuit opened while queued; no request was sent")
                browser = self._browser
                if browser is None and self.mode in ("browser", "browser-fetch"):
                    browser = self.browser()
                if browser is None:
                    # Do not replace the profile's UA/client-hints with a
                    # different Chrome version or copy browser cookies here.
                    session = self.session()
                    self.local.last_transport = "http"
                    response = session.get(url, timeout=35)
                    result = response.status_code, response.content, dict(response.headers), response.url
                    if self.javascript_challenge(result[0], result[1]):
                        browser = self.browser()
                if browser is not None:
                    self.local.last_transport = "browser"
                    result = browser.get(url)
                code, data, headers, final = result
                self.metrics["requests"] += 1
                counts = self.metrics["httpStatuses"]
                counts[str(code)] = counts.get(str(code), 0) + 1
                status = classify_response(code, data)
                interactive = status == "sourceBlocked" and any(marker in data[:50000].lower() for marker in
                    (b"g-recaptcha", b"h-captcha", b"captcha-container"))
                if interactive:
                    self.circuit_open = True
                    self.recovery_limit = self.metrics["recoveries"]
                    self.metrics["stopReason"] = "interactiveChallenge"
                    return result
                if status == "sourceBlocked" and any(k.lower() == "retry-after" for k in headers):
                    deadline = time.monotonic() + retry_delay(headers, attempt)
                    self.cooldown_until = max(self.cooldown_until, deadline)
                    self.next_request = max(self.next_request, deadline)
                if code in (429, 500, 502, 503, 504) and attempt + 1 < retries:
                    self._wait(retry_delay(headers, attempt))
                    continue
                if code in (429, 500, 502, 503, 504):
                    delay = retry_delay(headers, attempt)
                    self.cooldown_until = max(self.cooldown_until, time.monotonic() + delay)
                    # Also applies to the next entity after the last retry.
                    self.next_request = max(self.next_request, self.cooldown_until)
                with self.lock:
                    if status == "sourceBlocked" or code >= 500:
                        self.blocked_episodes += 1
                        if self.blocked_episodes >= 2:
                            self.circuit_open = True
                    else:
                        self.blocked_episodes = 0
                return code, data, headers, final
            except (HostCircuitOpen, TransportClosed):
                raise
            except Exception:
                if attempt + 1 == retries:
                    with self.lock:
                        self.blocked_episodes += 1
                        if self.blocked_episodes >= 2:
                            self.circuit_open = True
                    raise
                self._wait(2**attempt)
        raise SourceError("request attempts exhausted")

    @property
    def last_transport(self):
        return getattr(self.local, "last_transport", None)

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            browser, sessions = self._browser, self._sessions
            self._sessions = []
        errors = []
        try:
            if browser is not None:
                browser.close()
        except Exception as error:
            errors.append(error)
        for session in sessions:
            try:
                session.close()
            except Exception as error:
                errors.append(error)
        if errors:
            raise errors[0]


def response_record(root, key, url, getter, table=None, entity=None, parsed_sink=None):
    record = {"key": key, "url": url, "fetchedAt": now(), "attempted": True}
    try:
        status, data, headers, final = getter(url)
        # Only non-secret response metadata is retained.
        lower = {name.lower(): value for name, value in headers.items()}
        record.update(httpStatus=status, finalUrl=final, contentType=lower.get("content-type", ""),
                      contentDisposition=lower.get("content-disposition", ""),
                      status=classify_response(status, data), bytes=len(data), sha256=sha256(data))
        suffix = ".csv" if table else ".html"
        # Immutable response names keep a crash before checkpointing from
        # replacing bytes still referenced by the previous manifest.
        identity = "" if table else "." + record["sha256"]
        path = Path("responses") / (key.replace(":", "-") + identity + suffix)
        record["path"] = path.as_posix()
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_bytes(data)
        if record["status"] == "verified":
            try:
                if table:
                    if "text/csv" not in record["contentType"]:
                        raise SourceError("non-CSV table response")
                    build = parse_qs(urlsplit(url).query).get("build", [""])[0]
                    if f"{table}.{build}.csv" not in lower.get("content-disposition", ""):
                        raise SourceError("table response identity missing")
                    rows = parse_csv(data, table)
                    record["rows"] = len(rows)
                else:
                    parsed = parse_page(data, *entity, final)
                    record["entity"] = {"kind": entity[0], "id": entity[1], "title": parsed["title"]}
                    if parsed_sink is not None:
                        parsed_sink.update(parsed)
            except (ValueError, UnicodeError) as error:
                record["status"] = "parseError"
                record["error"] = str(error)
        return record
    except Exception as error:
        attempted = getattr(error, "attempted", True)
        record.update(status="sourceError" if attempted else "notFetched", attempted=attempted,
                      errorCode=getattr(error, "error_code", type(error).__name__),
                      error=type(error).__name__ + ": " + str(error)[:250])
        return record


def retain_response_evidence(previous, record, refresh=False):
    """An unsent retry does not erase the last real HTTP observation."""
    if previous and record.get("attempted") is False and not refresh:
        retained = dict(previous)
        retained["lastAttempt"] = {key: value for key, value in record.items() if key not in ("key", "url")}
        return retained
    if previous:
        record = dict(record)
        history = list(previous.get("attemptHistory", []))
        history.append({key: value for key, value in previous.items() if key != "attemptHistory"})
        record["attemptHistory"] = history
    return record


def response_evidence(records):
    """Current and prior real responses are all portable audited inputs."""
    for record in records:
        yield record
        yield from response_evidence(record.get("attemptHistory", []))


def checkpoint(path, manifest):
    """An interrupted write leaves the preceding complete manifest intact."""
    handle, temporary = tempfile.mkstemp(prefix="manifest.", suffix=".part", dir=path.parent)
    os.close(handle)
    stage = Path(temporary)
    try:
        write_json(stage, manifest)
        os.replace(stage, path)
    finally:
        stage.unlink(missing_ok=True)


def update_web_run(manifest, targets, records):
    run = manifest["webRun"]
    keys = sorted(f"web:{kind}:{entity}" for kind, entity in targets)
    counts, skips = {}, {}
    attempted = 0
    for key in keys:
        record = records.get(key, {})
        if record.get("webRunID") != run["id"]:
            record = record.get("lastAttempt", {})
        if record.get("webRunID") == run["id"] and record.get("attempted") is True:
            attempted += 1
            status = record["status"]
            counts[status] = counts.get(status, 0) + 1
        else:
            reason = record.get("errorCode", "pending") if record.get("webRunID") == run["id"] else "pending"
            skips[reason] = skips.get(reason, 0) + 1
    run.update(targets=keys, targetCount=len(keys), attempted=attempted, notAttempted=len(keys) - attempted,
               statuses=counts, skippedReasons=skips, requestCoverageComplete=attempted == len(keys), updatedAt=now())
    manifest["requestCoverageComplete"] = run["requestCoverageComplete"]


def snapshot_archive(root, output):
    """Portable byte-for-byte raw inputs, without machine paths or session cookies."""
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.is_relative_to(root):
        raise SourceError("archive output must be outside the raw snapshot")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    paths = {"manifest.json": root / "manifest.json"}
    # Never ship unreferenced bytes. Prior responses retained as attemptHistory
    # remain explicitly referenced evidence and receive the same validation.
    for record in response_evidence(manifest["responses"]):
        if "path" not in record:
            continue
        relative = record["path"]
        path = (root / relative).resolve()
        if "\\" in relative or ":" in relative or relative.startswith("/") or ".." in Path(relative).parts:
            raise SourceError("nonportable or escaping snapshot response path")
        if relative == "manifest.json" or not path.is_relative_to(root):
            raise SourceError("snapshot response path escapes package")
        checked_bytes(root, record)
        paths[path.relative_to(root).as_posix()] = path
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=output.name + ".", suffix=".part", dir=output.parent)
    os.close(handle)
    stage = Path(temporary)
    try:
        with zipfile.ZipFile(stage, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, path in sorted(paths.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
        os.replace(stage, output)
    finally:
        stage.unlink(missing_ok=True)


def route_slug(name):
    """A routing hint, never an entity identifier or a source fact."""
    if not isinstance(name, str):
        return ""
    name = html.unescape(name).strip()
    if "<" in name or ">" in name:
        return ""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"[^a-z0-9]+", "-", ascii_name.replace("'", "")).strip("-")
    return value if 0 < len(value) <= 200 else ""


def entity_url(kind, entity, names=None):
    if kind not in ("spell", "item", "npc", "quest") or not isinstance(entity, int) or isinstance(entity, bool) or entity <= 0:
        raise SourceError("invalid web entity identity")
    base = f"https://www.wowhead.com/forever/{kind}={entity}"
    slug = route_slug((names or {}).get((kind, entity)))
    return base + "/" + slug if slug else base


def fresh_route_names(tables):
    names = {}
    for kind, table, column in (("spell", "SpellName", "Name_lang"), ("item", "ItemSparse", "Display_lang")):
        for row in tables[table]:
            value = row.get(column)
            if route_slug(value):
                names[kind, integer(row["ID"])] = value
    return names


def referenced_entities(parsed, names=None):
    result = set()
    for name, rows in parsed["listviews"].items():
        kind = "item" if name == "taught-by-item" else "quest" if name in ("reward-from-q", "reward-from-quests") else (
            "npc" if name in ("taught-by-npc", "sold-by", "dropped-by") else None)
        if kind:
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("id"), int) or isinstance(row["id"], bool) or row["id"] <= 0:
                    continue
                key = kind, row["id"]
                result.add(key)
                value = row.get("name") or row.get("displayName")
                if names is not None and route_slug(value):
                    # Exact-version DB2 names already present retain priority.
                    names.setdefault(key, value)
    return result


def prepare_current_http_retry(source, build, status, pending_finalize=False):
    """Validate the complete source before mutating a targeted working copy."""
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    run = manifest.get("webRun", {})
    if (manifest.get("product") != PRODUCT or manifest.get("build") != build["version"]
            or manifest.get("buildInfo", {}).get("build_config") != build["build_config"]):
        raise SourceError("targeted retry latest build/config changed; original snapshot was not modified")
    if not isinstance(run.get("id"), str) or not run["id"] or run.get("mode") not in ("refresh", "retry", "acquire"):
        raise SourceError("targeted retry requires an existing full web run")
    active = run.get("currentHttpRetry")
    if active and (not active.get("complete") or not manifest.get("fetchComplete") or pending_finalize):
        if active.get("httpStatus") != status or active.get("webRunID") != run["id"] or not active.get("baselineFullCoverage"):
            raise SourceError("an unfinished targeted retry must be resumed with the same HTTP selection")
        plan = active
    else:
        if (not manifest.get("fetchComplete") or manifest.get("requestCoverageComplete") is not True
                or run.get("requestCoverageComplete") is not True):
            raise SourceError("targeted retry requires a closed full run with complete request coverage")
        selected = sorted(record["key"] for record in manifest["responses"]
                          if record.get("webRunID") == run["id"] and record.get("attempted") is True
                          and record.get("httpStatus") == status and record.get("status") == "sourceBlocked"
                          and re.fullmatch(r"web:(spell|item|quest|npc):[1-9]\d*", record["key"]))
        if not set(selected).issubset(run.get("targets", [])):
            raise SourceError("targeted records are absent from the full run target coverage")
        plan = {"id": now(), "webRunID": run["id"], "httpStatus": status, "selectedKeys": selected,
                "completedKeys": [], "additionalKeys": [], "baselineFullCoverage": True, "complete": False}
    load_tables(source, manifest)
    for record in response_evidence(manifest["responses"]):
        if "path" in record:
            checked_bytes(source, record)
    return plan


def fetch(out: Path, web_limit=None, workers=2, retries=3, resume=False, retry_failed=False, refresh_web=False, web_interval=1.0, log=print, web_transport="auto", retry_current_http=None,
          host_recoveries=2, host_cooldown=120.0, browser_assets="all"):
    if not 1 <= workers <= 2 or not 1 <= retries <= 3:
        raise SourceError("workers must be 1..2 and retries 1..3")
    if web_transport not in ("auto", "browser", "browser-fetch"):
        raise SourceError("web transport must be auto or browser")
    if not isinstance(host_recoveries, int) or not 0 <= host_recoveries <= 3 or not math.isfinite(host_cooldown) or host_cooldown < 0 or not math.isfinite(web_interval) or web_interval < 0 or browser_assets not in ("all", "light"):
        raise SourceError("invalid host recovery or browser assets option")
    if retry_current_http is not None:
        if retry_current_http not in (403, 429, 202) or not isinstance(retry_current_http, int):
            raise SourceError("targeted HTTP code must be403,429 or202")
        if not resume or refresh_web or retry_failed:
            raise SourceError("targeted retry requires --resume and cannot combine with refresh/retry-failed")
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    for restart in range(3):
        build = latest()
        continuing_web_run = False
        work = out.parent / (out.name + ".partial")
        # Distinguish a pre-existing pending publication from a completed out
        # directory moved here by this invocation's explicit new refresh.
        was_partial = work.exists()
        current_retry = None
        if retry_current_http is not None:
            source = out if out.exists() else work
            if not source.exists() or out.exists() and work.exists():
                raise SourceError("targeted retry requires one existing full snapshot or its retry partial")
            current_retry = prepare_current_http_retry(source, build, retry_current_http, pending_finalize=was_partial)
            if not current_retry["selectedKeys"]:
                log(f"no current sourceBlocked HTTP{retry_current_http} records; snapshot unchanged", flush=True)
                return out
        if out.exists():
            if resume and (retry_failed or refresh_web or current_retry is not None) and not work.exists():
                out.rename(work)
            else:
                raise SourceError("output already exists; choose fresh output or --resume with --retry-failed/--refresh-web")
        if work.exists():
            if not resume:
                raise SourceError(f"partial snapshot exists: {work}; use --resume")
            manifest = json.loads((work / "manifest.json").read_text(encoding="utf-8"))
            if manifest["build"] != build["version"] or manifest["buildInfo"]["build_config"] != build["build_config"]:
                # Retain old partial evidence, never silently reuse another build.
                old = work.with_name(work.name + ".old-" + manifest["build"])
                if old.exists():
                    raise SourceError("old partial snapshot already retained")
                work.rename(old)
                manifest = None
            else:
                # Every previously accepted byte is revalidated by build/check.
                for record in response_evidence(manifest["responses"]):
                    if "path" in record:
                        checked_bytes(work, record)
                # A closed snapshot can still have thousands of requests left
                # after a circuit break. Resume that same round, just as for
                # an interrupted .partial directory; completed entities stay done.
                continuing_web_run = (was_partial or current_retry is not None or not manifest.get("fetchComplete", False)
                    or manifest.get("webRun", {}).get("requestCoverageComplete") is False)
                manifest["fetchComplete"] = False
                manifest["resumedAt"] = now()
        else:
            manifest = None
        if manifest is None:
            work.mkdir()
            manifest = {"schema": 1, "product": PRODUCT, "build": build["version"], "buildInfo": build,
                        "startedAt": now(), "fetchComplete": False, "responses": [], "webLimited": web_limit is not None}
        mode = manifest["webRun"]["mode"] if current_retry is not None else "refresh" if refresh_web else "retry" if retry_failed else "acquire"
        if not continuing_web_run or manifest.get("webRun", {}).get("mode") != mode:
            manifest["webRun"] = {"id": now(), "mode": mode, "startedAt": now(), "webLimit": web_limit}
        manifest["webRun"].pop("closedAt", None)
        if current_retry is not None:
            manifest["webRun"]["currentHttpRetry"] = current_retry
        retry_selected = set(current_retry["selectedKeys"]) if current_retry else set()
        retry_completed = set(current_retry["completedKeys"]) if current_retry else set()
        retry_additional = set(current_retry["additionalKeys"]) if current_retry else set()
        segment = {"startedAt": now(), "transport": web_transport, "workers": workers,
                   "interval": max(0.0, web_interval), "retries": retries, "webLimit": web_limit,
                   "urlRouting": "fresh-name-slug-v1", "attempted": 0}
        segment.update(hostRecoveries=host_recoveries, hostCooldown=host_cooldown, browserAssets=browser_assets,
                       scheduler="bounded-v2", maxPending=workers)
        manifest["webRun"].setdefault("segments", []).append(segment)
        if current_retry is not None:
            segment.update(operation="retry-current-http", httpStatus=retry_current_http,
                           retryOperationID=current_retry["id"], selectedKeys=sorted(retry_selected - retry_completed),
                           attemptedKeys=[])
        manifest.pop("finishedAt", None)
        manifest["sourceCoverageComplete"] = False
        manifest["requestCoverageComplete"] = False
        manifest["webLimited"] = web_limit is not None
        run_id = manifest["webRun"]["id"]
        checkpoint(work / "manifest.json", manifest)
        log(f"resolve {PRODUCT} {build['version']}", flush=True)
        previous = {record["key"]: record for record in manifest["responses"]}
        for name in TABLES:
            key = "db2:" + name
            if key in previous and previous[key]["status"] == "verified":
                continue
            url = f"https://wago.tools/db2/{name}/csv?build={build['version']}&locale=enUS"
            record = response_record(work, key, url, lambda u: ordinary_get(u, retries), table=name)
            if record["status"] != "verified" or build["version"] not in record.get("url", ""):
                manifest["responses"] = list(previous.values()) + [record]
                checkpoint(work / "manifest.json", manifest)
                raise SourceError("required DB2 failed: " + name + ": " + record["status"])
            previous[key] = record
            manifest["responses"] = list(previous.values())
            checkpoint(work / "manifest.json", manifest)
            log(f"db2 {name} rows={record['rows']}", flush=True)
        tables = load_tables(work, manifest)
        names = fresh_route_names(tables)
        members, teaching = discover(tables)
        targets = {("spell", spell) for _, spell in members}
        targets.update(("item", item) for items in teaching.values() for item in items)
        # Same-build raw evidence identifies historical pages to request again;
        # it never supplies facts from an old generated catalogue.
        historical = [record["key"] for record in previous.values()
                      if refresh_web or retry_failed and record["status"] != "verified"]
        historical.extend(manifest["webRun"].get("targets", []))
        for key in historical:
            match = re.fullmatch(r"web:(spell|item|quest|npc):([1-9]\d*)", key)
            if match:
                targets.add((match[1], int(match[2])))
        seen, count = set(), 0
        if current_retry is not None:
            for entity in targets:
                key = f"web:{entity[0]}:{entity[1]}"
                old = previous.get(key, {})
                done = old.get("webRunID") == run_id and old.get("attempted") is True
                if not (key in retry_selected - retry_completed or key in retry_additional and not done):
                    seen.add(entity)
        attempted_count, reported_skips = 0, set()
        segment_attempted_keys = set()
        update_web_run(manifest, targets, previous)
        segment["attemptedAtStart"] = manifest["webRun"]["attempted"]
        checkpoint(work / "manifest.json", manifest)
        log(f"web mode={mode} transport={web_transport} workers={workers} interval={max(0.0, web_interval)} attempted={manifest['webRun']['attempted']} / targets={len(targets)}", flush=True)
        transport = None
        try:
            with WowheadTransport(interval=max(0.0, web_interval), mode=web_transport,
                                  recoveries=host_recoveries, cooldown=host_cooldown,
                                  browser_assets=browser_assets) as transport:
                # Traverse only explicit supported source relationships, once
                # per entity. A fixed depth must not silently omit prerequisites.
                while True:
                    batch = sorted(targets - seen, key=lambda x: ({"spell": 0, "item": 1, "quest": 2, "npc": 3}[x[0]], x[1]))
                    if not batch:
                        break
                    seen.update(batch)
                    pending = []
                    for kind, entity_id in batch:
                        key = f"web:{kind}:{entity_id}"
                        old = previous.get(key)
                        done = old and old.get("webRunID") == run_id and old.get("attempted") is True
                        targeted_pending = current_retry is not None and (
                            key in retry_selected - retry_completed or key in retry_additional and not done)
                        retryable = retry_failed and old and old["status"] in (
                            "sourceBlocked", "sourceError", "parseError", "sourceMissing")
                        if old and not targeted_pending and (done or old["status"] != "notFetched" and not refresh_web and not retryable):
                            if old["status"] == "verified":
                                parsed = parse_page((work / old["path"]).read_bytes(), kind, entity_id, old["finalUrl"])
                                targets.update(referenced_entities(parsed, names if old.get("webRunID") == run_id else None))
                            continue
                        if web_limit is not None and count + len(pending) >= web_limit:
                            deferred = {"key": key, "status": "notFetched", "reason": "explicitWebLimit", "attempted": False,
                                        "webRunID": run_id, "errorCode": "explicitWebLimit", "url": entity_url(kind, entity_id, names)}
                            if current_retry is not None:
                                deferred["retryOperationID"] = current_retry["id"]
                            previous[key] = retain_response_evidence(old, deferred,
                                refresh=refresh_web or current_retry is not None and key not in retry_selected)
                        else:
                            pending.append((kind, entity_id))

                    def acquire(entity):
                        kind, entity_id = entity
                        url = entity_url(kind, entity_id, names)
                        parsed = {}
                        record = response_record(work, f"web:{kind}:{entity_id}", url,
                                                 lambda u: transport.get(u, retries), entity=entity, parsed_sink=parsed)
                        observed = getattr(transport, "last_transport", None)
                        if record.get("attempted") is True and isinstance(observed, str) and observed in ("http", "browser"):
                            record["transport"] = observed
                        record["webRunID"] = run_id
                        if current_retry is not None:
                            record["retryOperationID"] = current_retry["id"]
                        return record, parsed

                    pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
                    entities = iter(pending)
                    futures = set()
                    processed = set()

                    def completed():
                        def fill():
                            while len(futures) < workers:
                                entity = next(entities, None)
                                if entity is None:
                                    break
                                futures.add(pool.submit(acquire, entity))
                        fill()
                        while futures:
                            for future in concurrent.futures.as_completed(tuple(futures)):
                                yield future
                                futures.remove(future)
                                processed.discard(future)
                                fill()

                    def accept(future):
                        nonlocal count, attempted_count
                        record, parsed = future.result()
                        processed.add(future)
                        previous[record["key"]] = retain_response_evidence(previous.get(record["key"]), record,
                            refresh=refresh_web or current_retry is not None and record["key"] not in retry_selected)
                        count += 1
                        if record.get("attempted") is True:
                            attempted_count += 1
                            segment["attempted"] = attempted_count
                            segment_attempted_keys.add(record["key"])
                            if current_retry is not None:
                                segment["attemptedKeys"] = sorted(segment_attempted_keys)
                                if record["key"] in retry_selected:
                                    retry_completed.add(record["key"])
                                    current_retry["completedKeys"] = sorted(retry_completed)
                        if record["status"] == "verified":
                            references = referenced_entities(parsed, names)
                            if current_retry is not None:
                                retry_additional.update(f"web:{kind}:{entity}" for kind, entity in references if (kind, entity) not in targets)
                                current_retry["additionalKeys"] = sorted(retry_additional)
                            targets.update(references)
                        return record

                    try:
                        for future in completed():
                            record = accept(future)
                            skipped_reason = record.get("errorCode") if record.get("attempted") is False else None
                            new_skip = skipped_reason is not None and skipped_reason not in reported_skips
                            if new_skip:
                                reported_skips.add(skipped_reason)
                            progress = record.get("attempted") is True and attempted_count % 25 == 0
                            failure = record.get("attempted") is True and record["status"] in ("sourceBlocked", "sourceError")
                            if progress or failure or new_skip:
                                manifest["responses"] = sorted(previous.values(), key=lambda r: r["key"])
                                update_web_run(manifest, targets, previous)
                                checkpoint(work / "manifest.json", manifest)
                                run = manifest["webRun"]
                                state = f" state={skipped_reason}" if new_skip else ""
                                log(f"web attempted={run['attempted']} / targets={run['targetCount']} last={record['key']} {record['status']}{state}", flush=True)
                    finally:
                        # Cancellation must not wait for thousands of queued
                        # requests. Only at most two already running jobs drain.
                        pool.shutdown(wait=True, cancel_futures=True)
                        for future in futures:
                            if future.done() and not future.cancelled() and future not in processed:
                                try:
                                    accept(future)
                                except BaseException:
                                    # Preserve the original interruption. Any
                                    # record already received is checkpointed;
                                    # unfinished entries stay pending on resume.
                                    pass
        finally:
            manifest["responses"] = sorted(previous.values(), key=lambda r: r["key"])
            update_web_run(manifest, targets, previous)
            segment.update(finishedAt=now(), attempted=attempted_count, attemptedAtEnd=manifest["webRun"]["attempted"])
            if isinstance(getattr(transport, "metrics", None), dict):
                segment["transportMetrics"] = dict(transport.metrics)
                browser = getattr(transport, "_browser", None)
                if isinstance(getattr(browser, "identity", None), dict):
                    segment["browserIdentity"] = dict(browser.identity)
            if current_retry is not None:
                current_retry["complete"] = retry_selected.issubset(retry_completed) and all(
                    previous.get(key, {}).get("webRunID") == run_id and previous[key].get("attempted") is True
                    for key in retry_additional)
                current_retry["updatedAt"] = now()
                segment["notAttemptedKeys"] = sorted(set(segment["selectedKeys"]) - segment_attempted_keys)
            checkpoint(work / "manifest.json", manifest)
        after = latest()
        manifest["latestAfter"] = after
        if (after["version"], after["build_config"]) != (build["version"], build["build_config"]):
            checkpoint(work / "manifest.json", manifest)
            if current_retry is not None:
                raise SourceError("latest changed during targeted retry; retained partial evidence and original archive")
            old = work.with_name(work.name + ".changed-" + build["version"])
            if old.exists():
                raise SourceError("build changed repeatedly; retained snapshot already exists")
            work.rename(old)
            log("latest changed; restarting batch", flush=True)
            resume = False
            continue
        manifest["responses"] = sorted(previous.values(), key=lambda r: r["key"])
        manifest["webRun"].update(closedAt=now(), referenceDepthLimited=False)
        manifest["requestCoverageComplete"] = manifest["webRun"]["requestCoverageComplete"]
        manifest.update(fetchComplete=True, sourceCoverageComplete=all(r["status"] == "verified" for r in previous.values()),
            finishedAt=now(), discovery={"members": len(members),
            "teachingPairs": sum(len(items) for items in teaching.values()), "webEntities": len(targets)})
        checkpoint(work / "manifest.json", manifest)
        work.rename(out)
        snapshot_archive(out, out.with_suffix(".zip"))
        log(f"closed {out} web={count} requestCoverageComplete={manifest['requestCoverageComplete']} sourceCoverageComplete={manifest['sourceCoverageComplete']}", flush=True)
        return out
    raise SourceError("latest changed in three consecutive batches")
