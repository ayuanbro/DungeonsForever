"""Native browser requests, confined to one owner thread and anonymous context.

Browser verification cookies never move into an unrelated HTTP fingerprint.
No interactive CAPTCHA is solved or clicked by this transport.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import base64
import re
import threading
import time
from urllib.parse import urlsplit

from .model import SourceError, classify_response


class BrowserClosed(SourceError):
    attempted = False
    error_code = "transportClosed"


def playwright_factory():
    from playwright.sync_api import sync_playwright
    return sync_playwright()


class BrowserTransport:
    def __init__(self, factory=None, timeout=60, request_mode="navigation", assets="all",
                 collect_metrics=False, diagnostics=False, recycle_every=100):
        if request_mode not in ("navigation", "fetch") or assets not in ("all", "light"):
            raise ValueError("invalid browser mode")
        if not isinstance(recycle_every, int) or recycle_every < 0:
            raise ValueError("browser page recycle interval must be nonnegative")
        self._factory = factory or playwright_factory
        self._timeout = timeout
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="wowhead-browser")
        self._lock = threading.Lock()
        self._closed = False
        self._playwright = self._browser = self._context = self._page = None
        self._responses = []
        self.request_mode, self.assets = request_mode, assets
        self.collect_metrics, self.diagnostics = collect_metrics, diagnostics
        self._ready_for_fetch = False
        self.metrics = {"requests": 0, "encodedBytes": 0, "cacheHits": 0,
                        "lightFetches": 0, "navigationFallbacks": 0, "browserRestarts": 0,
                        "pageRecycles": 0, "navigationCount": 0,
                        "navigationStatuses": {}, "fetchStatuses": {}}
        self.identity = None
        self.recycle_every = recycle_every
        self._cdp = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def get(self, url):
        with self._lock:
            if self._closed:
                raise BrowserClosed("browser transport is closed")
            future = self._executor.submit(self._get_owned, url)
        return future.result()

    def _start_owned(self):
        if self._page is not None:
            return
        try:
            self._playwright = self._factory().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            version = self._browser.version
            if not re.fullmatch(r"\d+(?:\.\d+){3}", version):
                raise SourceError("unrecognized actual Chromium version")
            # Keep UA, UAData and native TLS/HTTP behavior on the installed
            # browser version. Do not intercept requests through curl_cffi.
            agent = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     f"(KHTML, like Gecko) Chrome/{version} Safari/537.36")
            self._context = self._browser.new_context(locale="en-US", user_agent=agent)
            if self.assets == "light":
                # Experimental: routing disables the browser HTTP cache. This
                # must be compared on total bytes, not just fewer image loads.
                self._context.route("**/*", lambda route: route.abort() if
                                    route.request.resource_type in ("image", "font", "media") else route.continue_())
            self._page = self._context.new_page()
            self._page.on("response", self._on_response_owned)
            if self.collect_metrics:
                self._instrument_page_owned()
        except Exception:
            self._close_owned()
            raise

    def _metric(self, key, value):
        self.metrics[key] += value

    def _instrument_page_owned(self):
        self._cdp = self._context.new_cdp_session(self._page)
        self._cdp.send("Network.enable")
        self._cdp.on("Network.requestWillBeSent", lambda _: self._metric("requests", 1))
        self._cdp.on("Network.requestServedFromCache", lambda _: self._metric("cacheHits", 1))
        self._cdp.on("Network.loadingFinished", lambda event: self._metric("encodedBytes", event.get("encodedDataLength", 0)))

    def _recycle_page_owned(self):
        if self._page is not None:
            try:
                if self._cdp is not None:
                    self._cdp.detach()
            except Exception:
                pass
            self._cdp = None
            self._page.close()
        self._page = self._context.new_page()
        self._page.on("response", self._on_response_owned)
        if self.collect_metrics:
            self._instrument_page_owned()
        self._ready_for_fetch = False
        self._responses = []
        self.metrics["pageRecycles"] += 1

    def _identity_owned(self):
        value = self._page.evaluate("""() => ({userAgent:navigator.userAgent, platform:navigator.platform, webdriver:navigator.webdriver,
          languages:Array.from(navigator.languages), brands:navigator.userAgentData ? navigator.userAgentData.brands : null})""")
        version = self._browser.version
        value.update(browserVersion=version, uaVersionMatches=f"Chrome/{version}" in value["userAgent"],
                     platformMatchesLinux="Linux" in value["platform"])
        brands = value.get("brands")
        value["brandVersionMatches"] = (any(b["brand"] in ("Chromium", "Google Chrome") and
                                           b["version"] == version.split(".")[0] for b in brands) if brands else None)
        self.identity = value

    def _fetch_owned(self, url):
        parsed = urlsplit(url)
        origin = urlsplit(self._page.url)
        if (parsed.scheme, parsed.netloc) != ("https", "www.wowhead.com") or not parsed.path.startswith("/forever/"):
            raise SourceError("light fetch requires a Forever URL")
        if (origin.scheme, origin.netloc) != (parsed.scheme, parsed.netloc):
            return None
        self.metrics["lightFetches"] += 1
        value = self._page.evaluate("""async ({url, timeout}) => {
          const controller = new AbortController();
          const timer = setTimeout(() => controller.abort(), timeout);
          try {
            const r = await fetch(url, {credentials:'same-origin', signal:controller.signal});
            const bytes = new Uint8Array(await r.arrayBuffer()); let binary='';
            for(let i=0;i<bytes.length;i+=16384) binary+=String.fromCharCode(...bytes.subarray(i,i+16384));
            return {status:r.status, headers:Object.fromEntries(r.headers), url:r.url, body:btoa(binary)};
          } finally {clearTimeout(timer);}
        }""", {"url": url, "timeout": self._timeout * 1000})
        result = value["status"], base64.b64decode(value["body"], validate=True), value["headers"], value["url"]
        statuses = self.metrics["fetchStatuses"]
        statuses[str(result[0])] = statuses.get(str(result[0]), 0) + 1
        # JS validation must run in a real navigation. Ordinary refusals are
        # returned to the host scheduler, not retried through another identity.
        if result[0] == 202 or result[0] == 200 and classify_response(result[0], result[1]) == "sourceBlocked":
            return None
        return result

    def _on_response_owned(self, response):
        request = response.request
        if request.is_navigation_request() and request.frame == self._page.main_frame:
            self._responses.append(response)
            statuses = self.metrics["navigationStatuses"]
            statuses[str(response.status)] = statuses.get(str(response.status), 0) + 1

    def _get_owned(self, url):
        disconnected = self._browser is not None and callable(getattr(self._browser, "is_connected", None)) and not self._browser.is_connected()
        closed_page = self._page is not None and callable(getattr(self._page, "is_closed", None)) and self._page.is_closed()
        if disconnected or closed_page:
            self._close_owned()
            self.metrics["browserRestarts"] += 1
        self._start_owned()
        if self.request_mode == "fetch" and self._ready_for_fetch:
            try:
                result = self._fetch_owned(url)
                if result is not None:
                    return result
            except Exception:
                # One bounded navigation fallback, including expired context
                # and a failed fetch. The body still goes through entity checks.
                pass
            self.metrics["navigationFallbacks"] += 1
        self._responses = []
        deadline = time.monotonic() + self._timeout
        navigation_error = None
        self.metrics["navigationCount"] += 1
        try:
            # The main response is enough to start reading. Response.body()
            # below still waits for the complete document, without waiting for
            # advertisement scripts to reach a DOM lifecycle milestone.
            self._page.goto(url, wait_until="commit", timeout=min(45000, self._timeout * 1000))
        except Exception as error:
            # A challenge can replace the document during goto. Its final main
            # navigation response is still authoritative; page.content() is not.
            navigation_error = error
        last = None
        while time.monotonic() < deadline:
            if self._responses:
                response = self._responses[-1]
                if response.status not in (301, 302, 303, 307, 308):
                    try:
                        body = response.body()
                        headers = dict(response.all_headers())
                        # Both calls pump Playwright events. A newer main
                        # document may have arrived while reading this body.
                        if response is not self._responses[-1]:
                            continue
                        last = response.status, body, headers, response.url
                        blocked = classify_response(response.status, body) == "sourceBlocked"
                        interactive = any(marker in body[:50000].lower() for marker in
                                          (b"g-recaptcha", b"h-captcha", b"captcha-container"))
                        if interactive or response.status != 202 and not (response.status == 200 and blocked):
                            self._ready_for_fetch = not blocked and response.status == 200
                            if self.diagnostics and self._ready_for_fetch and not (self.identity or {}).get("brands"):
                                try:
                                    self._identity_owned()
                                except Exception:
                                    # Diagnostics never promote or discard source evidence.
                                    self.identity = {"diagnosticStatus": "unavailable"}
                            if (self.recycle_every and self.metrics["navigationCount"] % self.recycle_every == 0
                                    and self._context is not None):
                                self._recycle_page_owned()
                            return last
                    except Exception as error:
                        navigation_error = error
            self._page.wait_for_timeout(min(250, max(1, (deadline - time.monotonic()) * 1000)))
        if last is not None:
            return last
        raise SourceError("browser main navigation produced no readable response") from navigation_error

    def _close_owned(self):
        # All Playwright objects, including cleanup after partial startup, are
        # touched exclusively by this executor's owner thread.
        try:
            if self._context is not None:
                self._context.close()
        finally:
            try:
                if self._browser is not None:
                    self._browser.close()
            finally:
                try:
                    if self._playwright is not None:
                        self._playwright.stop()
                finally:
                    self._cdp = None
                    self._playwright = self._browser = self._context = self._page = None
                    self._responses = []
                    self._ready_for_fetch = False

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            future = self._executor.submit(self._close_owned)
        try:
            future.result()
        finally:
            self._executor.shutdown(wait=True)
