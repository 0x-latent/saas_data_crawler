"""Xingtu creator market API probe.

Usage:
  1. Add xingtu_cookies to config.yaml, or set XINGTU_COOKIE.
  2. Run:
     .venv/Scripts/python.exe -m scripts.xingtu_scraper --action probe

The Xingtu market API is protected by frontend gateway/security headers. This
script uses Playwright to let the real page create the signed request, then
captures the request payload and JSON response for schema analysis.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import csv
import getpass
import json
import os
import time
from collections import deque
from datetime import datetime
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any

import requests
from tqdm import tqdm

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

try:
    import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    from scripts import _bootstrap  # noqa: F401

from saas_crawler.core.config import load_yaml_config, require_cookie_list
from saas_crawler.core.paths import CONFIG_FILE, DATA_DIR, ensure_runtime_dirs


BASE_URL = "https://www.xingtu.cn"
MARKET_URL = f"{BASE_URL}/ad/creator/market"
AUTHOR_SQUARE_API = "/gw/api/gsearch/search_for_author_square"
COOKIE_ENV = "XINGTU_COOKIE"
REQUEST_DELAY = 1.0


class XingtuProbeError(Exception):
    """Xingtu probe error."""


def load_cookie(args: argparse.Namespace) -> str:
    if args.cookie_file:
        return Path(args.cookie_file).read_text(encoding="utf-8-sig").strip()
    if args.prompt_cookie:
        return getpass.getpass("Xingtu Cookie: ").strip()

    cookie = os.getenv(COOKIE_ENV, "").strip()
    if cookie:
        return cookie

    try:
        cfg = load_yaml_config(CONFIG_FILE)
        return require_cookie_list(cfg, "xingtu_cookies")[0]
    except (FileNotFoundError, ValueError) as e:
        print(f"Missing xingtu_cookies in {CONFIG_FILE}, or set {COOKIE_ENV}.")
        print(e)
        raise SystemExit(1) from e


def cookie_header_to_playwright(cookie_header: str) -> list[dict[str, Any]]:
    parsed = SimpleCookie()
    parsed.load(cookie_header)
    cookies: list[dict[str, Any]] = []
    for morsel in parsed.values():
        if not morsel.key:
            continue
        cookies.append({
            "name": morsel.key,
            "value": morsel.value,
            "domain": ".xingtu.cn",
            "path": "/",
            "secure": True,
            "httpOnly": False,
            "sameSite": "Lax",
        })
    if not cookies:
        raise XingtuProbeError("Cookie header is empty or invalid.")
    return cookies


def summarize_shape(value: Any, depth: int = 0, max_depth: int = 5) -> Any:
    if depth > max_depth:
        return "list" if isinstance(value, list) else type(value).__name__
    if isinstance(value, dict):
        return {key: summarize_shape(child, depth + 1, max_depth) for key, child in list(value.items())[:100]}
    if isinstance(value, list):
        return [summarize_shape(value[0], depth + 1, max_depth)] if value else []
    return type(value).__name__


def find_first_list(value: Any) -> list[dict[str, Any]]:
    queue: deque[Any] = deque([value])
    while queue:
        current = queue.popleft()
        if isinstance(current, list):
            if current and isinstance(current[0], dict):
                return current
            queue.extend(child for child in current if isinstance(child, (dict, list)))
        elif isinstance(current, dict):
            queue.extend(child for child in current.values() if isinstance(child, (dict, list)))
    return []


def leaf_paths(value: Any, max_paths: int = 300) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    queue: deque[tuple[str, Any]] = deque([("", value)])
    while queue and len(paths) < max_paths:
        path, current = queue.popleft()
        if isinstance(current, dict):
            for key, child in current.items():
                queue.append((f"{path}.{key}" if path else str(key), child))
        elif isinstance(current, list):
            if current:
                queue.append((f"{path}[]", current[0]))
            else:
                paths.append({"path": f"{path}[]", "type": "empty_list", "sample": ""})
        else:
            sample = current if current is None or isinstance(current, (str, int, float, bool)) else ""
            if isinstance(sample, str) and len(sample) > 160:
                sample = f"{sample[:160]}..."
            paths.append({"path": path, "type": type(current).__name__, "sample": sample})
    return paths


async def wait_for_author_square(page: Page, timeout_ms: int) -> dict[str, Any]:
    captured: dict[str, Any] = {"requests": [], "responses": []}

    async def on_request(request):
        if AUTHOR_SQUARE_API not in request.url:
            return
        post_data: Any = request.post_data
        try:
            post_data = request.post_data_json
        except Exception:
            pass
        headers = {
            key: value
            for key, value in (await request.all_headers()).items()
            if key.lower() not in {"cookie", "authorization"}
        }
        captured["requests"].append({
            "method": request.method,
            "url": request.url,
            "headers": headers,
            "post_data": post_data,
        })

    async def on_response(response):
        if AUTHOR_SQUARE_API not in response.url:
            return
        try:
            body = await response.json()
        except Exception:
            body = await response.text()
        captured["responses"].append({
            "status": response.status,
            "url": response.url,
            "body": body,
        })

    page.on("request", on_request)
    page.on("response", on_response)

    await page.goto(MARKET_URL, wait_until="domcontentloaded", timeout=60_000)
    try:
        await page.wait_for_load_state("networkidle", timeout=30_000)
    except PlaywrightTimeoutError:
        pass

    deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
    while asyncio.get_running_loop().time() < deadline:
        if captured["responses"]:
            return captured
        await asyncio.sleep(0.5)

    raise XingtuProbeError(f"Timed out waiting for {AUTHOR_SQUARE_API}")


async def probe(args: argparse.Namespace) -> Path:
    ensure_runtime_dirs()
    cookie_header = load_cookie(args)
    output_path = DATA_DIR / f"xingtu_author_square_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    captured = await capture_author_square(cookie_header, args)

    body = captured["responses"][0]["body"] if captured["responses"] else {}
    output = {
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "market_url": MARKET_URL,
        "api_path": AUTHOR_SQUARE_API,
        "request_count": len(captured["requests"]),
        "response_count": len(captured["responses"]),
        "captured": captured,
        "response_shape": summarize_shape(body),
        "response_leaf_paths": leaf_paths(body),
    }

    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print_probe_summary(output_path, captured, body)
    return output_path


async def capture_author_square(cookie_header: str, args: argparse.Namespace) -> dict[str, Any]:
    async with async_playwright() as p:
        browser: Browser | None = None
        context: BrowserContext | None = None
        if args.cdp_url:
            browser = await p.chromium.connect_over_cdp(args.cdp_url)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
        else:
            launch_kwargs: dict[str, Any] = {"headless": not args.headful}
            executable_path = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
            if executable_path:
                launch_kwargs["executable_path"] = executable_path
            elif args.browser_channel:
                launch_kwargs["channel"] = args.browser_channel
            browser = await p.chromium.launch(**launch_kwargs)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/136.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1440, "height": 1000},
            )
        await context.add_cookies(cookie_header_to_playwright(cookie_header))
        page = await context.new_page()
        captured = await wait_for_author_square(page, args.timeout_ms)
        await browser.close()
    return captured


def print_probe_summary(output_path: Path, captured: dict[str, Any], body: Any) -> None:
    print(f"Saved probe result: {output_path}")
    print(f"Captured requests: {len(captured['requests'])}, responses: {len(captured['responses'])}")
    if isinstance(body, dict):
        print(f"Top-level keys: {list(body.keys())}")
        base_resp = body.get("base_resp")
        if base_resp:
            print(f"base_resp: {base_resp}")
    first_items = find_first_list(body)
    print(f"First list length: {len(first_items)}")
    if first_items:
        print(f"First item keys: {list(first_items[0].keys())[:80]}")
        print(json.dumps(first_items[0], ensure_ascii=False)[:2000])


def replay_headers(captured_request: dict[str, Any], cookie_header: str) -> dict[str, str]:
    blocked = {"content-length", "accept-encoding", "cookie", "authorization"}
    headers = {
        key: value
        for key, value in (captured_request.get("headers") or {}).items()
        if not key.startswith(":") and key.lower() not in blocked
    }
    headers["Cookie"] = cookie_header
    headers.setdefault("Content-Type", "application/json")
    headers.setdefault("Accept", "application/json, text/plain, */*")
    return headers


def post_author_square(
    session: requests.Session,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = session.post(f"{BASE_URL}{AUTHOR_SQUARE_API}", headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    body = response.json()
    base_resp = body.get("base_resp") or {}
    if base_resp.get("status_code") not in (None, 0):
        raise XingtuProbeError(f"API error: {base_resp}")
    return body


def flatten_author(author: dict[str, Any]) -> dict[str, Any]:
    row = {
        "star_id": author.get("star_id", ""),
        "_task_infos": json.dumps(author.get("task_infos") or [], ensure_ascii=False),
        "_items": json.dumps(author.get("items") or [], ensure_ascii=False),
        "_extra_data": json.dumps(author.get("extra_data") or {}, ensure_ascii=False),
    }
    for key, value in (author.get("attribute_datas") or {}).items():
        row[key] = value
    return row


def write_authors_csv(path: Path, authors: list[dict[str, Any]]) -> None:
    rows = [flatten_author(author) for author in authors]
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


async def collect(args: argparse.Namespace) -> dict[str, Path]:
    ensure_runtime_dirs()
    cookie_header = load_cookie(args)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_output = DATA_DIR / f"xingtu_author_square_{timestamp}.json"
    csv_output = DATA_DIR / f"xingtu_author_square_{timestamp}.csv"

    captured = await capture_author_square(cookie_header, args)
    if not captured["requests"]:
        raise XingtuProbeError("No author square request captured.")

    seed_body = captured["responses"][0]["body"] if captured["responses"] else {}
    seed_payload = captured["requests"][0]["post_data"]
    if not isinstance(seed_payload, dict):
        raise XingtuProbeError("Captured request body is not JSON.")

    headers = replay_headers(captured["requests"][0], cookie_header)
    pagination = seed_body.get("pagination") if isinstance(seed_body, dict) else {}
    total_count = int((pagination or {}).get("total_count") or 0)
    page_size = args.page_size or int((pagination or {}).get("limit") or 20)
    total_pages = (total_count + page_size - 1) // page_size if total_count else args.max_pages
    max_pages = min(args.max_pages, total_pages) if args.max_pages else total_pages

    pages: list[dict[str, Any]] = []
    authors: list[dict[str, Any]] = []
    session = requests.Session()

    for page_num in tqdm(range(1, max_pages + 1), desc="Xingtu pages", unit="page"):
        payload = copy.deepcopy(seed_payload)
        payload.setdefault("page_param", {})
        payload["page_param"]["page"] = str(page_num)
        payload["page_param"]["limit"] = str(page_size)
        if page_num == 1 and isinstance(seed_body, dict) and int((pagination or {}).get("limit") or 0) == page_size:
            body = seed_body
        else:
            body = post_author_square(session, headers, payload)
            time.sleep(args.delay)
        page_authors = body.get("authors") or []
        pages.append({
            "page": page_num,
            "payload": payload,
            "pagination": body.get("pagination"),
            "base_resp": body.get("base_resp"),
            "authors_count": len(page_authors),
        })
        authors.extend(page_authors)
        if not (body.get("pagination") or {}).get("has_more"):
            break

    result = {
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "market_url": MARKET_URL,
        "api_path": AUTHOR_SQUARE_API,
        "total_count": total_count,
        "page_size": page_size,
        "pages": pages,
        "authors": authors,
        "seed_request": {
            "headers": {key: value for key, value in headers.items() if key.lower() != "cookie"},
            "post_data": seed_payload,
        },
    }
    json_output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_authors_csv(csv_output, authors)

    print(f"Saved JSON: {json_output}")
    print(f"Saved CSV: {csv_output}")
    print(f"Authors: {len(authors)}, pages: {len(pages)}, total_count: {total_count}")
    return {"json": json_output, "csv": csv_output}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Xingtu creator market scraper/probe")
    parser.add_argument("--action", choices=["probe", "collect"], default="probe")
    parser.add_argument("--cookie-file", default=None, help="Local text file containing one Cookie header value")
    parser.add_argument("--prompt-cookie", action="store_true", help="Prompt for Cookie instead of config/env")
    parser.add_argument("--headful", action="store_true", help="Show browser window for manual verification/captcha")
    parser.add_argument("--browser-channel", default=None, help="Playwright browser channel, e.g. chrome or msedge")
    parser.add_argument("--cdp-url", default=None, help="Connect to an existing debug browser, e.g. http://localhost:9222")
    parser.add_argument("--timeout-ms", type=int, default=45_000)
    parser.add_argument("--max-pages", type=int, default=1, help="Maximum pages to collect; 0 means all pages")
    parser.add_argument("--page-size", type=int, default=None, help="Override captured page size")
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY, help="Delay between replayed API requests")
    return parser


async def async_main() -> None:
    args = build_parser().parse_args()
    if args.action == "probe":
        await probe(args)
    elif args.action == "collect":
        if args.max_pages == 0:
            args.max_pages = 10**9
        await collect(args)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
