"""Account and login-session routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from saas_crawler.accounts.login_sessions import start_login_session, submit_code
from saas_crawler.accounts.login_runner import test_account_login_state
from saas_crawler.accounts.secrets import SecretKeyError, encrypt_secret, mask_value
from saas_crawler.storage import settings
from saas_crawler.storage.db import get_session
from saas_crawler.storage.models import Account, LoginSession
from saas_crawler.storage.repositories import create_account, set_account_secret
from saas_crawler.tasks.queue import enqueue_login_session

from .serializers import model_to_dict


router = APIRouter(tags=["accounts"])


class AccountCreate(BaseModel):
    platform: str
    display_name: str
    login_type: str
    username: str | None = None
    phone: str | None = None
    password: str | None = None
    cookie: str | None = None
    storage_state: str | None = None


class LoginCreate(BaseModel):
    mode: str | None = None


class CodeSubmit(BaseModel):
    code: str


@router.get("/accounts")
def list_accounts(session: Session = Depends(get_session)):
    accounts = session.scalars(select(Account).order_by(desc(Account.id))).all()
    return [model_to_dict(account) for account in accounts]


@router.post("/accounts")
def add_account(payload: AccountCreate, session: Session = Depends(get_session)):
    try:
        account = create_account(
            session,
            platform=payload.platform,
            display_name=payload.display_name,
            login_type=payload.login_type,
            username_masked=mask_value(payload.username),
            phone_masked=mask_value(payload.phone),
        )
        if payload.password:
            set_account_secret(session, account_id=account.id, secret_type="password", encrypted_value=encrypt_secret(payload.password))
        if payload.username:
            set_account_secret(session, account_id=account.id, secret_type="username", encrypted_value=encrypt_secret(payload.username))
        if payload.phone:
            set_account_secret(session, account_id=account.id, secret_type="phone", encrypted_value=encrypt_secret(payload.phone))
        if payload.cookie:
            set_account_secret(session, account_id=account.id, secret_type="cookie", encrypted_value=encrypt_secret(payload.cookie))
            account.status = "active"
        if payload.storage_state:
            set_account_secret(
                session,
                account_id=account.id,
                secret_type="storage_state",
                encrypted_value=encrypt_secret(payload.storage_state),
            )
            account.status = "active"
        session.commit()
        return model_to_dict(account)
    except SecretKeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/accounts/{account_id}/login")
def login_account(account_id: int, payload: LoginCreate, session: Session = Depends(get_session)):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    mode = payload.mode or account.login_type
    login_session = start_login_session(session, account, mode)
    session.commit()
    try:
        job = enqueue_login_session(login_session.id)
        login_session.prompt_message = f"登录任务已创建：{job.id}"
        session.commit()
    except Exception as exc:
        login_session.status = "failed"
        login_session.error_message = f"登录任务入队失败：{exc}"
        account.status = "login_failed"
        session.commit()
    return model_to_dict(login_session)


@router.post("/accounts/{account_id}/test")
def test_account(account_id: int, session: Session = Depends(get_session)):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    status, message = test_account_login_state(session, account)
    account.status = status
    session.commit()
    return {"account_id": account_id, "status": account.status, "message": message}


@router.get("/login-sessions/{session_id}")
def get_login_session(session_id: int, session: Session = Depends(get_session)):
    login_session = session.get(LoginSession, session_id)
    if not login_session:
        raise HTTPException(status_code=404, detail="login session not found")
    return model_to_dict(login_session)


@router.get("/login-sessions/{session_id}/screenshot")
def get_login_screenshot(session_id: int, session: Session = Depends(get_session)):
    login_session = session.get(LoginSession, session_id)
    if not login_session:
        raise HTTPException(status_code=404, detail="login session not found")
    stored_path = login_session.qr_image_path or login_session.latest_screenshot_path
    if not stored_path:
        raise HTTPException(status_code=404, detail="screenshot not available")
    path = Path(stored_path)
    if not path.is_absolute():
        path = settings.SERVICE_DATA_DIR / path
    if not path.exists():
        raise HTTPException(status_code=404, detail="screenshot not available")
    return FileResponse(path)


@router.post("/login-sessions/{session_id}/submit-code")
def submit_login_code(session_id: int, payload: CodeSubmit, session: Session = Depends(get_session)):
    login_session = session.get(LoginSession, session_id)
    if not login_session:
        raise HTTPException(status_code=404, detail="login session not found")
    submit_code(session, login_session, payload.code)
    session.commit()
    return model_to_dict(login_session)


@router.post("/login-sessions/{session_id}/cancel")
def cancel_login_session(session_id: int, session: Session = Depends(get_session)):
    login_session = session.get(LoginSession, session_id)
    if not login_session:
        raise HTTPException(status_code=404, detail="login session not found")
    if login_session.status not in {"success", "failed", "expired", "cancelled"}:
        login_session.status = "cancelled"
        login_session.prompt_message = "登录会话已取消。"
        account = session.get(Account, login_session.account_id)
        if account:
            account.status = "login_cancelled"
        session.commit()
    return model_to_dict(login_session)
