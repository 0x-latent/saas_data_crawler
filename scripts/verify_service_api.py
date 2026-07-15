"""Run a small API/Redis/database smoke test against a running backend."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import requests
from redis import Redis
from rq.job import Job
from sqlalchemy import delete

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from saas_crawler.storage import settings  # noqa: E402
from saas_crawler.storage.db import SessionLocal  # noqa: E402
from saas_crawler.storage.models import Account, AccountSecret, CrawlerTask, LoginSession  # noqa: E402


def _request(method: str, url: str, **kwargs):
    response = requests.request(method, url, timeout=20, **kwargs)
    response.raise_for_status()
    return response.json()


def main(base_url: str = "http://127.0.0.1:8010/api") -> int:
    redis = Redis.from_url(settings.REDIS_URL)
    jobs: list[str] = []
    account_id: int | None = None
    task_id: int | None = None
    login_session_id: int | None = None
    try:
        assert _request("GET", f"{base_url}/health")["status"] == "ok"
        dashboard = _request("GET", f"{base_url}/dashboard")
        assert dashboard["assets"] >= 96
        assets = _request("GET", f"{base_url}/assets")
        assert len(assets) >= 96
        creators = _request("GET", f"{base_url}/creators", params={"platform": "magnetic_juxing", "limit": 1})
        assert creators
        creator = _request(
            "GET",
            f"{base_url}/creators/{creators[0]['platform']}/{creators[0]['platform_creator_id']}",
        )
        assert creator["platform_creator_id"] == creators[0]["platform_creator_id"]

        account = _request(
            "POST",
            f"{base_url}/accounts",
            json={
                "platform": "xingtu",
                "display_name": "__api_validation__",
                "login_type": "sms",
                "phone": "13800138000",
            },
        )
        account_id = account["id"]
        assert "encrypted_value" not in account and account["phone_masked"] != "13800138000"
        tested = _request("POST", f"{base_url}/accounts/{account_id}/test")
        assert tested["status"] == "missing_cookie"

        login = _request("POST", f"{base_url}/accounts/{account_id}/login", json={"mode": "sms"})
        login_session_id = login["id"]
        match = re.search(r"([0-9a-f-]{20,})", login.get("prompt_message") or "")
        if match:
            jobs.append(match.group(1))
        submitted = _request(
            "POST",
            f"{base_url}/login-sessions/{login['id']}/submit-code",
            json={"code": "123456"},
        )
        assert submitted["status"] == "code_submitted"

        task = _request(
            "POST",
            f"{base_url}/tasks",
            json={
                "platform": "xingtu",
                "task_type": "author_square",
                "account_id": account_id,
                "params": {"max_pages": 1},
            },
        )
        task_id = task["id"]
        match = re.search(r"([0-9a-f-]{20,})", task.get("log_tail") or "")
        if match:
            jobs.append(match.group(1))
        cancelled = _request("POST", f"{base_url}/tasks/{task_id}/cancel")
        assert cancelled["status"] == "cancelled"
        print("api_verification=ok")
        return 0
    finally:
        for job_id in jobs:
            try:
                Job.fetch(job_id, connection=redis).delete()
            except Exception:
                pass
        if account_id is not None:
            if login_session_id is not None:
                redis.delete(f"login-session:{login_session_id}:code")
            with SessionLocal() as session:
                session.execute(delete(CrawlerTask).where(CrawlerTask.account_id == account_id))
                session.execute(delete(LoginSession).where(LoginSession.account_id == account_id))
                session.execute(delete(AccountSecret).where(AccountSecret.account_id == account_id))
                session.execute(delete(Account).where(Account.id == account_id))
                session.commit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010/api"))
