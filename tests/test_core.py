from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from saas_crawler.accounts import secrets
from saas_crawler.accounts.login_runner import _is_logged_in, _waiting_status
from saas_crawler.ingestion.discover_assets import infer_asset_type, infer_platform
from saas_crawler.ingestion.utils import as_float, as_int, file_sha256
from saas_crawler.storage import settings


class CoreHelpersTest(unittest.TestCase):
    def test_secret_round_trip_does_not_leave_plaintext(self) -> None:
        original = settings.CRAWLER_SECRET_KEY
        settings.CRAWLER_SECRET_KEY = "unit-test-secret"
        try:
            encrypted = secrets.encrypt_secret("sensitive-value")
            self.assertNotIn("sensitive-value", encrypted)
            self.assertEqual(secrets.decrypt_secret(encrypted), "sensitive-value")
        finally:
            settings.CRAWLER_SECRET_KEY = original

    def test_asset_inference(self) -> None:
        self.assertEqual(infer_platform(Path("data/xingtu/result.json")), "xingtu")
        self.assertEqual(infer_platform(Path("data/magnetic_juxing.sqlite")), "magnetic_juxing")
        self.assertEqual(infer_asset_type(Path("data/magnetic_juxing.sqlite")), "sqlite_database")
        self.assertEqual(infer_asset_type(Path("checkpoints/feigua.json")), "checkpoint_json")

    def test_numeric_conversions(self) -> None:
        self.assertEqual(as_int("1.2w"), 12000)
        self.assertEqual(as_int("1,234"), 1234)
        self.assertEqual(as_float("1,234.5"), 1234.5)
        self.assertIsNone(as_int("unknown"))

    def test_hash_limit_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.bin"
            path.write_bytes(b"abcdef")
            self.assertEqual(file_sha256(path, max_bytes=3), file_sha256(path, max_bytes=3))
            self.assertNotEqual(file_sha256(path, max_bytes=3), file_sha256(path))

    def test_xingtu_login_cookie_detection(self) -> None:
        self.assertTrue(_is_logged_in("xingtu", [{"name": "sessionid"}], "https://www.xingtu.cn/ad/creator/market"))
        self.assertFalse(_is_logged_in("xingtu", [{"name": "tt_webid"}], "https://www.xingtu.cn/ad/creator/market"))
        self.assertEqual(_waiting_status("sms"), "awaiting_code")


if __name__ == "__main__":
    unittest.main()
