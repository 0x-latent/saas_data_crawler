"""Open a real Xingtu login page and verify screenshot/cancel behavior."""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

import requests
from sqlalchemy import delete

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from saas_crawler.storage.db import SessionLocal  # noqa: E402
from saas_crawler.storage.models import Account, AccountSecret, LoginSession  # noqa: E402


def main(base_url: str = "http://127.0.0.1:8080/api") -> int:
    account_id: int | None = None
    login_session_id: int | None = None
    try:
        response = requests.post(
            f"{base_url}/accounts",
            json={
                "platform": "xingtu",
                "display_name": "__login_capture_validation__",
                "login_type": "qr",
            },
            timeout=20,
        )
        response.raise_for_status()
        account_id = response.json()["id"]
        response = requests.post(f"{base_url}/accounts/{account_id}/login", json={"mode": "qr"}, timeout=20)
        response.raise_for_status()
        login_session_id = response.json()["id"]

        screenshot_ok = False
        status = "pending"
        for _ in range(45):
            session_response = requests.get(f"{base_url}/login-sessions/{login_session_id}", timeout=10)
            session_response.raise_for_status()
            status = session_response.json()["status"]
            screenshot_response = requests.get(f"{base_url}/login-sessions/{login_session_id}/screenshot", timeout=10)
            if screenshot_response.status_code == 200 and screenshot_response.headers.get("content-type", "").startswith("image/"):
                screenshot_ok = len(screenshot_response.content) > 1000
                break
            if status in {"failed", "expired", "success", "cancelled"}:
                break
            time.sleep(2)
        if not screenshot_ok:
            raise RuntimeError(f"login screenshot was not produced; status={status}")

        cancelled = requests.post(f"{base_url}/login-sessions/{login_session_id}/cancel", timeout=10)
        cancelled.raise_for_status()
        assert cancelled.json()["status"] == "cancelled"
        time.sleep(3)
        print("login_capture_verification=ok")
        return 0
    finally:
        if account_id is not None:
            with SessionLocal() as session:
                session.execute(delete(LoginSession).where(LoginSession.account_id == account_id))
                session.execute(delete(AccountSecret).where(AccountSecret.account_id == account_id))
                session.execute(delete(Account).where(Account.id == account_id))
                session.commit()
        if login_session_id is not None:
            shutil.rmtree(ROOT_DIR / "data" / "login_sessions" / str(login_session_id), ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080/api"))
