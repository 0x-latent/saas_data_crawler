"""Magnetic Juxing star list API probe and scraper.

Usage:
  1. Put magnetic_juxing_cookies in config.yaml, or set
     MAGNETIC_JUXING_COOKIE for one-off probing.
  2. Run:
     .venv/Scripts/python.exe -m scripts.magnetic_juxing_scraper --action probe
     .venv/Scripts/python.exe -m scripts.magnetic_juxing_scraper --action hot-home
     .venv/Scripts/python.exe -m scripts.magnetic_juxing_scraper --action hot-list
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

try:
    import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    from scripts import _bootstrap  # noqa: F401

from saas_crawler.core.config import build_browser_headers, load_yaml_config, require_cookie_list
from saas_crawler.core.paths import CONFIG_FILE, DATA_DIR, ensure_runtime_dirs


BASE_URL = "https://k.kuaishou.com"
LIST_PATH = "/rest/web/star/list"
HOT_HOME_PATH = "/rest/web/hot/homePage"
HOT_STAR_LIST_PATH = "/rest/web/hot/star/list"
DETAIL_BASE_INFO_PATH = "/rest/web/star/match/starPage/baseInfo"
VIDEO_REPRESENTATIVE_WORKS_PATH = "/rest/web/post/video/representative/works/info/list"
VIDEO_WORKS_STATISTICS_PATH = "/rest/web/post/video/works/statistics/get"
STAR_PORTRAIT_PATH = "/rest/web/star/listPortrait"
VIDEO_BUSINESS_REPORT_PATH = "/rest/web/post/video/business/report/get"
REQUEST_DELAY = 1.0
REQUEST_RETRIES = 3
RETRYABLE_API_MESSAGES = ("网络繁忙", "稍后重试", "timeout", "timed out")
DEFAULT_ACCOUNT_ID = "112250379"
DEFAULT_HOT_RANKS: dict[str, dict[str, Any]] = {
    "develop": {"hotId": 104, "starType": 1, "name": "发展力表现榜"},
    "cost_performance": {"hotId": 5, "starType": 1, "name": "性价比表现榜"},
    "live_sales": {"hotId": 7, "starType": 4, "name": "带货实力榜"},
    "spread": {"hotId": 105, "starType": 1, "name": "传播力表现榜"},
    "live_popularity": {"hotId": 8, "starType": 4, "name": "人气主播榜"},
    "fans": {"hotId": 6, "starType": 1, "name": "涨粉表现榜"},
}
DEFAULT_LIVE_LIST_PAYLOAD: dict[str, Any] = {
    "currentPage": 1,
    "pageSize": 20,
    "starOrderTag": 2,
    "starOrderType": 2,
    "taskType": 4,
    "viewerCityPercentage": [],
    "fansCityPercentage": [],
    "starTagIds": [],
    "pickList": [],
    "advertiserPickList": [],
    "pathSource": "no_filter_live",
}
DEFAULT_DB_FILE = DATA_DIR / "magnetic_juxing.sqlite"


class MagneticJuxingError(Exception):
    """Magnetic Juxing API error."""


def is_retryable_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(token.lower() in message for token in RETRYABLE_API_MESSAGES)


def load_account_id(args: argparse.Namespace) -> str:
    if args.account_id:
        return str(args.account_id).strip()

    env_account_id = os.getenv("MAGNETIC_JUXING_ACCOUNT_ID", "").strip()
    if env_account_id:
        return env_account_id

    try:
        cfg = load_yaml_config(CONFIG_FILE)
    except FileNotFoundError:
        return DEFAULT_ACCOUNT_ID

    section = cfg.get("magnetic_juxing", {}) or {}
    return str(section.get("account_id") or DEFAULT_ACCOUNT_ID).strip()


def load_headers(cookie_file: str | None = None, account_id: str | None = None) -> dict[str, str]:
    cookie = ""
    if cookie_file:
        cookie = Path(cookie_file).read_text(encoding="utf-8-sig").strip()
    if not cookie:
        cookie = os.getenv("MAGNETIC_JUXING_COOKIE", "")
    if not cookie:
        try:
            cfg = load_yaml_config(CONFIG_FILE)
            cookie = require_cookie_list(cfg, "magnetic_juxing_cookies")[0]
        except (FileNotFoundError, ValueError) as e:
            print(f"Missing magnetic_juxing_cookies in {CONFIG_FILE}")
            print(e)
            raise SystemExit(1) from e

    headers = build_browser_headers(cookie, f"{BASE_URL}/")
    headers.update({
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": BASE_URL,
    })
    if account_id:
        headers["ACCOUNT-ID"] = str(account_id)
    return headers


def decode_response(response: requests.Response, request_name: str) -> dict[str, Any]:
    response.raise_for_status()
    try:
        body = response.json()
    except json.JSONDecodeError as e:
        raise MagneticJuxingError(f"{request_name} returned non-JSON: {response.text[:200]}") from e

    code = body.get("result", body.get("code"))
    if code not in (None, 0, 1, 200, True):
        message = body.get("error_msg") or body.get("msg") or body.get("message")
        raise MagneticJuxingError(f"{request_name} API error code={code} msg={message}")
    return body


def api_request(
    session: requests.Session,
    headers: dict[str, str],
    method: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{BASE_URL}{LIST_PATH}"
    if method == "GET":
        response = session.get(url, headers=headers, timeout=30)
    else:
        response = session.post(url, headers=headers, json=payload or {}, timeout=30)
    return decode_response(response, f"{method} {LIST_PATH}")


def api_post_path(
    session: requests.Session,
    headers: dict[str, str],
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            response = session.post(f"{BASE_URL}{path}", headers=headers, json=payload or {}, timeout=30)
            return decode_response(response, f"POST {path}")
        except (requests.RequestException, MagneticJuxingError) as e:
            last_error = e
            if attempt >= REQUEST_RETRIES or not is_retryable_error(e):
                raise
            sleep_seconds = REQUEST_DELAY * attempt * 2
            print(f"Retry {attempt}/{REQUEST_RETRIES - 1} after {sleep_seconds:.1f}s: POST {path} {e}")
            time.sleep(sleep_seconds)
    raise MagneticJuxingError(f"POST {path} failed: {last_error}")


def summarize_shape(value: Any, depth: int = 0, max_depth: int = 4) -> Any:
    if depth > max_depth:
        return "list" if isinstance(value, list) else type(value).__name__
    if isinstance(value, dict):
        return {
            key: summarize_shape(child, depth + 1, max_depth)
            for key, child in list(value.items())[:100]
        }
    if isinstance(value, list):
        return [summarize_shape(value[0], depth + 1, max_depth)] if value else []
    return type(value).__name__


def leaf_paths(value: Any, max_paths: int = 300) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    queue: deque[tuple[str, Any]] = deque([("", value)])
    while queue and len(paths) < max_paths:
        path, current = queue.popleft()
        if isinstance(current, dict):
            for key, child in current.items():
                child_path = f"{path}.{key}" if path else str(key)
                queue.append((child_path, child))
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


def find_first_list(value: Any) -> list[dict[str, Any]]:
    queue: deque[Any] = deque([value])
    while queue:
        current = queue.popleft()
        if isinstance(current, list):
            if not current:
                continue
            if isinstance(current[0], dict):
                return current
            continue
        if isinstance(current, dict):
            for child in current.values():
                if isinstance(child, (dict, list)):
                    queue.append(child)
    return []


def find_total(value: Any) -> int | None:
    total_keys = {"total", "totalCount", "count", "totalNum", "recordTotal", "total_count"}
    queue: deque[Any] = deque([value])
    while queue:
        current = queue.popleft()
        if isinstance(current, dict):
            for key, child in current.items():
                if key in total_keys:
                    try:
                        return int(child)
                    except (TypeError, ValueError):
                        pass
                if isinstance(child, (dict, list)):
                    queue.append(child)
        elif isinstance(current, list):
            queue.extend(child for child in current if isinstance(child, (dict, list)))
    return None


def probe(session: requests.Session, headers: dict[str, str]) -> dict[str, Any]:
    cases: list[tuple[str, str, dict[str, Any] | None]] = [
        ("get", "GET", None),
        ("post_empty", "POST", {}),
        ("post_page_num", "POST", {"pageNum": 1, "pageSize": 20}),
        ("post_page", "POST", {"page": 1, "pageSize": 20}),
        ("post_current", "POST", {"currentPage": 1, "pageSize": 20}),
        ("post_common", "POST", {"pageNum": 1, "pageSize": 20, "sortType": 0, "order": 0}),
    ]
    results = []
    for name, method, payload in cases:
        started = time.time()
        try:
            body = api_request(session, headers, method, payload)
            items = find_first_list(body)
            results.append({
                "case": name,
                "method": method,
                "payload": payload,
                "ok": True,
                "elapsed_seconds": round(time.time() - started, 3),
                "top_keys": list(body.keys()) if isinstance(body, dict) else [],
                "total": find_total(body),
                "item_count": len(items),
                "item_keys": list(items[0].keys()) if items else [],
                "shape": summarize_shape(body),
                "leaf_paths": leaf_paths(body),
                "raw": body,
            })
        except (requests.RequestException, MagneticJuxingError) as e:
            results.append({
                "case": name,
                "method": method,
                "payload": payload,
                "ok": False,
                "elapsed_seconds": round(time.time() - started, 3),
                "error": str(e),
            })
        time.sleep(REQUEST_DELAY)

    return {
        "platform": "magnetic_juxing",
        "action": "probe",
        "url": f"{BASE_URL}{LIST_PATH}",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "results": results,
    }


def list_payload(page: int, page_size: int) -> dict[str, Any]:
    return {"pageNum": page, "pageSize": page_size}


def fetch_list_pages(
    session: requests.Session,
    headers: dict[str, str],
    page_size: int,
    max_pages: int,
    base_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pages = []
    all_items: list[dict[str, Any]] = []
    total: int | None = None
    for page in range(1, max_pages + 1):
        payload = dict(base_payload or list_payload(page, page_size))
        payload["currentPage"] = page
        payload["pageSize"] = page_size
        body = api_request(session, headers, "POST", payload)
        items = body.get("starList") if isinstance(body.get("starList"), list) else find_first_list(body)
        total = int(body["total"]) if total is None and body.get("total") is not None else total
        total = find_total(body) if total is None else total
        pages.append({"page": page, "payload": payload, "item_count": len(items), "raw": body})
        all_items.extend(items)
        if not items or len(items) < page_size:
            break
        time.sleep(REQUEST_DELAY)
    return {
        "platform": "magnetic_juxing",
        "action": "list",
        "url": f"{BASE_URL}{LIST_PATH}",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "page_size": page_size,
        "max_pages": max_pages,
        "total": total,
        "pages": pages,
        "items": all_items,
    }


def parse_ext_data(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def annotated_star_rows(rank_key: str, rank_meta: dict[str, Any], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, item in enumerate(items, 1):
        ext_data = parse_ext_data(item.get("extData"))
        rows.append({
            "_rank_key": rank_key,
            "_rank_name": rank_meta.get("name"),
            "_hot_id": rank_meta.get("hotId"),
            "_star_type": rank_meta.get("starType"),
            "_rank_in_result": index,
            "_hot_name": ext_data.get("hotName"),
            **item,
        })
    return rows


def fetch_hot_home(session: requests.Session, headers: dict[str, str]) -> dict[str, Any]:
    body = api_post_path(session, headers, HOT_HOME_PATH, {})
    data = body.get("data") or []
    rows = []
    if isinstance(data, list):
        for group_index, group in enumerate(data, 1):
            if not isinstance(group, dict):
                continue
            group_name = group.get("name")
            for rank_in_group, item in enumerate(group.get("starList") or [], 1):
                if isinstance(item, dict):
                    rows.append({
                        "_home_group_index": group_index,
                        "_home_group_name": group_name,
                        "_rank_in_group": rank_in_group,
                        **item,
                    })
    return {
        "platform": "magnetic_juxing",
        "action": "hot-home",
        "url": f"{BASE_URL}{HOT_HOME_PATH}",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "raw": body,
        "items": rows,
    }


def fetch_hot_rank(
    session: requests.Session,
    headers: dict[str, str],
    rank_key: str,
    rank_meta: dict[str, Any],
    user_id: str | None = None,
    star_tag_ids: list[int] | None = None,
) -> dict[str, Any]:
    payload = {
        "hotId": rank_meta["hotId"],
        "starTagIds": star_tag_ids or [],
        "starType": rank_meta["starType"],
    }
    if user_id:
        payload["userId"] = user_id
    body = api_post_path(session, headers, HOT_STAR_LIST_PATH, payload)
    data = body.get("data") or {}
    items = data.get("starList") or []
    return {
        "rank_key": rank_key,
        "rank_meta": rank_meta,
        "payload": payload,
        "total": data.get("total"),
        "create_time": data.get("createTime"),
        "cart_type": data.get("cartType"),
        "star_tags": data.get("starTags") or [],
        "field_conf": (data.get("conf") or {}).get("fieldConf") or [],
        "description": (data.get("conf") or {}).get("description"),
        "raw": body,
        "items": annotated_star_rows(rank_key, rank_meta, items),
    }


def resolve_rank_keys(value: str) -> list[str]:
    if value == "all":
        return list(DEFAULT_HOT_RANKS)
    keys = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [key for key in keys if key not in DEFAULT_HOT_RANKS]
    if unknown:
        raise MagneticJuxingError(f"Unknown hot rank key(s): {', '.join(unknown)}")
    return keys


def fetch_hot_ranks(
    session: requests.Session,
    headers: dict[str, str],
    rank_keys: list[str],
    user_id: str | None = None,
    continue_on_error: bool = False,
) -> dict[str, Any]:
    ranks = []
    rows = []
    failures = []
    for rank_key in rank_keys:
        try:
            rank = fetch_hot_rank(session, headers, rank_key, DEFAULT_HOT_RANKS[rank_key], user_id=user_id)
            ranks.append(rank)
            rows.extend(rank["items"])
        except (requests.RequestException, MagneticJuxingError) as e:
            if not continue_on_error:
                raise
            failure = {
                "rank_key": rank_key,
                "rank_meta": DEFAULT_HOT_RANKS[rank_key],
                "error": str(e),
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
            }
            failures.append(failure)
            print(f"Hot rank skipped: {rank_key} error={e}")
        time.sleep(REQUEST_DELAY)
    return {
        "platform": "magnetic_juxing",
        "action": "hot-list",
        "url": f"{BASE_URL}{HOT_STAR_LIST_PATH}",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "ranks": ranks,
        "failures": failures,
        "items": rows,
    }


def detail_base_payload(
    star_id: int | str,
    star_type: int,
    path_source: str | None = None,
    penetration_json: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "starId": star_id,
        "starType": star_type,
    }
    if path_source:
        payload["pathSource"] = path_source
    if penetration_json:
        payload["penetrationJSON"] = penetration_json
    return payload


def fetch_star_detail(
    session: requests.Session,
    headers: dict[str, str],
    star_id: int | str,
    star_type: int,
    path_source: str | None = None,
    penetration_json: str | None = None,
    works_nature: bool | None = False,
) -> dict[str, Any]:
    base_payload = detail_base_payload(star_id, star_type, path_source, penetration_json)
    works_payload: dict[str, Any] = {"starId": star_id}
    if star_type:
        works_payload["starType"] = star_type
    if path_source:
        works_payload["pathSource"] = path_source
    if penetration_json:
        works_payload["penetrationJSON"] = penetration_json
    if works_nature is not None:
        works_payload["nature"] = works_nature

    base_info = api_post_path(session, headers, DETAIL_BASE_INFO_PATH, base_payload)
    time.sleep(REQUEST_DELAY)
    representative_works = api_post_path(session, headers, VIDEO_REPRESENTATIVE_WORKS_PATH, works_payload)
    time.sleep(REQUEST_DELAY)
    portrait = api_post_path(session, headers, STAR_PORTRAIT_PATH, base_payload)

    return {
        "star_id": star_id,
        "star_type": star_type,
        "path_source": path_source,
        "base_payload": base_payload,
        "works_payload": works_payload,
        "base_info": base_info,
        "representative_works": representative_works,
        "portrait": portrait,
    }


def flatten_portrait_rows(star_id: Any, star_type: Any, portrait_data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for portrait_name, groups in portrait_data.items():
        if not isinstance(groups, dict):
            continue
        for group_name, values in groups.items():
            if isinstance(values, list):
                for index, item in enumerate(values, 1):
                    row = {
                        "_star_id": star_id,
                        "_star_type": star_type,
                        "_portrait": portrait_name,
                        "_group": group_name,
                        "_index": index,
                    }
                    if isinstance(item, dict):
                        row.update(item)
                    else:
                        row["value"] = item
                    rows.append(row)
            elif values not in (None, "", [], {}):
                rows.append({
                    "_star_id": star_id,
                    "_star_type": star_type,
                    "_portrait": portrait_name,
                    "_group": group_name,
                    "_index": "",
                    "value": values,
                })
    return rows


def flatten_detail_rows(detail: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    star_id = detail.get("star_id")
    star_type = detail.get("star_type")
    base_data = detail.get("base_info", {}).get("data") or {}
    base_rows = [{
        "_star_id": star_id,
        "_star_type": star_type,
        **base_data,
    }] if base_data else []

    works = detail.get("representative_works", {}).get("data", {}).get("detailList") or []
    work_rows = []
    for index, item in enumerate(works, 1):
        if isinstance(item, dict):
            work_rows.append({
                "_star_id": star_id,
                "_star_type": star_type,
                "_work_index": index,
                **item,
            })

    portrait_data = detail.get("portrait", {}).get("data") or {}
    portrait_rows = flatten_portrait_rows(star_id, star_type, portrait_data)
    return base_rows, work_rows, portrait_rows


def fetch_details(
    session: requests.Session,
    headers: dict[str, str],
    star_ids: list[str],
    star_type: int,
    path_source: str | None = None,
    penetration_json: str | None = None,
    works_nature: bool | None = False,
) -> dict[str, Any]:
    details = []
    base_rows = []
    work_rows = []
    portrait_rows = []
    failures = []
    for star_id in star_ids:
        try:
            detail = fetch_star_detail(
                session,
                headers,
                star_id,
                star_type,
                path_source=path_source,
                penetration_json=penetration_json,
                works_nature=works_nature,
            )
            details.append(detail)
            rows, works, portraits = flatten_detail_rows(detail)
            base_rows.extend(rows)
            work_rows.extend(works)
            portrait_rows.extend(portraits)
        except (requests.RequestException, MagneticJuxingError) as e:
            failures.append({
                "star_id": star_id,
                "star_type": star_type,
                "error": str(e),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            })
        time.sleep(REQUEST_DELAY)

    return {
        "platform": "magnetic_juxing",
        "action": "detail",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "detail_endpoints": {
            "base_info": f"{BASE_URL}{DETAIL_BASE_INFO_PATH}",
            "representative_works": f"{BASE_URL}{VIDEO_REPRESENTATIVE_WORKS_PATH}",
            "portrait": f"{BASE_URL}{STAR_PORTRAIT_PATH}",
            "works_statistics": f"{BASE_URL}{VIDEO_WORKS_STATISTICS_PATH}",
            "business_report": f"{BASE_URL}{VIDEO_BUSINESS_REPORT_PATH}",
        },
        "star_type": star_type,
        "path_source": path_source,
        "works_nature": works_nature,
        "details": details,
        "base_rows": base_rows,
        "work_rows": work_rows,
        "portrait_rows": portrait_rows,
        "failures": failures,
    }


def save_json_result(result: dict[str, Any], prefix: str) -> Path:
    ensure_runtime_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = DATA_DIR / f"{prefix}_{timestamp}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def save_items_csv(items: list[dict[str, Any]], prefix: str) -> Path:
    ensure_runtime_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = DATA_DIR / f"{prefix}_{timestamp}.csv"
    headers: list[str] = []
    seen = set()
    for item in items:
        for key in item:
            if key not in seen:
                headers.append(key)
                seen.add(key)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for item in items:
            writer.writerow({
                key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                for key, value in item.items()
            })
    return path


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def scalar(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json_dumps(value)
    return value


def as_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def open_sqlite(path: Path) -> sqlite3.Connection:
    ensure_runtime_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_sqlite(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            action TEXT NOT NULL,
            account_id TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            params_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS raw_api_response (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            action TEXT NOT NULL,
            account_id TEXT,
            fetched_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            response_json TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        );

        CREATE TABLE IF NOT EXISTS dim_star (
            star_id TEXT PRIMARY KEY,
            user_id TEXT,
            kwai_id TEXT,
            name TEXT,
            gender TEXT,
            fans_number INTEGER,
            head_url TEXT,
            profile_id TEXT,
            profile_url TEXT,
            mcn_id TEXT,
            mcn_name TEXT,
            updated_at TEXT NOT NULL,
            latest_source_json TEXT NOT NULL,
            latest_detail_json TEXT
        );

        CREATE TABLE IF NOT EXISTS fact_star_source (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            star_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            account_id TEXT,
            fetched_at TEXT NOT NULL,
            page INTEGER,
            rank INTEGER,
            rank_key TEXT,
            rank_name TEXT,
            hot_id INTEGER,
            star_type INTEGER,
            task_type INTEGER,
            star_order_tag INTEGER,
            star_order_type INTEGER,
            path_source TEXT,
            payload_json TEXT NOT NULL,
            item_json TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        );

        CREATE TABLE IF NOT EXISTS star_detail_base (
            star_id TEXT NOT NULL,
            star_type INTEGER NOT NULL,
            fetched_at TEXT NOT NULL,
            data_json TEXT NOT NULL,
            PRIMARY KEY(star_id, star_type)
        );

        CREATE TABLE IF NOT EXISTS star_work (
            star_id TEXT NOT NULL,
            star_type INTEGER NOT NULL,
            photo_id TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            caption TEXT,
            like_cnt INTEGER,
            view_cnt INTEGER,
            forward_cnt INTEGER,
            comment_cnt INTEGER,
            release_time_millis INTEGER,
            business INTEGER,
            product_name TEXT,
            first_industry_id INTEGER,
            first_industry_name TEXT,
            data_json TEXT NOT NULL,
            PRIMARY KEY(star_id, star_type, photo_id)
        );

        CREATE TABLE IF NOT EXISTS star_portrait (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            star_id TEXT NOT NULL,
            star_type INTEGER NOT NULL,
            fetched_at TEXT NOT NULL,
            portrait TEXT NOT NULL,
            group_name TEXT NOT NULL,
            item_index INTEGER,
            label TEXT,
            value REAL,
            tgi REAL,
            item_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_raw_run ON raw_api_response(run_id);
        CREATE INDEX IF NOT EXISTS idx_source_star ON fact_star_source(star_id);
        CREATE INDEX IF NOT EXISTS idx_source_run ON fact_star_source(run_id);
        CREATE INDEX IF NOT EXISTS idx_work_star ON star_work(star_id);
        CREATE INDEX IF NOT EXISTS idx_portrait_star ON star_portrait(star_id);

        CREATE VIEW IF NOT EXISTS v_run_summary AS
        SELECT
            r.run_id,
            r.action,
            r.account_id,
            r.started_at,
            r.finished_at,
            r.status,
            COUNT(DISTINCT s.star_id) AS discovered_stars,
            COUNT(DISTINCT CASE WHEN d.star_id IS NOT NULL THEN d.star_id END) AS detail_stars,
            COUNT(DISTINCT w.photo_id) AS works,
            COUNT(DISTINCT p.id) AS portrait_rows,
            r.params_json
        FROM runs r
        LEFT JOIN fact_star_source s ON s.run_id = r.run_id
        LEFT JOIN star_detail_base d ON d.star_id = s.star_id
        LEFT JOIN star_work w ON w.star_id = s.star_id
        LEFT JOIN star_portrait p ON p.star_id = s.star_id
        GROUP BY r.run_id;

        CREATE VIEW IF NOT EXISTS v_star_overview AS
        SELECT
            d.star_id,
            d.user_id,
            d.kwai_id,
            d.name,
            d.gender,
            d.fans_number,
            d.profile_url,
            d.mcn_name,
            MAX(s.fetched_at) AS last_seen_at,
            COUNT(DISTINCT s.run_id) AS run_count,
            COUNT(DISTINCT s.id) AS source_count,
            GROUP_CONCAT(DISTINCT s.source_type) AS source_types,
            GROUP_CONCAT(DISTINCT s.rank_name) AS rank_names,
            MAX(b.fetched_at) AS detail_fetched_at,
            COUNT(DISTINCT w.photo_id) AS work_count,
            COUNT(DISTINCT p.portrait || ':' || p.group_name) AS portrait_group_count
        FROM dim_star d
        LEFT JOIN fact_star_source s ON s.star_id = d.star_id
        LEFT JOIN star_detail_base b ON b.star_id = d.star_id
        LEFT JOIN star_work w ON w.star_id = d.star_id
        LEFT JOIN star_portrait p ON p.star_id = d.star_id
        GROUP BY d.star_id;

        CREATE VIEW IF NOT EXISTS v_star_source_latest AS
        SELECT
            s.star_id,
            d.name,
            s.source_type,
            s.endpoint,
            s.fetched_at,
            s.page,
            s.rank,
            s.rank_key,
            s.rank_name,
            s.hot_id,
            s.star_type,
            s.task_type,
            s.star_order_tag,
            s.star_order_type,
            s.path_source,
            s.run_id
        FROM fact_star_source s
        LEFT JOIN dim_star d ON d.star_id = s.star_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM fact_star_source newer
            WHERE newer.star_id = s.star_id
              AND newer.source_type = s.source_type
              AND newer.fetched_at > s.fetched_at
        );

        CREATE VIEW IF NOT EXISTS v_star_work_latest AS
        SELECT
            w.star_id,
            d.name,
            w.star_type,
            w.photo_id,
            w.fetched_at,
            w.caption,
            w.view_cnt,
            w.like_cnt,
            w.comment_cnt,
            w.forward_cnt,
            w.release_time_millis,
            w.business,
            w.product_name,
            w.first_industry_name
        FROM star_work w
        LEFT JOIN dim_star d ON d.star_id = w.star_id;

        CREATE VIEW IF NOT EXISTS v_star_portrait_latest AS
        SELECT
            p.star_id,
            d.name,
            p.star_type,
            p.fetched_at,
            p.portrait,
            p.group_name,
            p.item_index,
            p.label,
            p.value,
            p.tgi
        FROM star_portrait p
        LEFT JOIN dim_star d ON d.star_id = p.star_id;
        """
    )
    conn.commit()


def start_run(conn: sqlite3.Connection, action: str, account_id: str, params: dict[str, Any]) -> str:
    run_id = f"mj_{action}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    conn.execute(
        """
        INSERT INTO runs(run_id, platform, action, account_id, started_at, status, params_json)
        VALUES (?, 'magnetic_juxing', ?, ?, ?, 'running', ?)
        """,
        (run_id, action, account_id, now_iso(), json_dumps(params)),
    )
    conn.commit()
    return run_id


def finish_run(conn: sqlite3.Connection, run_id: str, status: str) -> None:
    conn.execute(
        "UPDATE runs SET finished_at = ?, status = ? WHERE run_id = ?",
        (now_iso(), status, run_id),
    )
    conn.commit()


def insert_raw_response(
    conn: sqlite3.Connection,
    run_id: str,
    endpoint: str,
    action: str,
    account_id: str,
    payload: dict[str, Any],
    response: dict[str, Any],
    fetched_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO raw_api_response(run_id, endpoint, action, account_id, fetched_at, payload_json, response_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, endpoint, action, account_id, fetched_at, json_dumps(payload), json_dumps(response)),
    )


def star_id_from_item(item: dict[str, Any]) -> str:
    return str(item.get("starId") or item.get("_star_id") or "").strip()


def upsert_dim_star(conn: sqlite3.Connection, item: dict[str, Any], fetched_at: str, detail: dict[str, Any] | None = None) -> None:
    star_id = star_id_from_item(item)
    if not star_id:
        return
    detail_json = json_dumps(detail) if detail else None
    conn.execute(
        """
        INSERT INTO dim_star(
            star_id, user_id, kwai_id, name, gender, fans_number, head_url,
            profile_id, profile_url, mcn_id, mcn_name, updated_at,
            latest_source_json, latest_detail_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(star_id) DO UPDATE SET
            user_id = COALESCE(excluded.user_id, dim_star.user_id),
            kwai_id = COALESCE(excluded.kwai_id, dim_star.kwai_id),
            name = COALESCE(excluded.name, dim_star.name),
            gender = COALESCE(excluded.gender, dim_star.gender),
            fans_number = COALESCE(excluded.fans_number, dim_star.fans_number),
            head_url = COALESCE(excluded.head_url, dim_star.head_url),
            profile_id = COALESCE(excluded.profile_id, dim_star.profile_id),
            profile_url = COALESCE(excluded.profile_url, dim_star.profile_url),
            mcn_id = COALESCE(excluded.mcn_id, dim_star.mcn_id),
            mcn_name = COALESCE(excluded.mcn_name, dim_star.mcn_name),
            updated_at = excluded.updated_at,
            latest_source_json = excluded.latest_source_json,
            latest_detail_json = COALESCE(excluded.latest_detail_json, dim_star.latest_detail_json)
        """,
        (
            star_id,
            str(item.get("userId")) if item.get("userId") is not None else None,
            item.get("kwaiId"),
            item.get("name"),
            item.get("gender"),
            as_int(item.get("fansNumber")),
            item.get("headUrl"),
            item.get("profileId"),
            item.get("profileUrl"),
            str(item.get("mcnId")) if item.get("mcnId") is not None else str(item.get("mcnOrgId")) if item.get("mcnOrgId") is not None else None,
            item.get("mcnName"),
            fetched_at,
            json_dumps(item),
            detail_json,
        ),
    )


def insert_star_sources(
    conn: sqlite3.Connection,
    run_id: str,
    source_type: str,
    endpoint: str,
    account_id: str,
    fetched_at: str,
    items: list[dict[str, Any]],
    payload: dict[str, Any],
    page: int | None = None,
) -> None:
    for index, item in enumerate(items, 1):
        star_id = star_id_from_item(item)
        if not star_id:
            continue
        upsert_dim_star(conn, item, fetched_at)
        conn.execute(
            """
            INSERT INTO fact_star_source(
                run_id, star_id, source_type, endpoint, account_id, fetched_at, page, rank,
                rank_key, rank_name, hot_id, star_type, task_type, star_order_tag,
                star_order_type, path_source, payload_json, item_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                star_id,
                source_type,
                endpoint,
                account_id,
                fetched_at,
                page,
                as_int(item.get("_rank_in_result")) or index,
                item.get("_rank_key"),
                item.get("_rank_name") or item.get("_home_group_name"),
                as_int(item.get("_hot_id")) or as_int(payload.get("hotId")),
                as_int(item.get("_star_type")) or as_int(payload.get("starType")),
                as_int(payload.get("taskType")),
                as_int(payload.get("starOrderTag")),
                as_int(payload.get("starOrderType")),
                item.get("pathSource") or payload.get("pathSource"),
                json_dumps(payload),
                json_dumps(item),
            ),
        )


def store_hot_home_sqlite(conn: sqlite3.Connection, run_id: str, account_id: str, result: dict[str, Any]) -> None:
    fetched_at = result["fetched_at"]
    insert_raw_response(conn, run_id, HOT_HOME_PATH, "hot-home", account_id, {}, result["raw"], fetched_at)
    insert_star_sources(conn, run_id, "hot-home", HOT_HOME_PATH, account_id, fetched_at, result["items"], {})
    conn.commit()


def store_hot_list_sqlite(conn: sqlite3.Connection, run_id: str, account_id: str, result: dict[str, Any]) -> None:
    fetched_at = result["fetched_at"]
    for failure in result.get("failures", []):
        insert_raw_response(
            conn,
            run_id,
            HOT_STAR_LIST_PATH,
            "hot-list-failure",
            account_id,
            failure.get("rank_meta") or {},
            {"rank_key": failure.get("rank_key"), "error": failure.get("error")},
            fetched_at,
        )
    for rank in result.get("ranks", []):
        payload = rank.get("payload") or {}
        insert_raw_response(conn, run_id, HOT_STAR_LIST_PATH, "hot-list", account_id, payload, rank["raw"], fetched_at)
        insert_star_sources(conn, run_id, "hot-list", HOT_STAR_LIST_PATH, account_id, fetched_at, rank["items"], payload)
    conn.commit()


def store_list_sqlite(
    conn: sqlite3.Connection,
    run_id: str,
    account_id: str,
    result: dict[str, Any],
    action: str,
    source_type: str,
) -> None:
    fetched_at = result["fetched_at"]
    for page in result.get("pages", []):
        payload = page.get("payload") or {}
        raw = page.get("raw") or {}
        items = raw.get("starList") if isinstance(raw.get("starList"), list) else page.get("raw", {}).get("items", [])
        if not items:
            items = find_first_list(raw)
        insert_raw_response(conn, run_id, LIST_PATH, action, account_id, payload, raw, fetched_at)
        insert_star_sources(conn, run_id, source_type, LIST_PATH, account_id, fetched_at, items, payload, page=page.get("page"))
    conn.commit()


def store_details_sqlite(conn: sqlite3.Connection, run_id: str, account_id: str, result: dict[str, Any]) -> None:
    fetched_at = result["fetched_at"]
    star_type = as_int(result.get("star_type")) or 1
    for detail in result.get("details", []):
        star_id = str(detail.get("star_id"))
        for endpoint_key, path in (
            ("base_info", DETAIL_BASE_INFO_PATH),
            ("representative_works", VIDEO_REPRESENTATIVE_WORKS_PATH),
            ("portrait", STAR_PORTRAIT_PATH),
        ):
            payload_key = "base_payload" if endpoint_key in ("base_info", "portrait") else "works_payload"
            insert_raw_response(
                conn,
                run_id,
                path,
                endpoint_key,
                account_id,
                detail.get(payload_key) or {},
                detail.get(endpoint_key) or {},
                fetched_at,
            )

        base_data = detail.get("base_info", {}).get("data") or {}
        if base_data:
            upsert_dim_star(conn, base_data, fetched_at, detail=base_data)
            conn.execute(
                """
                INSERT INTO star_detail_base(star_id, star_type, fetched_at, data_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(star_id, star_type) DO UPDATE SET
                    fetched_at = excluded.fetched_at,
                    data_json = excluded.data_json
                """,
                (star_id, star_type, fetched_at, json_dumps(base_data)),
            )

        for work in detail.get("representative_works", {}).get("data", {}).get("detailList") or []:
            photo_id = str(work.get("photoId") or "")
            if not photo_id:
                continue
            conn.execute(
                """
                INSERT INTO star_work(
                    star_id, star_type, photo_id, fetched_at, caption, like_cnt, view_cnt,
                    forward_cnt, comment_cnt, release_time_millis, business, product_name,
                    first_industry_id, first_industry_name, data_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(star_id, star_type, photo_id) DO UPDATE SET
                    fetched_at = excluded.fetched_at,
                    caption = excluded.caption,
                    like_cnt = excluded.like_cnt,
                    view_cnt = excluded.view_cnt,
                    forward_cnt = excluded.forward_cnt,
                    comment_cnt = excluded.comment_cnt,
                    release_time_millis = excluded.release_time_millis,
                    business = excluded.business,
                    product_name = excluded.product_name,
                    first_industry_id = excluded.first_industry_id,
                    first_industry_name = excluded.first_industry_name,
                    data_json = excluded.data_json
                """,
                (
                    star_id,
                    star_type,
                    photo_id,
                    fetched_at,
                    work.get("caption"),
                    as_int(work.get("likeCnt")),
                    as_int(work.get("viewCnt")),
                    as_int(work.get("forwardCnt")),
                    as_int(work.get("commentCnt")),
                    as_int(work.get("releaseTimeMillis")),
                    1 if work.get("business") else 0 if work.get("business") is not None else None,
                    work.get("productName"),
                    as_int(work.get("firstIndustryId")),
                    work.get("firstIndustryName"),
                    json_dumps(work),
                ),
            )

        conn.execute("DELETE FROM star_portrait WHERE star_id = ? AND star_type = ?", (star_id, star_type))
        for row in flatten_portrait_rows(star_id, star_type, detail.get("portrait", {}).get("data") or {}):
            conn.execute(
                """
                INSERT INTO star_portrait(
                    star_id, star_type, fetched_at, portrait, group_name, item_index,
                    label, value, tgi, item_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    star_id,
                    star_type,
                    fetched_at,
                    row.get("_portrait"),
                    row.get("_group"),
                    as_int(row.get("_index")),
                    row.get("label"),
                    row.get("value"),
                    row.get("tgi"),
                    json_dumps({k: v for k, v in row.items() if not k.startswith("_")}),
                ),
            )
    conn.commit()


def detail_due_star_ids(
    conn: sqlite3.Connection,
    star_ids: list[str],
    star_type: int,
    refresh_days: int,
    limit: int | None,
) -> list[str]:
    if refresh_days < 0:
        selected = star_ids
    else:
        selected = []
        cutoff_seconds = refresh_days * 86400
        now_ts = time.time()
        for star_id in star_ids:
            row = conn.execute(
                "SELECT fetched_at FROM star_detail_base WHERE star_id = ? AND star_type = ?",
                (star_id, star_type),
            ).fetchone()
            if not row:
                selected.append(star_id)
                continue
            try:
                fetched_ts = datetime.fromisoformat(row["fetched_at"]).timestamp()
            except ValueError:
                selected.append(star_id)
                continue
            if now_ts - fetched_ts >= cutoff_seconds:
                selected.append(star_id)
    return selected[:limit] if limit else selected


def run_full_to_sqlite(
    session: requests.Session,
    headers: dict[str, str],
    account_id: str,
    db_path: Path,
    args: argparse.Namespace,
) -> tuple[Path, dict[str, int]]:
    conn = open_sqlite(db_path)
    init_sqlite(conn)
    params = {
        "hot_ranks": args.hot_ranks,
        "live_max_pages": args.max_pages,
        "page_size": args.page_size,
        "detail_limit": args.detail_limit,
        "detail_refresh_days": args.detail_refresh_days,
        "skip_details": args.skip_details,
    }
    run_id = start_run(conn, "full", account_id, params)
    counts = {
        "discovered": 0,
        "hot_rank_failures": 0,
        "detail_requested": 0,
        "detail_success": 0,
        "detail_failures": 0,
    }
    try:
        hot_home = fetch_hot_home(session, headers)
        store_hot_home_sqlite(conn, run_id, account_id, hot_home)

        hot_ranks = fetch_hot_ranks(
            session,
            headers,
            resolve_rank_keys(args.hot_ranks),
            user_id=args.user_id,
            continue_on_error=True,
        )
        counts["hot_rank_failures"] = len(hot_ranks.get("failures", []))
        store_hot_list_sqlite(conn, run_id, account_id, hot_ranks)

        live_payload = dict(DEFAULT_LIVE_LIST_PAYLOAD)
        live_payload.update({
            "starOrderTag": args.star_order_tag,
            "starOrderType": args.star_order_type,
            "taskType": args.task_type,
        })
        live_list = fetch_list_pages(session, headers, args.page_size, args.max_pages, base_payload=live_payload)
        store_list_sqlite(conn, run_id, account_id, live_list, "live-list", "live-list")

        discovered = [
            row["star_id"]
            for row in conn.execute(
                """
                SELECT DISTINCT star_id
                FROM fact_star_source
                WHERE run_id = ?
                ORDER BY star_id
                """,
                (run_id,),
            ).fetchall()
        ]
        counts["discovered"] = len(discovered)

        if not args.skip_details:
            due_ids = detail_due_star_ids(conn, discovered, args.star_type, args.detail_refresh_days, args.detail_limit)
            counts["detail_requested"] = len(due_ids)
            if due_ids:
                detail_result = fetch_details(
                    session,
                    headers,
                    due_ids,
                    args.star_type,
                    path_source=args.path_source,
                    penetration_json=args.penetration_json,
                    works_nature=None if args.works_nature == "omit" else args.works_nature == "true",
                )
                store_details_sqlite(conn, run_id, account_id, detail_result)
                counts["detail_success"] = len(detail_result.get("details", []))
                counts["detail_failures"] = len(detail_result.get("failures", []))

        finish_run(conn, run_id, "success")
        return db_path, counts
    except Exception:
        finish_run(conn, run_id, "failed")
        raise
    finally:
        conn.close()


DB_OBJECT_DESCRIPTIONS = [
    ("v_star_overview", "日常优先看：达人一行一条，带来源数、详情时间、作品数、画像组数"),
    ("v_star_source_latest", "日常优先看：达人最新来源、榜单、页码、排序模型"),
    ("v_run_summary", "日常优先看：每次采集任务的汇总"),
    ("v_star_work_latest", "日常优先看：代表作品明细，已带达人名称"),
    ("v_star_portrait_latest", "日常优先看：粉丝/观众画像长表，已带达人名称"),
    ("dim_star", "底层表：达人主表，按 star_id 去重"),
    ("fact_star_source", "底层表：达人来源事实，保留榜单/筛选模型/页码"),
    ("star_detail_base", "底层表：达人详情页基础资料原始 JSON"),
    ("star_work", "底层表：代表作品结构化字段和原始 JSON"),
    ("star_portrait", "底层表：粉丝画像和观众画像展开结果"),
    ("raw_api_response", "底层表：所有接口原始响应，补字段和排查问题用"),
    ("runs", "底层表：采集任务参数和状态"),
]


def sqlite_object_count(conn: sqlite3.Connection, name: str) -> int | None:
    try:
        row = conn.execute(f'SELECT COUNT(*) AS count FROM "{name}"').fetchone()
    except sqlite3.Error:
        return None
    return int(row["count"]) if row else None


def print_db_summary(db_path: Path) -> None:
    conn = open_sqlite(db_path)
    try:
        init_sqlite(conn)
        print(f"SQLite: {db_path}")
        print("")
        print("Recommended views")
        for name, description in DB_OBJECT_DESCRIPTIONS[:5]:
            count = sqlite_object_count(conn, name)
            print(f"  {name}: rows={count if count is not None else '?'} - {description}")
        print("")
        print("Base tables")
        for name, description in DB_OBJECT_DESCRIPTIONS[5:]:
            count = sqlite_object_count(conn, name)
            print(f"  {name}: rows={count if count is not None else '?'} - {description}")
        print("")
        print("Suggested starting queries")
        print("  SELECT * FROM v_star_overview ORDER BY last_seen_at DESC LIMIT 50;")
        print("  SELECT * FROM v_run_summary ORDER BY started_at DESC LIMIT 20;")
        print("  SELECT * FROM v_star_source_latest WHERE source_type = 'live-list' LIMIT 50;")
    finally:
        conn.close()


def estimate_full_requests(args: argparse.Namespace) -> int:
    hot_rank_count = len(resolve_rank_keys(args.hot_ranks))
    detail_requests = 0 if args.skip_details else (args.detail_limit or args.max_pages * args.page_size) * 3
    return 1 + hot_rank_count + args.max_pages + detail_requests


def read_menu_int(prompt: str, default: int, minimum: int = 0) -> int:
    raw = input(f"{prompt} [{default}]: ").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        print(f"Invalid number, using {default}")
        return default
    return max(minimum, value)


def read_menu_text(prompt: str, default: str) -> str:
    raw = input(f"{prompt} [{default}]: ").strip()
    return raw or default


def configure_interactive_args(args: argparse.Namespace) -> bool:
    presets = {
        "1": {
            "name": "smoke test",
            "description": "5 live pages, all hot ranks, 100 detail stars",
            "max_pages": 5,
            "detail_limit": 100,
            "skip_details": False,
            "hot_ranks": "all",
        },
        "2": {
            "name": "daily discovery",
            "description": "50 live pages, all hot ranks, no detail refresh",
            "max_pages": 50,
            "detail_limit": 0,
            "skip_details": True,
            "hot_ranks": "all",
        },
        "3": {
            "name": "daily detail batch",
            "description": "20 live pages, all hot ranks, 200 due detail stars",
            "max_pages": 20,
            "detail_limit": 200,
            "skip_details": False,
            "hot_ranks": "all",
        },
        "4": {
            "name": "large batch",
            "description": "100 live pages, all hot ranks, 500 due detail stars",
            "max_pages": 100,
            "detail_limit": 500,
            "skip_details": False,
            "hot_ranks": "all",
        },
        "5": {
            "name": "deep discovery only",
            "description": "250 live pages, all hot ranks, no detail refresh",
            "max_pages": 250,
            "detail_limit": 0,
            "skip_details": True,
            "hot_ranks": "all",
        },
    }

    print("Magnetic Juxing scrape menu")
    for key, preset in presets.items():
        print(f"  {key}. {preset['name']} - {preset['description']}")
    print("  6. custom")
    print("  q. quit")

    choice = input("Choose a run mode [1]: ").strip().lower() or "1"
    if choice in {"q", "quit", "exit"}:
        return False

    if choice == "6":
        args.hot_ranks = read_menu_text("Hot ranks (develop,cost_performance,live_sales,spread,live_popularity,fans,all)", args.hot_ranks)
        args.max_pages = read_menu_int("Live list pages", args.max_pages, minimum=1)
        skip_raw = input("Skip detail refresh? [y/N]: ").strip().lower()
        args.skip_details = skip_raw in {"y", "yes"}
        if args.skip_details:
            args.detail_limit = 0
        else:
            args.detail_limit = read_menu_int("Detail stars limit, 0 means all due stars", args.detail_limit, minimum=0)
            args.detail_refresh_days = read_menu_int("Detail refresh days, -1 forces refresh", args.detail_refresh_days, minimum=-1)
    elif choice in presets:
        preset = presets[choice]
        args.hot_ranks = preset["hot_ranks"]
        args.max_pages = preset["max_pages"]
        args.detail_limit = preset["detail_limit"]
        args.skip_details = preset["skip_details"]
    else:
        print("Unknown choice.")
        return False

    args.action = "full"
    try:
        estimated_requests = estimate_full_requests(args)
    except MagneticJuxingError as e:
        print(f"Invalid menu configuration: {e}")
        return False

    detail_text = "skip" if args.skip_details else str(args.detail_limit or "all due")
    print("")
    print("Run summary")
    print(f"  db_path: {args.db_path}")
    print(f"  hot_ranks: {args.hot_ranks}")
    print(f"  live_pages: {args.max_pages}")
    print(f"  detail_limit: {detail_text}")
    print(f"  detail_refresh_days: {args.detail_refresh_days}")
    print(f"  estimated_requests: about {estimated_requests}")
    confirm = input("Start this run? [Y/n]: ").strip().lower()
    return confirm not in {"n", "no"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Magnetic Juxing star list API scraper")
    parser.add_argument(
        "--action",
        choices=["probe", "list", "live-list", "hot-home", "hot-list", "detail", "full", "interactive", "db-summary"],
        default="probe",
    )
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--db-path", default=str(DEFAULT_DB_FILE), help="SQLite path for --action full")
    parser.add_argument(
        "--detail-limit",
        type=int,
        default=50,
        help="Max discovered stars to refresh in --action full; use 0 for all due stars",
    )
    parser.add_argument(
        "--detail-refresh-days",
        type=int,
        default=7,
        help="Skip detail refresh when a star was fetched within this many days; use -1 to force",
    )
    parser.add_argument("--skip-details", action="store_true", help="Only collect list/rank sources in --action full")
    parser.add_argument("--cookie-file", default=None, help="Local text file containing one Cookie header value")
    parser.add_argument("--account-id", default=None, help="ACCOUNT-ID header value; defaults to config magnetic_juxing.account_id")
    parser.add_argument("--user-id", default=None, help="Optional userId included in hot-list payload")
    parser.add_argument(
        "--hot-ranks",
        default="develop,cost_performance,live_sales",
        help=f"Comma-separated rank keys or all. Available: {', '.join(DEFAULT_HOT_RANKS)}",
    )
    parser.add_argument("--star-id", default=None, help="Single starId for --action detail")
    parser.add_argument("--star-ids", default=None, help="Comma-separated starId list for --action detail")
    parser.add_argument("--star-type", type=int, default=1, help="Detail starType; observed video=1")
    parser.add_argument("--path-source", default=None, help="Optional detail pathSource, e.g. no_filter_video")
    parser.add_argument("--penetration-json", default=None, help="Optional detail penetrationJSON string")
    parser.add_argument(
        "--works-nature",
        choices=["true", "false", "omit"],
        default="false",
        help="Representative works nature flag; observed browser payload uses false",
    )
    parser.add_argument("--star-order-tag", type=int, default=2, help="Live list sort tag; observed default=2")
    parser.add_argument("--star-order-type", type=int, default=2, help="Live list sort direction/type; observed default=2")
    parser.add_argument("--task-type", type=int, default=4, help="Star list task type; observed live=4")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.action == "db-summary":
        print_db_summary(Path(args.db_path))
        return 0

    if args.action == "interactive" and not configure_interactive_args(args):
        print("Run cancelled.")
        return 0

    account_id = load_account_id(args)
    headers = load_headers(args.cookie_file, account_id=account_id)
    session = requests.Session()

    if args.action == "full":
        if args.detail_limit <= 0:
            args.detail_limit = None
        try:
            db_path, counts = run_full_to_sqlite(session, headers, account_id, Path(args.db_path), args)
        except MagneticJuxingError as e:
            print(f"Scrape failed: {e}")
            return 1
        print(f"SQLite saved: {db_path}")
        print(
            "Full scrape summary: "
            f"discovered={counts['discovered']}, "
            f"hot_rank_failures={counts['hot_rank_failures']}, "
            f"detail_requested={counts['detail_requested']}, "
            f"detail_success={counts['detail_success']}, "
            f"detail_failures={counts['detail_failures']}"
        )
        return 0

    if args.action == "probe":
        result = probe(session, headers)
        output = save_json_result(result, "magnetic_juxing_probe")
        print(f"Probe saved: {output}")
        for item in result["results"]:
            print(
                f"{item['case']}: ok={item['ok']} "
                f"items={item.get('item_count', 0)} total={item.get('total')} "
                f"keys={item.get('item_keys', [])[:20]} error={item.get('error', '')}"
            )
        return 0

    if args.action == "hot-home":
        result = fetch_hot_home(session, headers)
        json_output = save_json_result(result, "magnetic_juxing_hot_home")
        csv_output = save_items_csv(result["items"], "magnetic_juxing_hot_home_items")
        print(f"Hot home saved: {json_output}")
        print(f"Items CSV saved: {csv_output}")
        print(f"Hot home summary: groups={len((result['raw'].get('data') or []))} items={len(result['items'])}")
        return 0

    if args.action == "hot-list":
        try:
            rank_keys = resolve_rank_keys(args.hot_ranks)
            result = fetch_hot_ranks(session, headers, rank_keys, user_id=args.user_id)
        except MagneticJuxingError as e:
            print(f"Scrape failed: {e}")
            return 1
        json_output = save_json_result(result, "magnetic_juxing_hot_list")
        csv_output = save_items_csv(result["items"], "magnetic_juxing_hot_list_items")
        print(f"Hot list saved: {json_output}")
        print(f"Items CSV saved: {csv_output}")
        for rank in result["ranks"]:
            print(
                f"{rank['rank_key']}: total={rank.get('total')} "
                f"items={len(rank['items'])} description={rank.get('description', '')[:40]}"
            )
        return 0

    if args.action == "detail":
        star_ids = []
        if args.star_id:
            star_ids.append(str(args.star_id).strip())
        if args.star_ids:
            star_ids.extend(item.strip() for item in args.star_ids.split(",") if item.strip())
        star_ids = list(dict.fromkeys(star_ids))
        if not star_ids:
            print("Scrape failed: --action detail requires --star-id or --star-ids")
            return 1

        result = fetch_details(
            session,
            headers,
            star_ids,
            args.star_type,
            path_source=args.path_source,
            penetration_json=args.penetration_json,
            works_nature=None if args.works_nature == "omit" else args.works_nature == "true",
        )
        json_output = save_json_result(result, "magnetic_juxing_detail")
        base_csv_output = save_items_csv(result["base_rows"], "magnetic_juxing_detail_base")
        works_csv_output = save_items_csv(result["work_rows"], "magnetic_juxing_detail_works")
        portrait_csv_output = save_items_csv(result["portrait_rows"], "magnetic_juxing_detail_portrait")
        print(f"Detail saved: {json_output}")
        print(f"Base CSV saved: {base_csv_output}")
        print(f"Works CSV saved: {works_csv_output}")
        print(f"Portrait CSV saved: {portrait_csv_output}")
        print(
            "Detail summary: "
            f"stars={len(result['details'])}, "
            f"base_rows={len(result['base_rows'])}, "
            f"work_rows={len(result['work_rows'])}, "
            f"portrait_rows={len(result['portrait_rows'])}, "
            f"failures={len(result['failures'])}"
        )
        return 0

    if args.action == "live-list":
        live_payload = dict(DEFAULT_LIVE_LIST_PAYLOAD)
        live_payload.update({
            "starOrderTag": args.star_order_tag,
            "starOrderType": args.star_order_type,
            "taskType": args.task_type,
        })
        result = fetch_list_pages(session, headers, args.page_size, args.max_pages, base_payload=live_payload)
        json_output = save_json_result(result, "magnetic_juxing_live_list")
        csv_output = save_items_csv(result["items"], "magnetic_juxing_live_list_items")
        print(f"Live list saved: {json_output}")
        print(f"Items CSV saved: {csv_output}")
        print(f"Live list summary: total={result.get('total')} items={len(result['items'])}")
        return 0

    result = fetch_list_pages(session, headers, args.page_size, args.max_pages)
    json_output = save_json_result(result, "magnetic_juxing_list")
    csv_output = save_items_csv(result["items"], "magnetic_juxing_list_items")
    print(f"Raw list saved: {json_output}")
    print(f"Items CSV saved: {csv_output}")
    print(f"List summary: total={result.get('total')} items={len(result['items'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
