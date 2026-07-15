"""Playwright-backed account login sessions.

The worker persists only encrypted credentials and browser state. Screenshots are
shared through DATA_DIR so the API can expose them without returning secrets.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from saas_crawler.accounts.login_sessions import consume_code
from saas_crawler.accounts.secrets import decrypt_secret, encrypt_secret
from saas_crawler.storage import settings
from saas_crawler.storage.db import SessionLocal
from saas_crawler.storage.models import Account, AccountSecret, LoginSession, utcnow
from saas_crawler.storage.repositories import set_account_secret


LOGIN_URLS = {
    "xingtu": "https://www.xingtu.cn/ad/creator/market",
    "magnetic_juxing": "https://juxing.kuaishou.com/",
    "ks_feigua": "https://ks.feigua.cn/",
    "feigua": "https://www.feigua.cn/",
}

AUTH_COOKIE_NAMES = {
    "xingtu": {"sessionid", "sessionid_ss", "star_sessionid"},
    "magnetic_juxing": {"did", "kuaishou.server.web_st"},
}


def run_login_session(login_session_id: int) -> None:
    asyncio.run(_run_login_session(login_session_id))


async def _run_login_session(login_session_id: int) -> None:
    from playwright.async_api import async_playwright

    with SessionLocal() as session:
        login_session = session.get(LoginSession, login_session_id)
        if not login_session:
            return
        account = session.get(Account, login_session.account_id)
        if not account:
            _fail(session, login_session, None, "账号不存在。")
            return
        target_url = LOGIN_URLS.get(account.platform)
        if not target_url:
            _fail(session, login_session, account, f"平台 {account.platform} 尚未配置登录地址。")
            return
        secrets = _account_secrets(session, account.id)
        login_session.status = "starting"
        login_session.prompt_message = "正在启动登录浏览器。"
        session.commit()

    screenshot_dir = settings.SERVICE_DATA_DIR / "login_sessions" / str(login_session_id)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    latest_path = screenshot_dir / "latest.png"
    qr_path = screenshot_dir / "qr.png"
    deadline = asyncio.get_running_loop().time() + settings.LOGIN_TIMEOUT_SECONDS

    try:
        async with async_playwright() as playwright:
            launch_options: dict[str, Any] = {"headless": settings.LOGIN_HEADLESS}
            executable_path = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
            if executable_path:
                launch_options["executable_path"] = executable_path
            browser = await playwright.chromium.launch(**launch_options)
            context_options: dict[str, Any] = {"viewport": {"width": 1365, "height": 900}}
            storage_state = secrets.get("storage_state")
            if storage_state:
                try:
                    context_options["storage_state"] = json.loads(storage_state)
                except json.JSONDecodeError:
                    pass
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60_000)
            await _prepare_login(page, login_session.mode, account, secrets)

            while asyncio.get_running_loop().time() < deadline:
                if _session_should_stop(login_session_id):
                    await browser.close()
                    return
                await _capture(page, latest_path, qr_path)
                cookies = await context.cookies()
                if _is_logged_in(account.platform, cookies, page.url):
                    state = await context.storage_state()
                    _complete_login(login_session_id, cookies, state, latest_path)
                    await browser.close()
                    return

                if login_session.mode == "sms":
                    code = consume_code(login_session_id)
                    if code:
                        await _submit_sms_code(page, code)
                        _update_session(login_session_id, status="verifying", prompt="验证码已代填，正在确认登录结果。")

                prompt = await _page_prompt(page, login_session.mode)
                _update_session(
                    login_session_id,
                    status=_waiting_status(login_session.mode),
                    prompt=prompt,
                    screenshot=latest_path,
                    qr=qr_path if qr_path.exists() else None,
                )
                await asyncio.sleep(2)

            await browser.close()
        _mark_expired(login_session_id)
    except Exception as exc:
        with SessionLocal() as session:
            current = session.get(LoginSession, login_session_id)
            account = session.get(Account, current.account_id) if current else None
            if current:
                _fail(session, current, account, str(exc))


async def _prepare_login(page: Any, mode: str, account: Account, secrets: dict[str, str]) -> None:
    if mode == "password":
        username = secrets.get("username") or secrets.get("phone")
        password = secrets.get("password")
        if not username or not password:
            raise RuntimeError("账号密码登录需要保存用户名和密码。")
        await _fill_first(page, _username_selectors(), username)
        await _fill_first(page, ["input[type='password']", "input[placeholder*='密码']"], password)
        await _click_text(page, re.compile(r"登录|登\s*录|Sign\s*in", re.I))
    elif mode == "sms":
        phone = secrets.get("phone")
        if not phone:
            raise RuntimeError("短信登录需要保存手机号。")
        await _fill_first(page, _phone_selectors(), phone)
        await _click_text(page, re.compile(r"发送验证码|获取验证码|Send\s*code", re.I))


async def _submit_sms_code(page: Any, code: str) -> None:
    await _fill_first(
        page,
        [
            "input[autocomplete='one-time-code']",
            "input[placeholder*='验证码']",
            "input[name*='code']",
        ],
        code,
    )
    await _click_text(page, re.compile(r"登录|确认|提交|Sign\s*in", re.I))


async def _fill_first(page: Any, selectors: list[str], value: str) -> bool:
    for frame in page.frames:
        for selector in selectors:
            locator = frame.locator(selector).first
            try:
                if await locator.is_visible(timeout=500):
                    await locator.fill(value)
                    return True
            except Exception:
                continue
    return False


async def _click_text(page: Any, pattern: re.Pattern[str]) -> bool:
    for frame in page.frames:
        for role in ("button", "link"):
            locator = frame.get_by_role(role, name=pattern).first
            try:
                if await locator.is_visible(timeout=500):
                    await locator.click()
                    return True
            except Exception:
                continue
    return False


async def _capture(page: Any, latest_path: Path, qr_path: Path) -> None:
    await page.screenshot(path=str(latest_path), full_page=True)
    for frame in page.frames:
        for selector in ("[class*='qr'] canvas", "[class*='qrcode']", "img[src*='qr']", "canvas"):
            locator = frame.locator(selector).first
            try:
                if await locator.is_visible(timeout=200):
                    box = await locator.bounding_box()
                    if box and box["width"] >= 100 and box["height"] >= 100:
                        await locator.screenshot(path=str(qr_path))
                        return
            except Exception:
                continue


async def _page_prompt(page: Any, mode: str) -> str:
    try:
        body = (await page.locator("body").inner_text(timeout=1_000))[-4000:]
    except Exception:
        body = ""
    if any(word in body for word in ("滑块", "安全验证", "完成验证", "captcha")):
        return "页面要求人工完成安全验证，请查看最新截图。"
    return {
        "qr": "请扫描二维码，页面会自动检测登录结果。",
        "sms": "验证码发送后，请在前端输入验证码。",
        "password": "账号密码已代填，正在等待平台确认。",
        "manual": "请根据最新截图人工处理登录验证。",
    }.get(mode, "正在等待平台确认登录结果。")


def _username_selectors() -> list[str]:
    return [
        "input[autocomplete='username']",
        "input[placeholder*='账号']",
        "input[placeholder*='用户名']",
        "input[type='text']",
    ]


def _phone_selectors() -> list[str]:
    return [
        "input[type='tel']",
        "input[placeholder*='手机号']",
        "input[name*='phone']",
    ]


def _account_secrets(session: Session, account_id: int) -> dict[str, str]:
    rows = session.scalars(select(AccountSecret).where(AccountSecret.account_id == account_id)).all()
    return {row.secret_type: decrypt_secret(row.encrypted_value) for row in rows}


def _is_logged_in(platform: str, cookies: list[dict[str, Any]], url: str) -> bool:
    names = {str(cookie.get("name")) for cookie in cookies}
    required = AUTH_COOKIE_NAMES.get(platform)
    if required:
        return bool(names & required)
    auth_like = any(re.search(r"session|auth|token", name, re.I) for name in names)
    return auth_like and not any(part in url.lower() for part in ("login", "passport", "signin"))


def _waiting_status(mode: str) -> str:
    return {"qr": "awaiting_scan", "sms": "awaiting_code", "manual": "awaiting_manual"}.get(mode, "verifying")


def _update_session(
    login_session_id: int,
    *,
    status: str,
    prompt: str,
    screenshot: Path | None = None,
    qr: Path | None = None,
) -> None:
    with SessionLocal() as session:
        login_session = session.get(LoginSession, login_session_id)
        if not login_session or login_session.status in {"success", "failed", "expired"}:
            return
        login_session.status = status
        login_session.prompt_message = prompt
        if screenshot:
            login_session.latest_screenshot_path = _storage_path(screenshot)
        if qr:
            login_session.qr_image_path = _storage_path(qr)
        session.commit()


def _session_should_stop(login_session_id: int) -> bool:
    with SessionLocal() as session:
        login_session = session.get(LoginSession, login_session_id)
        return login_session is None or login_session.status in {"cancelled", "failed", "expired", "success"}


def _storage_path(path: Path) -> str:
    try:
        return path.relative_to(settings.SERVICE_DATA_DIR).as_posix()
    except ValueError:
        return str(path)


def _complete_login(login_session_id: int, cookies: list[dict[str, Any]], storage_state: dict[str, Any], screenshot: Path) -> None:
    with SessionLocal() as session:
        login_session = session.get(LoginSession, login_session_id)
        if not login_session:
            return
        account = session.get(Account, login_session.account_id)
        if not account:
            return
        cookie_header = "; ".join(f"{item['name']}={item['value']}" for item in cookies)
        set_account_secret(session, account_id=account.id, secret_type="cookie", encrypted_value=encrypt_secret(cookie_header))
        set_account_secret(
            session,
            account_id=account.id,
            secret_type="storage_state",
            encrypted_value=encrypt_secret(json.dumps(storage_state, ensure_ascii=False)),
        )
        expirations = [float(item["expires"]) for item in cookies if float(item.get("expires") or 0) > 0]
        if expirations:
            account.cookie_expires_at = datetime.fromtimestamp(min(expirations), tz=timezone.utc)
        account.status = "active"
        account.last_login_at = utcnow()
        login_session.status = "success"
        login_session.prompt_message = "登录成功，登录态已加密保存。"
        login_session.latest_screenshot_path = _storage_path(screenshot)
        login_session.completed_at = utcnow()
        session.commit()


def _mark_expired(login_session_id: int) -> None:
    with SessionLocal() as session:
        login_session = session.get(LoginSession, login_session_id)
        if not login_session:
            return
        account = session.get(Account, login_session.account_id)
        login_session.status = "expired"
        login_session.error_message = "登录会话超时。"
        if account:
            account.status = "login_expired"
        session.commit()


def _fail(session: Session, login_session: LoginSession, account: Account | None, message: str) -> None:
    login_session.status = "failed"
    login_session.error_message = message[-2000:]
    login_session.completed_at = utcnow()
    if account:
        account.status = "login_failed"
    session.commit()


def test_account_login_state(session: Session, account: Account) -> tuple[str, str]:
    secrets = _account_secrets(session, account.id)
    cookie = secrets.get("cookie")
    if not cookie:
        return "missing_cookie", "账号没有已保存的 Cookie。"
    cookie_names = {part.split("=", 1)[0].strip() for part in cookie.split(";") if "=" in part}
    required = AUTH_COOKIE_NAMES.get(account.platform)
    if required and not cookie_names.intersection(required):
        return "expired", "Cookie 中缺少平台登录会话字段。"
    target_url = LOGIN_URLS.get(account.platform)
    if not target_url:
        return "active", "已检查加密 Cookie，但该平台尚未配置在线探测地址。"
    try:
        response = requests.get(
            target_url,
            headers={"Cookie": cookie, "User-Agent": "Mozilla/5.0"},
            timeout=15,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        return "unknown", f"平台连接失败：{exc}"
    if response.status_code >= 400 or any(part in response.url.lower() for part in ("login", "passport", "signin")):
        return "expired", f"平台返回未登录状态：HTTP {response.status_code}。"
    return "active", f"登录态在线探测成功：HTTP {response.status_code}。"
