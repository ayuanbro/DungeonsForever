"""Native browser requests, confined to one owner thread and anonymous context.

Browser verification cookies never move into an unrelated HTTP fingerprint.
No interactive CAPTCHA is solved or clicked by this transport.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import re
import threading
import time

from .model import SourceError, classify_response


class BrowserClosed(SourceError):
    attempted = False
    error_code = "transportClosed"


def playwright_factory():
    from playwright.sync_api import sync_playwright
    return sync_playwright()


class BrowserTransport:
    def __init__(self, factory=None, timeout=60):
        self._factory = factory or playwright_factory
        self._timeout = timeout
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="wowhead-browser")
        self._lock = threading.Lock()
        self._closed = False
        self._playwright = self._browser = self._context = self._page = None
        self._responses = []

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
            self._page = self._context.new_page()
            self._page.on("response", self._on_response_owned)
        except Exception:
            self._close_owned()
            raise

    def _on_response_owned(self, response):
        request = response.request
        if request.is_navigation_request() and request.frame == self._page.main_frame:
            self._responses.append(response)

    def _get_owned(self, url):
        self._start_owned()
        self._responses = []
        deadline = time.monotonic() + self._timeout
        navigation_error = None
        try:
            self._page.goto(url, wait_until="domcontentloaded", timeout=min(45000, self._timeout * 1000))
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
                    self._playwright = self._browser = self._context = self._page = None
                    self._responses = []

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
