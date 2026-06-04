"""Feigua Kuaishou blogger API scraper.

Usage:
  1. Add ks_feigua_cookies to config.yaml.
  2. Add ks_feigua.timestamp/signature to config.yaml, or pass them with
     --timestamp / --signature.
  3. Run:
     .venv/Scripts/python.exe scripts/ks_feigua_scraper.py --blogger-id 74865
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from tqdm import tqdm

try:
    import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    from scripts import _bootstrap  # noqa: F401

from saas_crawler.core.checkpoint import load_json, save_json_atomic
from saas_crawler.core.config import build_browser_headers, load_yaml_config, require_cookie_list
from saas_crawler.core.paths import CHECKPOINT_DIR, CONFIG_FILE, DATA_DIR, ensure_runtime_dirs


BASE_URL = "https://ks.feigua.cn"
REQUEST_DELAY = 1.0
FULL_CHECKPOINT = CHECKPOINT_DIR / "ks_feigua_full.json"
DETAIL_PARAMS_VERSION = 1
SEARCH_PARAMS_VERSION = 1
DEFAULT_SEARCH_SORT = 5


class FeiguaKuaishouError(Exception):
    """Feigua Kuaishou API error."""


def now_ms() -> int:
    return int(time.time() * 1000)


def default_year_begin(today: date | None = None) -> str:
    today = today or date.today()
    return date(today.year, 1, 1).strftime("%Y/%m/%d")


def default_end_date(today: date | None = None) -> str:
    today = today or date.today()
    return (today - timedelta(days=1)).isoformat()


def default_trend_begin(today: date | None = None) -> str:
    today = today or date.today()
    return date(today.year, 1, 1).isoformat()


def load_headers() -> dict[str, str]:
    try:
        cfg = load_yaml_config(CONFIG_FILE)
        cookie = os.getenv("KS_FEIGUA_COOKIE") or require_cookie_list(cfg, "ks_feigua_cookies")[0]
    except (FileNotFoundError, ValueError) as e:
        print(f"Missing ks_feigua_cookies in {CONFIG_FILE}")
        print(e)
        raise SystemExit(1) from e

    headers = build_browser_headers(cookie, f"{BASE_URL}/")
    headers.update({
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
    })
    return headers


def load_auth_args(args: argparse.Namespace) -> tuple[str | None, str | None]:
    cfg = load_yaml_config(CONFIG_FILE)
    section = cfg.get("ks_feigua", {}) or {}
    timestamp = args.timestamp or os.getenv("KS_FEIGUA_TIMESTAMP") or section.get("timestamp")
    signature = args.signature or os.getenv("KS_FEIGUA_SIGNATURE") or section.get("signature")
    return str(timestamp).strip() if timestamp else None, str(signature).strip() if signature else None


def decode_response(response: requests.Response, path: str) -> dict[str, Any]:
    response.raise_for_status()
    try:
        body = response.json()
    except json.JSONDecodeError as e:
        raise FeiguaKuaishouError(f"{path} returned non-JSON: {response.text[:200]}") from e

    code = body.get("Code", body.get("code"))
    if code not in (None, 0, 200):
        message = body.get("Msg") or body.get("msg") or body.get("Message") or body.get("message")
        raise FeiguaKuaishouError(f"{path} API error code={code} msg={message}")

    return body


def api_get(
    session: requests.Session,
    headers: dict[str, str],
    path: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request_params = dict(params or {})
    request_params.setdefault("_", now_ms())
    response = session.get(f"{BASE_URL}{path}", params=request_params, headers=headers, timeout=30)
    return decode_response(response, path)


def api_post(
    session: requests.Session,
    headers: dict[str, str],
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params = {"_": now_ms()}
    response = session.post(f"{BASE_URL}{path}", params=params, json=payload or {}, headers=headers, timeout=30)
    return decode_response(response, path)


def get_data(body: dict[str, Any]) -> Any:
    return body.get("Data", body.get("data"))


def extract_jump_auth(item: dict[str, Any]) -> dict[str, str]:
    jump_url = str(item.get("BloggerJumpUrl") or "")
    blogger_id = str(item.get("BloggerId") or "")

    def find_param(name: str) -> str:
        match = re.search(rf"(?:[?&#]|^){name}=([^&#]+)", jump_url)
        return match.group(1) if match else ""

    return {
        "blogger_id": find_param("id") or blogger_id,
        "timestamp": find_param("timestamp"),
        "signature": find_param("signature"),
    }


def search_bloggers(
    session: requests.Session,
    headers: dict[str, str],
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
    sort: int = DEFAULT_SEARCH_SORT,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "keyword": keyword,
        "pageIndex": page,
        "pageSize": page_size,
        "sort": sort,
    }
    return api_post(session, headers, "/api/v1/blogger/search", payload)


def normalize_search_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for item in items:
        auth = extract_jump_auth(item)
        normalized.append({
            **item,
            "_detail_auth": auth,
        })
    return normalized


def signed_params(
    blogger_id: int | str,
    timestamp: str | None,
    signature: str | None,
    period: str,
    begin_date: str,
    end_date: str,
) -> dict[str, Any]:
    if not timestamp or not signature:
        raise FeiguaKuaishouError("Missing timestamp/signature for detail APIs")

    return {
        "period": period,
        "beginDate": begin_date,
        "endDate": end_date,
        "bloggerId": blogger_id,
        "timestamp": timestamp,
        "signature": signature,
    }


def blogger_total(
    session: requests.Session,
    headers: dict[str, str],
    total_type: int,
    blogger_id: int | str,
    timestamp: str | None,
    signature: str | None,
    period: str,
    begin_date: str,
    end_date: str,
) -> dict[str, Any]:
    params = signed_params(blogger_id, timestamp, signature, period, begin_date, end_date)
    return api_get(session, headers, f"/api/v1/blogger/BloggerOverview_Total_{total_type}", params)


def blogger_overview(
    session: requests.Session,
    headers: dict[str, str],
    blogger_id: int | str,
    timestamp: str | None,
    signature: str | None,
) -> dict[str, Any]:
    if not timestamp or not signature:
        raise FeiguaKuaishouError("Missing timestamp/signature for overview API")

    params = {
        "bloggerId": blogger_id,
        "timestamp": timestamp,
        "signature": signature,
    }
    return api_get(session, headers, "/api/v1/blogger/BloggerOverview", params)


def metric_list_to_dict(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {str(item.get("Text", "")).strip(): item.get("Value") for item in items if item.get("Text")}


def parse_search(body: dict[str, Any]) -> dict[str, Any]:
    data = get_data(body) or {}
    return {
        "surplus_count": data.get("SurplusCount"),
        "search_export_count": data.get("SearchExportCount"),
        "total_count": data.get("TotalCount"),
        "permission_count": data.get("PermissionCount"),
        "fake_page": data.get("FakePage"),
        "items": data.get("ItemList", []),
    }


def parse_detail_bundle(raw_detail: dict[str, Any]) -> dict[str, Any]:
    apis = raw_detail.get("apis", {})
    video_data = get_data(apis.get("video_total", {})) or {}
    live_data = get_data(apis.get("live_total", {})) or {}
    commerce_data = get_data(apis.get("commerce_total", {})) or {}
    fans_data = get_data(apis.get("fans_trend", {})) or {}
    overview_data = get_data(apis.get("overview", {})) or {}

    return {
        "blogger_id": raw_detail.get("blogger_id"),
        "metrics": {
            "video": metric_list_to_dict(video_data.get("VideoData", [])),
            "live": metric_list_to_dict(live_data.get("LiveData", [])),
        },
        "commerce": {
            "categories": commerce_data.get("LiveShopData_Cate", []),
            "brands": commerce_data.get("LiveShopData_Brand", []),
        },
        "fans_trend": {
            "fans": fans_data.get("Fans"),
            "total_fans": fans_data.get("LstFansData", []),
            "increment_fans": fans_data.get("LstIncFansData", []),
            "total_video": fans_data.get("LstVideoData", []),
            "increment_video": fans_data.get("LstIncVideoData", []),
        },
        "overview": {
            "live_metrics": metric_list_to_dict(overview_data.get("Top10Lives", [])),
            "live_rank": overview_data.get("Top10LiveDatas", []),
            "live_metrics_2": metric_list_to_dict(overview_data.get("Top10Lives2", [])),
            "live_rank_2": overview_data.get("Top10LiveDatas2", []),
            "video_metrics": metric_list_to_dict(overview_data.get("Top10Video", [])),
            "video_rank": overview_data.get("Top10VideoDatas", []),
            "live_segments": overview_data.get("LiveSegments", []),
            "video_segments": overview_data.get("VideoSegments", []),
        },
    }


def save_json_result(result: dict[str, Any], prefix: str) -> Path:
    ensure_runtime_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = DATA_DIR / f"{prefix}_{timestamp}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return path


def load_full_checkpoint() -> dict[str, Any]:
    ckpt = load_json(FULL_CHECKPOINT)
    ckpt.setdefault("search_pages", {})
    ckpt.setdefault("search_runs", {})
    ckpt.setdefault("bloggers", {})
    ckpt.setdefault("detail_raw", {})
    ckpt.setdefault("detail_parsed", {})
    ckpt.setdefault("detail_failures", {})
    ckpt.setdefault("completed_pages", [])
    return ckpt


def save_full_checkpoint(ckpt: dict[str, Any]) -> None:
    ckpt["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_json_atomic(FULL_CHECKPOINT, ckpt)


def effective_search_total(total_count: Any, permission_count: Any) -> int | None:
    totals = []
    for value in (total_count, permission_count):
        try:
            if value is not None:
                totals.append(int(value))
        except (TypeError, ValueError):
            pass
    return min(totals) if totals else None


def repair_bad_search_checkpoint(ckpt: dict[str, Any], page_size: int) -> None:
    completed_pages = ckpt.get("completed_pages", [])
    blogger_count = len(ckpt.get("bloggers", {}))
    if len(completed_pages) > 1 and blogger_count <= page_size:
        ckpt["search_pages"] = {}
        ckpt["bloggers"] = {}
        ckpt["completed_pages"] = []
        ckpt["search_checkpoint_repaired_at"] = datetime.now().isoformat(timespec="seconds")
        save_full_checkpoint(ckpt)


def reset_details_if_params_changed(ckpt: dict[str, Any], detail_params: dict[str, str]) -> None:
    params_changed = ckpt.get("detail_params") and ckpt.get("detail_params") != detail_params
    params_unknown = ckpt.get("detail_parsed") and not ckpt.get("detail_params_version")
    if params_changed or params_unknown:
        ckpt["detail_raw"] = {}
        ckpt["detail_parsed"] = {}
        ckpt["detail_failures"] = {}
        ckpt["detail_params_reset_at"] = datetime.now().isoformat(timespec="seconds")
    ckpt["detail_params"] = detail_params
    ckpt["detail_params_version"] = DETAIL_PARAMS_VERSION
    save_full_checkpoint(ckpt)


def search_key(keyword: str, page_size: int, sort: int) -> str:
    safe_keyword = keyword.replace("|", "%7C")
    return f"keyword={safe_keyword}|page_size={page_size}|sort={sort}"


def get_search_run(ckpt: dict[str, Any], keyword: str, page_size: int, sort: int) -> tuple[str, dict[str, Any]]:
    key = search_key(keyword, page_size, sort)
    run = ckpt.setdefault("search_runs", {}).setdefault(key, {
        "params": {
            "keyword": keyword,
            "page_size": page_size,
            "sort": sort,
        },
        "pages": {},
        "completed_pages": [],
    })
    run.setdefault("pages", {})
    run.setdefault("completed_pages", [])
    return key, run


def merge_blogger_item(
    ckpt: dict[str, Any],
    item: dict[str, Any],
    keyword: str,
    page_size: int,
    sort: int,
    page: int,
    rank_in_page: int,
) -> None:
    blogger_id = str(item.get("_detail_auth", {}).get("blogger_id") or item.get("BloggerId") or "")
    if not blogger_id:
        return

    source = {
        "keyword": keyword,
        "page_size": page_size,
        "sort": sort,
        "page": page,
        "rank_in_page": rank_in_page,
    }
    existing = ckpt["bloggers"].get(blogger_id, {})
    sources = existing.get("_search_sources", [])
    if source not in sources:
        sources.append(source)

    merged = {**existing, **item}
    merged["_search_sources"] = sources
    ckpt["bloggers"][blogger_id] = merged


def ordered_blogger_ids(ckpt: dict[str, Any]) -> list[str]:
    ordered = []
    seen = set()
    for run in ckpt.get("search_runs", {}).values():
        pages = run.get("pages", {})
        for page in sorted(pages.keys(), key=lambda x: int(x) if str(x).isdigit() else str(x)):
            for item in pages.get(str(page), []):
                blogger_id = str(item.get("_detail_auth", {}).get("blogger_id") or item.get("BloggerId") or "")
                if blogger_id and blogger_id not in seen:
                    ordered.append(blogger_id)
                    seen.add(blogger_id)

    pages = ckpt.get("search_pages", {})
    for page in sorted(pages.keys(), key=lambda x: int(x) if str(x).isdigit() else str(x)):
        for item in pages.get(str(page), []):
            blogger_id = str(item.get("_detail_auth", {}).get("blogger_id") or item.get("BloggerId") or "")
            if blogger_id and blogger_id not in seen:
                ordered.append(blogger_id)
                seen.add(blogger_id)

    for blogger_id in ckpt.get("bloggers", {}):
        if blogger_id not in seen:
            ordered.append(blogger_id)
            seen.add(blogger_id)
    return ordered


def fetch_all_search_pages(
    session: requests.Session,
    headers: dict[str, str],
    keyword: str,
    page_size: int,
    sort: int,
    max_pages: int | None = None,
) -> dict[str, Any]:
    ckpt = load_full_checkpoint()
    if not ckpt.get("search_runs"):
        repair_bad_search_checkpoint(ckpt, page_size)
    run_key, run = get_search_run(ckpt, keyword, page_size, sort)
    completed_pages = {int(page) for page in run.get("completed_pages", [])}
    total_count = run.get("total_count")
    permission_count = run.get("permission_count")
    effective_total = effective_search_total(total_count, permission_count)
    total_pages = math.ceil(effective_total / page_size) if effective_total is not None else None
    if max_pages and total_pages is not None:
        total_pages = min(total_pages, max_pages)
    elif max_pages:
        total_pages = max_pages

    initial_pages = len([page for page in completed_pages if not total_pages or page <= total_pages])

    page = 1
    with tqdm(
        total=total_pages,
        initial=initial_pages,
        desc="Search pages",
        unit="page",
        dynamic_ncols=True,
        file=sys.stdout,
        leave=False,
    ) as progress:
        while True:
            if max_pages and page > max_pages:
                break
            effective_total = effective_search_total(total_count, permission_count)
            if effective_total is not None and (page - 1) * page_size >= effective_total:
                break

            if page in completed_pages:
                page += 1
                continue

            body = search_bloggers(session, headers, keyword, page, page_size, sort)
            parsed = parse_search(body)
            items = normalize_search_items(parsed["items"])

            total_count = parsed["total_count"] or total_count
            permission_count = parsed["permission_count"] or permission_count
            effective_total = effective_search_total(total_count, permission_count)
            new_total_pages = math.ceil(effective_total / page_size) if effective_total is not None else None
            if max_pages and new_total_pages is not None:
                new_total_pages = min(new_total_pages, max_pages)
            if new_total_pages and progress.total != new_total_pages:
                progress.total = new_total_pages
                progress.refresh()

            ckpt["total_count"] = total_count
            ckpt["permission_count"] = permission_count
            ckpt["surplus_count"] = parsed["surplus_count"]
            ckpt["search_export_count"] = parsed["search_export_count"]
            ckpt["fake_page"] = parsed["fake_page"]
            ckpt["search_params"] = {
                "keyword": keyword,
                "page_size": page_size,
                "sort": sort,
            }
            ckpt["search_params_version"] = SEARCH_PARAMS_VERSION
            run["total_count"] = total_count
            run["permission_count"] = permission_count
            run["surplus_count"] = parsed["surplus_count"]
            run["search_export_count"] = parsed["search_export_count"]
            run["fake_page"] = parsed["fake_page"]
            run["pages"][str(page)] = items

            for rank_in_page, item in enumerate(items, 1):
                merge_blogger_item(ckpt, item, keyword, page_size, sort, page, rank_in_page)

            completed_pages.add(page)
            run["completed_pages"] = sorted(completed_pages)
            ckpt["completed_pages"] = sorted(set(ckpt.get("completed_pages", [])) | completed_pages)
            ckpt["search_runs"][run_key] = run
            save_full_checkpoint(ckpt)

            progress.set_postfix({
                "page": page,
                "new": len(items),
                "bloggers": len(ckpt["bloggers"]),
                "permission": permission_count,
            })
            progress.update(1)
            if not items or len(items) < page_size:
                break

            page += 1
            time.sleep(REQUEST_DELAY)

    return ckpt


def fetch_all_details(
    session: requests.Session,
    headers: dict[str, str],
    ckpt: dict[str, Any],
    year_begin: str,
    year_end: str,
    trend_begin: str,
    trend_end: str,
    max_bloggers: int | None = None,
) -> dict[str, Any]:
    detail_params = {
        "year_begin": year_begin,
        "year_end": year_end,
        "trend_begin": trend_begin,
        "trend_end": trend_end,
    }
    reset_details_if_params_changed(ckpt, detail_params)

    bloggers = ckpt.get("bloggers", {})
    done = set(ckpt.get("detail_parsed", {}).keys())
    failures = ckpt.get("detail_failures", {})
    todo = [bid for bid in ordered_blogger_ids(ckpt) if bid in bloggers and bid not in done]

    if max_bloggers:
        todo = todo[:max_bloggers]

    with tqdm(
        total=len(todo),
        desc="Details",
        unit="blogger",
        dynamic_ncols=True,
        file=sys.stdout,
        leave=False,
    ) as progress:
        for blogger_id in todo:
            item = bloggers[blogger_id]
            auth = item.get("_detail_auth") or extract_jump_auth(item)
            timestamp = auth.get("timestamp")
            signature = auth.get("signature")
            detail_id = auth.get("blogger_id") or blogger_id
            status = "ok"

            if not timestamp or not signature:
                failures[blogger_id] = {
                    "error": "missing timestamp/signature in BloggerJumpUrl",
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
                ckpt["detail_failures"] = failures
                save_full_checkpoint(ckpt)
                status = "missing_auth"
                progress.set_postfix({
                    "id": blogger_id,
                    "status": status,
                    "ok": len(ckpt.get("detail_parsed", {})),
                    "failed": len(failures),
                })
                progress.update(1)
                continue

            try:
                raw_detail = fetch_detail_bundle(
                    session,
                    headers,
                    detail_id,
                    timestamp,
                    signature,
                    year_begin,
                    year_end,
                    trend_begin,
                    trend_end,
                )
                raw_detail["search_item"] = item
                parsed_detail = parse_detail_bundle(raw_detail)
                parsed_detail["search_item"] = item

                ckpt["detail_raw"][blogger_id] = raw_detail
                ckpt["detail_parsed"][blogger_id] = parsed_detail
                failures.pop(blogger_id, None)
                ckpt["detail_failures"] = failures
                save_full_checkpoint(ckpt)
            except (requests.RequestException, FeiguaKuaishouError) as e:
                status = "failed"
                failures[blogger_id] = {
                    "error": str(e),
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
                ckpt["detail_failures"] = failures
                save_full_checkpoint(ckpt)

            progress.set_postfix({
                "id": blogger_id,
                "status": status,
                "ok": len(ckpt.get("detail_parsed", {})),
                "failed": len(failures),
            })
            progress.update(1)
            time.sleep(REQUEST_DELAY)

    return ckpt


def build_full_outputs(ckpt: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    fetched_at = datetime.now().isoformat(timespec="seconds")
    raw = {
        "platform": "ks_feigua",
        "action": "full",
        "fetched_at": fetched_at,
        "total_count": ckpt.get("total_count"),
        "permission_count": ckpt.get("permission_count"),
        "search_pages": ckpt.get("search_pages", {}),
        "search_runs": ckpt.get("search_runs", {}),
        "details": ckpt.get("detail_raw", {}),
        "failures": ckpt.get("detail_failures", {}),
    }
    parsed = {
        "platform": "ks_feigua",
        "action": "full",
        "fetched_at": fetched_at,
        "total_count": ckpt.get("total_count"),
        "permission_count": ckpt.get("permission_count"),
        "bloggers": list(ckpt.get("bloggers", {}).values()),
        "details": list(ckpt.get("detail_parsed", {}).values()),
        "failures": ckpt.get("detail_failures", {}),
    }
    return raw, parsed


def csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def write_csv(path: Path, rows: list[dict[str, Any]], headers: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if headers is None:
        headers = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    headers.append(key)
                    seen.add(key)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key, "")) for key in headers})


def metric_columns(prefix: str, metrics: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for name, value in metrics.items():
        if isinstance(value, list):
            labels = ["当前", "对比", "变化率"]
            for index, item in enumerate(value):
                suffix = labels[index] if index < len(labels) else str(index + 1)
                row[f"{prefix}_{name}_{suffix}"] = item
        else:
            row[f"{prefix}_{name}"] = value
    return row


def data_count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if value in (None, "", {}, []):
        return 0
    return 1


def raw_api_rows(base: dict[str, Any], raw_detail: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for api_name, body in raw_detail.get("apis", {}).items():
        data = body.get("Data") or {}
        if not isinstance(data, dict):
            rows.append({**base, "api": api_name, "data_key": "Data", "item_index": "", "value": data})
            continue

        for data_key, value in data.items():
            if isinstance(value, list):
                for index, item in enumerate(value):
                    row = {**base, "api": api_name, "data_key": data_key, "item_index": index}
                    if isinstance(item, dict):
                        row.update(item)
                    else:
                        row["value"] = item
                    rows.append(row)
            else:
                rows.append({**base, "api": api_name, "data_key": data_key, "item_index": "", "value": value})
    return rows


def api_status_rows(base: dict[str, Any], raw_detail: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for api_name, body in raw_detail.get("apis", {}).items():
        data = body.get("Data") or {}
        row = {
            **base,
            "api": api_name,
            "Code": body.get("Code"),
            "Msg": body.get("Msg"),
            "Status": body.get("Status"),
            "IsExample": body.get("IsExample"),
        }
        if isinstance(data, dict):
            for key, value in data.items():
                row[f"{key}_count"] = data_count(value)
        rows.append(row)
    return rows


def export_full_csv(ckpt: dict[str, Any]) -> Path:
    ensure_runtime_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = DATA_DIR / f"ks_feigua_csv_{timestamp}"
    bloggers = ckpt.get("bloggers", {})
    details = ckpt.get("detail_parsed", {})
    raw_details = ckpt.get("detail_raw", {})

    blogger_rows = [{k: v for k, v in item.items()} for item in bloggers.values()]
    summary_rows: list[dict[str, Any]] = []
    commerce_rows: list[dict[str, Any]] = []
    trend_rows: list[dict[str, Any]] = []
    overview_metric_rows: list[dict[str, Any]] = []
    live_rows: list[dict[str, Any]] = []
    video_rows: list[dict[str, Any]] = []
    segment_rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []

    for blogger_id, detail in details.items():
        search_item = detail.get("search_item", {})
        base = {
            "blogger_id": blogger_id,
            "Nick": search_item.get("Nick", ""),
            "KwaiId": search_item.get("KwaiId", ""),
            "SearchFans": search_item.get("Fans", ""),
            "BloggerJumpUrl": search_item.get("BloggerJumpUrl", ""),
        }

        summary = dict(base)
        summary.update(metric_columns("视频", detail.get("metrics", {}).get("video", {})))
        summary.update(metric_columns("直播", detail.get("metrics", {}).get("live", {})))

        commerce = detail.get("commerce", {})
        fans_trend = detail.get("fans_trend", {})
        overview = detail.get("overview", {})
        summary.update({
            "趋势_Fans": fans_trend.get("fans", ""),
            "带货品类_count": len(commerce.get("categories", [])),
            "带货品牌_count": len(commerce.get("brands", [])),
            "趋势_total_fans_count": len(fans_trend.get("total_fans", [])),
            "趋势_increment_fans_count": len(fans_trend.get("increment_fans", [])),
            "趋势_total_video_count": len(fans_trend.get("total_video", [])),
            "趋势_increment_video_count": len(fans_trend.get("increment_video", [])),
            "近10直播_count": len(overview.get("live_rank", [])),
            "近10直播2_count": len(overview.get("live_rank_2", [])),
            "近10视频_count": len(overview.get("video_rank", [])),
            "直播词段_count": len(overview.get("live_segments", [])),
            "视频词段_count": len(overview.get("video_segments", [])),
        })
        summary_rows.append(summary)

        for group, rows in (("category", commerce.get("categories", [])), ("brand", commerce.get("brands", []))):
            for row in rows:
                commerce_rows.append({**base, "type": group, **row})

        for series_name in ("total_fans", "increment_fans", "total_video", "increment_video"):
            for row in fans_trend.get(series_name, []):
                trend_rows.append({**base, "series": series_name, **row})

        for group in ("live_metrics", "live_metrics_2", "video_metrics"):
            for name, value in overview.get(group, {}).items():
                overview_metric_rows.append({**base, "group": group, "metric": name, "value": value})

        for group in ("live_rank", "live_rank_2"):
            for row in overview.get(group, []):
                live_rows.append({**base, "group": group, **row})

        for row in overview.get("video_rank", []):
            video_rows.append({**base, **row})

        for group in ("live_segments", "video_segments"):
            for row in overview.get(group, []):
                segment_rows.append({**base, "group": group, **row})

        raw_detail = raw_details.get(blogger_id, {})
        status_rows.extend(api_status_rows(base, raw_detail))
        raw_rows.extend(raw_api_rows(base, raw_detail))

    write_csv(output_dir / "bloggers.csv", blogger_rows)
    write_csv(output_dir / "detail_summary.csv", summary_rows)
    write_csv(output_dir / "commerce.csv", commerce_rows, ["blogger_id", "Nick", "KwaiId", "SearchFans", "BloggerJumpUrl", "type", "Name", "Samples", "Ratio"])
    write_csv(output_dir / "fans_trend.csv", trend_rows, ["blogger_id", "Nick", "KwaiId", "SearchFans", "BloggerJumpUrl", "series", "Date", "ShortTime", "Fans", "TotalComments", "Likes", "TotalViews", "FansStr", "TotalCommentsStr", "LikesStr", "TotalViewsStr"])
    write_csv(output_dir / "overview_metrics.csv", overview_metric_rows, ["blogger_id", "Nick", "KwaiId", "SearchFans", "BloggerJumpUrl", "group", "metric", "value"])
    write_csv(output_dir / "overview_lives.csv", live_rows, ["blogger_id", "Nick", "KwaiId", "SearchFans", "BloggerJumpUrl", "group", "Date", "ShortTime", "DisplayWatchCount", "DisplayWatchCountStr", "TotalVolume", "TotalVolumeStr", "TotalPrice", "TotalPriceStr", "Title", "CoverImage", "LiveDetailUrl"])
    write_csv(output_dir / "overview_videos.csv", video_rows, ["blogger_id", "Nick", "KwaiId", "SearchFans", "BloggerJumpUrl", "Date", "ShortTime", "LikeCount", "CommentCount", "ViewCount", "LikeCountStr", "CommentCountStr", "ViewCountStr", "Title", "CoverImage", "PhotoId", "BloggerId"])
    write_csv(output_dir / "segments.csv", segment_rows, ["blogger_id", "Nick", "KwaiId", "SearchFans", "BloggerJumpUrl", "group", "Segment", "Count", "CountStr"])
    write_csv(output_dir / "api_status.csv", status_rows)
    write_csv(output_dir / "raw_api_items.csv", raw_rows)
    return output_dir


def fetch_detail_bundle(
    session: requests.Session,
    headers: dict[str, str],
    blogger_id: int | str,
    timestamp: str | None,
    signature: str | None,
    year_begin: str,
    year_end: str,
    trend_begin: str,
    trend_end: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "blogger_id": blogger_id,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "apis": {},
    }

    api_plan = [
        ("video_total", 2, "year", year_begin, year_end),
        ("live_total", 1, "year", year_begin, year_end),
        ("commerce_total", 3, "year", year_begin, year_end),
        ("fans_trend", 4, "custom", trend_begin, trend_end),
    ]

    for name, total_type, period, begin_date, end_date in api_plan:
        result["apis"][name] = blogger_total(
            session,
            headers,
            total_type,
            blogger_id,
            timestamp,
            signature,
            period,
            begin_date,
            end_date,
        )
        time.sleep(REQUEST_DELAY)

    result["apis"]["overview"] = blogger_overview(session, headers, blogger_id, timestamp, signature)
    return result


def resolve_detail_params(args: argparse.Namespace, ckpt: dict[str, Any] | None = None) -> dict[str, str]:
    existing = (ckpt or {}).get("detail_params", {})
    return {
        "year_begin": args.year_begin or existing.get("year_begin") or default_year_begin(),
        "year_end": args.year_end or existing.get("year_end") or default_end_date(),
        "trend_begin": args.trend_begin or existing.get("trend_begin") or default_trend_begin(),
        "trend_end": args.trend_end or existing.get("trend_end") or default_end_date(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Feigua Kuaishou blogger API scraper")
    parser.add_argument("--action", choices=["search", "detail", "all", "full", "export-csv"], default="all")
    parser.add_argument("--keyword", default="", help="Search keyword")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--sort", type=int, default=DEFAULT_SEARCH_SORT, help="Search sort code; 5 returns high GMV bloggers in observed responses")
    parser.add_argument("--blogger-id", default="74865", help="Feigua Kuaishou bloggerId")
    parser.add_argument("--timestamp", default=None, help="Detail page timestamp")
    parser.add_argument("--signature", default=None, help="Detail page signature")
    parser.add_argument("--year-begin", default=None, help="Detail yearly begin date; full mode reuses checkpoint value when omitted")
    parser.add_argument("--year-end", default=None, help="Detail yearly end date; full mode reuses checkpoint value when omitted")
    parser.add_argument("--trend-begin", default=None, help="Trend begin date; full mode reuses checkpoint value when omitted")
    parser.add_argument("--trend-end", default=None, help="Trend end date; full mode reuses checkpoint value when omitted")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit full search pages for testing")
    parser.add_argument("--max-bloggers", type=int, default=None, help="Limit full detail bloggers for testing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.action == "export-csv":
        ckpt = load_full_checkpoint()
        output_dir = export_full_csv(ckpt)
        print(f"CSV files saved: {output_dir}")
        print(
            "CSV export summary: "
            f"bloggers={len(ckpt.get('bloggers', {}))}, "
            f"details={len(ckpt.get('detail_parsed', {}))}, "
            f"failures={len(ckpt.get('detail_failures', {}))}"
        )
        return 0

    headers = load_headers()
    timestamp, signature = load_auth_args(args)
    session = requests.Session()

    raw_result: dict[str, Any] = {
        "platform": "ks_feigua",
        "action": args.action,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }
    parsed_result: dict[str, Any] = {
        "platform": "ks_feigua",
        "action": args.action,
        "fetched_at": raw_result["fetched_at"],
    }

    try:
        if args.action == "full":
            ckpt = fetch_all_search_pages(
                session,
                headers,
                args.keyword,
                args.page_size,
                args.sort,
                args.max_pages,
            )
            detail_params = resolve_detail_params(args, ckpt)
            ckpt = fetch_all_details(
                session,
                headers,
                ckpt,
                detail_params["year_begin"],
                detail_params["year_end"],
                detail_params["trend_begin"],
                detail_params["trend_end"],
                args.max_bloggers,
            )
            raw_result, parsed_result = build_full_outputs(ckpt)
            raw_output = save_json_result(raw_result, "ks_feigua_full_raw")
            parsed_output = save_json_result(parsed_result, "ks_feigua_full_parsed")
            print(f"Raw response saved: {raw_output}")
            print(f"Parsed data saved: {parsed_output}")
            print(
                "Full scrape summary: "
                f"bloggers={len(ckpt.get('bloggers', {}))}, "
                f"details={len(ckpt.get('detail_parsed', {}))}, "
                f"failures={len(ckpt.get('detail_failures', {}))}"
            )
            return 0

        if args.action in ("search", "all"):
            raw_result["search"] = search_bloggers(session, headers, args.keyword, args.page, args.page_size, args.sort)
            parsed_result["search"] = parse_search(raw_result["search"])
            time.sleep(REQUEST_DELAY)

        if args.action in ("detail", "all"):
            detail_params = resolve_detail_params(args)
            raw_result["detail"] = fetch_detail_bundle(
                session,
                headers,
                args.blogger_id,
                timestamp,
                signature,
                detail_params["year_begin"],
                detail_params["year_end"],
                detail_params["trend_begin"],
                detail_params["trend_end"],
            )
            parsed_result["detail"] = parse_detail_bundle(raw_result["detail"])
    except (requests.RequestException, FeiguaKuaishouError) as e:
        print(f"Scrape failed: {e}")
        return 1

    raw_output = save_json_result(raw_result, f"ks_feigua_{args.action}_raw")
    parsed_output = save_json_result(parsed_result, f"ks_feigua_{args.action}_parsed")
    print(f"Raw response saved: {raw_output}")
    print(f"Parsed data saved: {parsed_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
