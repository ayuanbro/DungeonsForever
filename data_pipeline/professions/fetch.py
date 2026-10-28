"""Bounded online acquisition. Raw snapshots, never addon exports, are inputs."""
from __future__ import annotations

import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit, parse_qs
import zipfile

from .model import (LATEST_URL, PRODUCT, TABLES, USER_AGENT, SourceError, checked_bytes, classify_response,
                    discover, load_tables, parse_csv, parse_page, sha256, write_json)


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


def retry_delay(headers, attempt):
    try:
        return min(30.0, max(0.0, float(headers.get("Retry-After", 2**attempt))))
    except (TypeError, ValueError):
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


class WowheadTransport:
    """One anonymous session generation shared by two bounded HTTP workers.

    No cookies or verification response bodies enter the manifest. A browser is
    started only on a JavaScript challenge; unsupported challenges stay blocked.
    """
    agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"

    def __init__(self, interval=1.0):
        self.local = threading.local()
        self.lock = threading.Lock()
        self.cookies = []
        self.generation = 0
        self.bootstrap_attempts = 0
        self.pace_lock = threading.Lock()
        self.next_request = 0.0
        self.interval = interval
        self.blocked_episodes = 0
        self.circuit_open = False

    def pace(self):
        with self.pace_lock:
            delay = max(0.0, self.next_request - time.monotonic())
            self.next_request = max(time.monotonic(), self.next_request) + self.interval
        if delay:
            time.sleep(delay)

    def session(self):
        from curl_cffi import requests
        if not hasattr(self.local, "session"):
            self.local.session = requests.Session(impersonate="chrome")
            self.local.generation = -1
        if self.local.generation != self.generation:
            for cookie in self.cookies:
                self.local.session.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"], path=cookie["path"])
            self.local.generation = self.generation
        return self.local.session

    def bootstrap(self, url, previous_generation):
        with self.lock:
            if self.generation != previous_generation:
                return True
            self.bootstrap_attempts += 1
            from playwright.sync_api import sync_playwright
            from curl_cffi import requests
            # Do not seed the challenge browser with the very token rejected by
            # the origin. Presence of an old token is not successful renewal.
            session = requests.Session(impersonate="chrome")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(locale="en-US", user_agent=self.agent)
                page = context.new_page()
                document = {"status": None}

                def route_request(route):
                    request = route.request
                    host = urlsplit(request.url).hostname or ""
                    permitted = any(host == domain or host.endswith("." + domain)
                                    for domain in ("wowhead.com", "awswaf.com", "zamimg.com"))
                    if not permitted or request.resource_type in ("image", "font", "media"):
                        route.abort()
                        return
                    try:
                        headers = dict(request.all_headers())
                        headers.pop("content-length", None)
                        headers.pop("accept-encoding", None)
                        response = session.request(request.method, request.url, headers=headers,
                            data=request.post_data_buffer, timeout=20, allow_redirects=False)
                        if request.is_navigation_request() and request.frame == page.main_frame:
                            document["status"] = response.status_code
                        outgoing = dict(response.headers)
                        for name in ("content-encoding", "content-length", "transfer-encoding"):
                            outgoing.pop(name, None)
                        route.fulfill(status=response.status_code, headers=outgoing, body=response.content)
                    except Exception:
                        route.abort()

                try:
                    page.route("**/*", route_request)
                    page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    deadline = time.monotonic() + 25
                    while time.monotonic() < deadline:
                        page.wait_for_timeout(500)
                        cookies = context.cookies()
                        if document["status"] in (200, 404) and any(cookie["name"] == "aws-waf-token" for cookie in cookies):
                            self.cookies = cookies
                            self.generation += 1
                            self.blocked_episodes = 0
                            return True
                    return False
                finally:
                    browser.close()

    def get(self, url, retries=3):
        if self.circuit_open:
            raise SourceError("hostCircuitOpen: repeated challenge renewal failed; retry failed sources in a later run")
        for attempt in range(retries):
            try:
                self.pace()
                generation = self.generation
                response = self.session().get(url, headers={"User-Agent": self.agent,
                    "Accept-Language": "en-US,en;q=0.9"}, timeout=35)
                status = classify_response(response.status_code, response.content)
                if status == "sourceBlocked" and response.status_code != 429:
                    if attempt + 1 < retries and self.bootstrap(url, generation):
                        continue
                if response.status_code in (429, 500, 502, 503, 504) and attempt + 1 < retries:
                    time.sleep(retry_delay(response.headers, attempt))
                    continue
                if status == "sourceBlocked":
                    with self.lock:
                        self.blocked_episodes += 1
                        if self.blocked_episodes >= 2:
                            self.circuit_open = True
                else:
                    self.blocked_episodes = 0
                return response.status_code, response.content, dict(response.headers), response.url
            except Exception:
                if attempt + 1 == retries:
                    with self.lock:
                        self.blocked_episodes += 1
                        if self.blocked_episodes >= 2:
                            self.circuit_open = True
                    raise
                time.sleep(2**attempt)
        raise SourceError("request attempts exhausted")


def response_record(root, key, url, getter, table=None, entity=None):
    record = {"key": key, "url": url, "fetchedAt": now()}
    try:
        status, data, headers, final = getter(url)
        # Only non-secret response metadata is retained.
        lower = {name.lower(): value for name, value in headers.items()}
        record.update(httpStatus=status, finalUrl=final, contentType=lower.get("content-type", ""),
                      contentDisposition=lower.get("content-disposition", ""),
                      status=classify_response(status, data), bytes=len(data), sha256=sha256(data))
        suffix = ".csv" if table else ".html"
        path = Path("responses") / (key.replace(":", "-") + suffix)
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
            except (ValueError, UnicodeError) as error:
                record["status"] = "parseError"
                record["error"] = str(error)
        return record
    except Exception as error:
        record.update(status="sourceBlocked", error=type(error).__name__ + ": " + str(error)[:250])
        return record


def snapshot_archive(root, output):
    """Portable byte-for-byte raw inputs, without machine paths or session cookies."""
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.is_relative_to(root):
        raise SourceError("archive output must be outside the raw snapshot")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    paths = {"manifest.json": root / "manifest.json"}
    # A resumed request can replace an old HTTP failure with a circuit-open
    # record that has no response body. Preserve old files on disk for local
    # investigation, but never ship unreferenced and unaudited bytes in a replay
    # package. Validate every referenced response before replacing any archive.
    for record in manifest["responses"]:
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


def referenced_entities(parsed):
    result = set()
    for name, rows in parsed["listviews"].items():
        kind = "item" if name == "taught-by-item" else "quest" if name in ("reward-from-q", "reward-from-quests") else (
            "npc" if name in ("taught-by-npc", "sold-by", "dropped-by") else None)
        if kind:
            result.update((kind, int(row["id"])) for row in rows if isinstance(row, dict)
                          and isinstance(row.get("id"), int) and row["id"] > 0)
    return result


def fetch(out: Path, web_limit=None, workers=2, retries=3, resume=False, retry_failed=False, web_interval=1.0, log=print):
    if not 1 <= workers <= 2 or not 1 <= retries <= 3:
        raise SourceError("workers must be 1..2 and retries 1..3")
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    for restart in range(3):
        build = latest()
        work = out.parent / (out.name + ".partial")
        if out.exists():
            if resume and retry_failed and not work.exists():
                out.rename(work)
            else:
                raise SourceError("output already exists; choose fresh output or --resume --retry-failed")
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
                for record in manifest["responses"]:
                    if "path" in record:
                        checked_bytes(work, record)
                manifest["fetchComplete"] = False
                manifest["resumedAt"] = now()
        else:
            manifest = None
        if manifest is None:
            work.mkdir()
            manifest = {"schema": 1, "product": PRODUCT, "build": build["version"], "buildInfo": build,
                        "startedAt": now(), "fetchComplete": False, "responses": [], "webLimited": web_limit is not None}
        write_json(work / "manifest.json", manifest)
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
                write_json(work / "manifest.json", manifest)
                raise SourceError("required DB2 failed: " + name + ": " + record["status"])
            previous[key] = record
            manifest["responses"] = list(previous.values())
            write_json(work / "manifest.json", manifest)
            log(f"db2 {name} rows={record['rows']}", flush=True)
        tables = load_tables(work, manifest)
        members, teaching = discover(tables)
        targets = {("spell", spell) for _, spell in members}
        targets.update(("item", item) for items in teaching.values() for item in items)
        transport = WowheadTransport(interval=max(0.0, web_interval))
        seen = set()
        count = 0
        for depth in range(4):
            batch = sorted(targets - seen, key=lambda x: ({"spell": 0, "item": 1, "quest": 2, "npc": 3}[x[0]], x[1]))
            if not batch:
                break
            seen.update(batch)
            pending = []
            for kind, entity_id in batch:
                key = f"web:{kind}:{entity_id}"
                retryable = retry_failed and key in previous and previous[key]["status"] in ("sourceBlocked", "sourceError", "parseError")
                if key in previous and previous[key]["status"] != "notFetched" and not retryable:
                    record = previous[key]
                    if record["status"] == "verified":
                        parsed = parse_page((work / record["path"]).read_bytes(), kind, entity_id, record["finalUrl"])
                        targets.update(referenced_entities(parsed))
                    continue
                if web_limit is not None and count + len(pending) >= web_limit:
                    previous[key] = {"key": key, "status": "notFetched", "reason": "explicitWebLimit",
                                     "url": f"https://www.wowhead.com/forever/{kind}={entity_id}"}
                else:
                    pending.append((kind, entity_id))

            def acquire(entity):
                kind, entity_id = entity
                url = f"https://www.wowhead.com/forever/{kind}={entity_id}"
                return response_record(work, f"web:{kind}:{entity_id}", url,
                                       lambda u: transport.get(u, retries), entity=entity)

            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                for record in pool.map(acquire, pending):
                    previous[record["key"]] = record
                    count += 1
                    if record["status"] == "verified":
                        _, kind, entity_id = record["key"].split(":")
                        parsed = parse_page((work / record["path"]).read_bytes(), kind, int(entity_id), record["finalUrl"])
                        targets.update(referenced_entities(parsed))
                    if count % 25 == 0:
                        manifest["responses"] = sorted(previous.values(), key=lambda r: r["key"])
                        write_json(work / "manifest.json", manifest)
                        log(f"web {count} / discovered {len(targets)} last={record['key']} {record['status']}", flush=True)
        manifest["responses"] = sorted(previous.values(), key=lambda r: r["key"])
        after = latest()
        manifest["latestAfter"] = after
        if (after["version"], after["build_config"]) != (build["version"], build["build_config"]):
            write_json(work / "manifest.json", manifest)
            old = work.with_name(work.name + ".changed-" + build["version"])
            if old.exists():
                raise SourceError("build changed repeatedly; retained snapshot already exists")
            work.rename(old)
            log("latest changed; restarting batch", flush=True)
            resume = False
            continue
        for kind, entity_id in sorted(targets - seen):
            key = f"web:{kind}:{entity_id}"
            previous.setdefault(key, {"key": key, "status": "notFetched", "reason": "referenceDepthLimit",
                                     "url": f"https://www.wowhead.com/forever/{kind}={entity_id}"})
        manifest["responses"] = sorted(previous.values(), key=lambda r: r["key"])
        manifest.update(fetchComplete=True, sourceCoverageComplete=all(r["status"] == "verified" for r in previous.values()),
            finishedAt=now(), discovery={"members": len(members),
            "teachingPairs": sum(len(items) for items in teaching.values()), "webEntities": len(targets)})
        write_json(work / "manifest.json", manifest)
        work.rename(out)
        snapshot_archive(out, out.with_suffix(".zip"))
        log(f"complete {out} web={count}", flush=True)
        return out
    raise SourceError("latest changed in three consecutive batches")
