"""Fixture-only checks for repeatable wuxianwow catalog acquisition."""

from email.utils import formatdate
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.error


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "df-prof-pipeline-v1.0/_temp/fc_recipe_catalog_fetch.py"
SPEC = importlib.util.spec_from_file_location("fc_recipe_catalog_fetch", SCRIPT)
fetch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetch)
STAMP = 1792500000.0


def row(record_id=100, spell=200, skill=164, products=None):
    return {"id": record_id, "spell": spell, "skill": skill,
            "products": [[300, 1]] if products is None else products}


def data(rows=None):
    return json.dumps([row()] if rows is None else rows).encode("utf-8")


def response(body=b"", status=200, headers=None, url=None):
    result = {"body": body, "status": status, "headers": headers or {}}
    if url:
        result["url"] = url
    return result


class RecipeCatalogFetchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="df-catalog-fetch-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.cache = self.directory / "cache"
        self.policy = self.directory / "policy"
        self.clock = STAMP
        for patcher in (
            mock.patch.object(fetch, "POLICY_DIR", self.policy),
            mock.patch.object(fetch, "_now", side_effect=lambda: self.clock),
            mock.patch.object(fetch.time, "sleep", side_effect=self.sleep),
            mock.patch.object(fetch.random, "uniform", return_value=0),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        transport = mock.patch.object(fetch, "_transport",
                                       side_effect=AssertionError("Unexpected live request"))
        self.transport = transport.start()
        self.addCleanup(transport.stop)

    def sleep(self, seconds):
        self.clock += seconds

    def collect(self, **kwargs):
        return fetch.collect_catalog(self.cache, **kwargs)

    def cache_files(self):
        return [self.cache / name for name in ("recipes.json", "source.json")]

    def cached(self, rows=None, age=0):
        raw = data(rows)
        source = {
            "url": fetch.URL, "fetchedAt": fetch._iso(self.clock - age * 86400),
            "sha256": sha256(raw).hexdigest(), "sourceBuild": "",
            # Existing cached manifests use these uppercase HTTP header names.
            "headers": {"ETag": '"prior"', "Last-Modified": "Tue, 20 Oct 2026 10:00:00 GMT",
                        "Date": "Tue, 20 Oct 2026 12:00:00 GMT"},
        }
        fetch._publish(self.cache, raw, source)
        return {path: path.read_bytes() for path in self.cache_files()}

    def assert_unchanged(self, previous):
        for path, raw in previous.items():
            self.assertEqual(path.read_bytes(), raw)

    def robots(self, text="User-agent: *\nDisallow:\n"):
        fetch._atomic_write(self.policy / "robots.json", fetch._json_bytes({
            "checkedAt": self.clock, "body": text,
        }))

    def test_legacy_cache_hit_has_no_network_or_state_directory_writes(self):
        old = self.cached()
        result = self.collect()
        self.assertEqual(result["cacheState"], "fresh")
        self.assertEqual(result["rows"], [row()])
        self.assertEqual(result["path"], str((self.cache / "recipes.json").resolve()))
        self.assertEqual(result["source"]["sourceBuild"], "")
        self.assert_unchanged(old)
        self.assertFalse(self.policy.exists())
        self.transport.assert_not_called()

    def test_offline_reads_old_cache_and_reports_missing_or_corrupt_cache(self):
        with self.assertRaises(fetch.CatalogFetchError):
            self.collect(offline=True)
        old = self.cached(age=100)
        self.assertEqual(self.collect(offline=True)["cacheState"], "offline")
        (self.cache / "recipes.json").write_bytes(data([row(spell=201)]))
        with self.assertRaises(fetch.CatalogFetchError):
            self.collect(offline=True)
        self.transport.assert_not_called()
        self.assertEqual((self.cache / "source.json").read_bytes(),
                         old[self.cache / "source.json"])

    def test_schema_requires_positive_integer_ids_and_product_pairs(self):
        invalid = (
            b"{}", b"[]", b"not json", data([{}]), data([row(record_id=True)]),
            data([row(spell=0)]), data([row(skill=-1)]),
            data([row(products=[[300]])]), data([row(products=[[300, 0]])]),
            data([row(products={"300": 1})]), data([row(), row()]),
        )
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(fetch.CatalogValidationError):
                fetch.validate_catalog(raw)
        rows = [row(products=[]), row(record_id=101)]
        self.assertEqual(fetch.validate_catalog(data(rows)), rows)  # shared spell is valid

    def test_records_and_products_do_not_become_teaching_links(self):
        self.cached()
        result = self.collect(offline=True)
        self.assertEqual(set(result["rows"][0]), {"id", "spell", "skill", "products"})
        self.assertNotIn("RecipeItemID", result["rows"][0])
        self.assertNotIn("RecipeSpellID", result["rows"][0])

    def test_first_request_checks_actual_user_agent_robots_and_spaces_requests(self):
        self.transport.side_effect = [
            response(b"User-agent: *\nDisallow:\n"),
            response(data(), headers={"etag": '"new"', "date": "Wed, 21 Oct 2026 00:00:00 GMT"}),
        ]
        result = self.collect()
        calls = self.transport.call_args_list
        self.assertEqual([call.args[0] for call in calls], [fetch.ROBOTS_URL, fetch.URL])
        self.assertTrue(all(call.args[1]["User-Agent"] == fetch.USER_AGENT for call in calls))
        self.assertGreaterEqual(self.clock - STAMP, 3)
        self.assertEqual(result["cacheState"], "fetched")
        self.assertEqual(result["source"]["sourceBuild"], "")
        self.assertEqual(result["source"]["sha256"], sha256(data()).hexdigest())

    def test_304_uses_legacy_conditional_headers_and_preserves_fetch_date(self):
        self.cached(age=8)
        old_source = fetch._load_cache(self.cache)["source"]
        old_body = (self.cache / "recipes.json").read_bytes()
        self.robots()
        self.transport.side_effect = [response(status=304)]
        result = self.collect()
        self.assertEqual(result["cacheState"], "revalidated")
        self.assertEqual(result["source"]["fetchedAt"], old_source["fetchedAt"])
        self.assertGreater(result["source"]["checkedAt"], old_source["fetchedAt"])
        self.assertEqual(result["source"]["sourceBuild"], "")
        self.assertEqual((self.cache / "recipes.json").read_bytes(), old_body)
        headers = self.transport.call_args.args[1]
        self.assertEqual(headers["If-None-Match"], '"prior"')
        self.assertEqual(headers["If-Modified-Since"], old_source["headers"]["Last-Modified"])
        self.transport.reset_mock()
        self.assertEqual(self.collect()["cacheState"], "fresh")
        self.transport.assert_not_called()

    def test_refresh_revalidates_fresh_cache_and_updated_content_is_hashed(self):
        self.cached()
        self.robots()
        new = data([row(record_id=101, spell=201)])
        self.transport.side_effect = [response(new, headers={"etag": '"v2"'})]
        result = self.collect(refresh=True)
        self.assertEqual(result["cacheState"], "fetched")
        self.assertEqual(result["source"]["sha256"], sha256(new).hexdigest())
        self.assertEqual(self.collect(offline=True)["rows"][0]["spell"], 201)

    def test_invalid_json_and_unexpected_http_preserve_valid_old_pair(self):
        old = self.cached(age=8)
        self.robots()
        for failed in (response(b"{}"), response(data([row(spell=0)])), response(status=404)):
            self.transport.side_effect = [failed]
            with self.subTest(response=failed), self.assertRaises(fetch.CatalogFetchError):
                self.collect()
            self.assert_unchanged(old)

    def test_robots_disallow_does_not_fetch_catalog_or_change_identity(self):
        old = self.cached(age=8)
        self.transport.side_effect = [
            response(b"User-agent: DungeonsForeverDataPipeline\nDisallow: /data/\n"
                     b"User-agent: *\nDisallow:\n"),
        ]
        with self.assertRaisesRegex(fetch.CatalogFetchError, "robots.txt disallows"):
            self.collect()
        self.assertEqual(self.transport.call_count, 1)
        self.assert_unchanged(old)

    def test_absent_robots_is_recorded_and_catalog_can_be_requested(self):
        self.transport.side_effect = [response(status=404), response(data())]
        self.assertEqual(self.collect()["cacheState"], "fetched")
        self.assertEqual(self.transport.call_count, 2)

    def test_challenge_403_202_and_429_persist_cooldown_without_retry(self):
        old = self.cached(age=8)
        for failed in (
            response(status=403), response(status=202), response(status=429),
            response(b"<html>CAPTCHA: verify that you're not a robot</html>"),
            response(b"<script>window.gokuProps = {};</script>"),
            response(b'{"error":"captcha required"}'),
        ):
            (self.policy / "cooldown.json").unlink(missing_ok=True)
            self.robots()
            self.transport.reset_mock()
            self.transport.side_effect = [failed]
            with self.subTest(response=failed), self.assertRaises(fetch.CatalogCooldownError):
                self.collect()
            self.assertEqual(self.transport.call_count, 1)
            state = fetch._read_json(self.policy / "cooldown.json")
            self.assertEqual(state["until"], self.clock + 86400)
            self.assert_unchanged(old)
            with self.assertRaises(fetch.CatalogCooldownError):
                fetch.collect_catalog(self.directory / "different-cache")
            self.assertEqual(self.transport.call_count, 1)

    def test_retry_after_seconds_and_http_date_are_honored(self):
        for value, expected in (("600", 600), (formatdate(STAMP + 7200, usegmt=True), 7200)):
            (self.policy / "cooldown.json").unlink(missing_ok=True)
            (self.policy / "request-clock.json").unlink(missing_ok=True)
            self.clock = STAMP
            self.robots()
            self.transport.side_effect = [response(status=429, headers={"retry-after": value})]
            with self.assertRaises(fetch.CatalogCooldownError):
                self.collect()
            self.assertEqual(fetch._read_json(self.policy / "cooldown.json")["until"],
                             STAMP + expected)

    def test_timeout_and_5xx_retry_at_most_twice_with_backoff(self):
        self.robots()
        self.transport.side_effect = [
            urllib.error.URLError("timeout"), response(status=503), response(data()),
        ]
        self.assertEqual(self.collect()["cacheState"], "fetched")
        self.assertEqual(self.transport.call_count, 3)
        self.assertGreaterEqual(self.clock - STAMP, 18)
        old = {path: path.read_bytes() for path in self.cache_files()}
        self.transport.reset_mock()
        self.transport.side_effect = [response(status=500)] * 3
        with self.assertRaises(fetch.CatalogFetchError):
            self.collect(refresh=True)
        self.assertEqual(self.transport.call_count, 3)
        self.assert_unchanged(old)

    def test_cross_invocation_spacing_is_persisted(self):
        self.robots()
        self.transport.side_effect = [response(data()), response(status=304)]
        self.collect()
        after_first = self.clock
        self.collect(refresh=True)
        self.assertGreaterEqual(self.clock - after_first, 3)

    def test_concurrent_fetch_is_rejected_and_lock_released_after_exit(self):
        self.robots()
        with fetch._network_lock():
            with self.assertRaises(fetch.CatalogFetchError):
                self.collect()
        self.transport.side_effect = [response(data())]
        self.assertEqual(self.collect()["cacheState"], "fetched")

    def test_no_proxy_or_hidden_redirect_or_arbitrary_origin(self):
        handler = fetch._NoAutomaticRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 301, "Moved", {}, fetch.URL))
        self.robots()
        for target in ("https://example.com/data/recipes.json",
                       "https://wuxianwow.com/data/other.json"):
            self.transport.side_effect = [response(status=302, headers={"location": target})]
            with self.assertRaises(fetch.CatalogFetchError):
                self.collect()
            self.assertFalse((self.cache / "recipes.json").exists())

    def test_publication_failure_rolls_back_compatibility_pair(self):
        old = self.cached(age=8)
        self.robots()
        self.transport.side_effect = [response(data([row(spell=201)]))]
        actual_write = fetch._atomic_write

        def fail_source_once(path, raw):
            if Path(path) == self.cache / "source.json":
                raise OSError("simulated source publication failure")
            return actual_write(path, raw)

        with mock.patch.object(fetch, "_atomic_write", side_effect=fail_source_once):
            with self.assertRaisesRegex(fetch.CatalogFetchError, "old cache was restored"):
                self.collect()
        self.assert_unchanged(old)
        self.assertIsNotNone(fetch._load_cache(self.cache))

    def test_valid_json_description_with_captcha_word_is_not_a_challenge(self):
        raw = data([dict(row(), desc="This example contains the word captcha.")])
        self.assertFalse(fetch._is_challenge(raw))
        self.assertEqual(len(fetch.validate_catalog(raw)), 1)


if __name__ == "__main__":
    unittest.main()
