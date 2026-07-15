"""Login-session state management.

The first service version stores interaction state and screenshots. Platform-
specific browser automation can update these records from workers.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session
from redis import Redis

from saas_crawler.storage import settings
from saas_crawler.storage.models import Account, LoginSession, utcnow
from saas_crawler.storage.repositories import create_login_session


def start_login_session(session: Session, account: Account, mode: str) -> LoginSession:
    login_session = create_login_session(
        session,
        account=account,
        mode=mode,
        prompt_message=_prompt_for_mode(mode),
    )
    login_session.expires_at = utcnow() + timedelta(minutes=10)
    account.status = "login_pending"
    session.flush()
    return login_session


def _prompt_for_mode(mode: str) -> str:
    if mode == "qr":
        return "等待扫码确认。"
    if mode == "sms":
        return "等待输入短信验证码。"
    if mode == "password":
        return "正在使用已保存账号密码登录。"
    return "等待人工完成验证。"


def submit_code(session: Session, login_session: LoginSession, code: str) -> LoginSession:
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis.setex(_code_key(login_session.id), 300, code)
    login_session.prompt_message = "验证码已提交，等待平台确认。"
    login_session.status = "code_submitted"
    session.flush()
    return login_session


def consume_code(login_session_id: int) -> str | None:
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    key = _code_key(login_session_id)
    code = redis.get(key)
    if code:
        redis.delete(key)
    return code


def _code_key(login_session_id: int) -> str:
    return f"login-session:{login_session_id}:code"
