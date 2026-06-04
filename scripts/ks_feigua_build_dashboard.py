"""Build an offline Feigua Kuaishou blogger analysis dashboard."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    from scripts import _bootstrap  # noqa: F401

from saas_crawler.core.paths import DATA_DIR


BASE_FIELDS = ["blogger_id", "Nick", "KwaiId", "SearchFans", "BloggerJumpUrl"]
TOP_COMMERCE = 20
TOP_SEGMENTS = 50


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if not math.isnan(float(value)) else None

    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "null", "None", "nan"}:
        return None

    percent = text.endswith("%")
    if percent:
        text = text[:-1]

    multiplier = 1.0
    if text.endswith("万") or text.lower().endswith("w"):
        multiplier = 10000.0
        text = text[:-1]
    elif text.endswith("亿"):
        multiplier = 100000000.0
        text = text[:-1]

    try:
        result = float(text) * multiplier
    except ValueError:
        return None
    return result / 100.0 if percent else result


def as_int(value: float | None) -> int | None:
    if value is None:
        return None
    return int(round(value))


def latest_csv_dir(input_dir: str | None = None) -> Path:
    if input_dir:
        path = Path(input_dir)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            raise FileNotFoundError(f"Input directory not found: {path}")
        return path

    candidates = [path for path in DATA_DIR.glob("ks_feigua_csv_*") if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No ks_feigua_csv_* directory found under {DATA_DIR}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def row_id(row: dict[str, Any], fallback: str = "") -> str:
    return str(row.get("blogger_id") or row.get("BloggerId") or fallback).strip()


def first_nonempty(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", "-", [], {}):
            return value
    return ""


def extract_source_sorts(row: dict[str, Any]) -> list[int]:
    raw = row.get("_search_sources", "")
    if not raw:
        return []
    try:
        sources = json.loads(raw)
    except json.JSONDecodeError:
        return [int(v) for v in re.findall(r"'sort':\s*(\d+)|\"sort\":\s*(\d+)", raw) for v in v if v]

    sorts = []
    if isinstance(sources, list):
        for source in sources:
            try:
                sorts.append(int(source.get("sort")))
            except (AttributeError, TypeError, ValueError):
                pass
    return sorted(set(sorts))


def extract_best_rank(row: dict[str, Any]) -> int | None:
    raw = row.get("_search_sources", "")
    if not raw:
        return None
    try:
        sources = json.loads(raw)
    except json.JSONDecodeError:
        ranks = []
        for page, rank in re.findall(r"'page':\s*(\d+).*?'rank_in_page':\s*(\d+)|\"page\":\s*(\d+).*?\"rank_in_page\":\s*(\d+)", raw):
            nums = [v for v in (page, rank) if v]
            if len(nums) == 2:
                ranks.append((int(nums[0]) - 1) * 20 + int(nums[1]))
        return min(ranks) if ranks else None

    ranks = []
    if isinstance(sources, list):
        for source in sources:
            try:
                ranks.append((int(source.get("page")) - 1) * int(source.get("page_size", 20)) + int(source.get("rank_in_page")))
            except (TypeError, ValueError):
                pass
    return min(ranks) if ranks else None


def compact_item(row: dict[str, str], numeric_fields: list[str]) -> dict[str, Any]:
    result = {key: row.get(key, "") for key in row if row.get(key, "") not in ("", None)}
    for key in numeric_fields:
        result[f"{key}_num"] = as_int(parse_number(row.get(key)))
    return result


def build_dashboard_data(input_dir: Path) -> dict[str, Any]:
    bloggers = read_csv(input_dir / "bloggers.csv")
    summaries = read_csv(input_dir / "detail_summary.csv")
    commerce_rows = read_csv(input_dir / "commerce.csv")
    trend_rows = read_csv(input_dir / "fans_trend.csv")
    live_rows = read_csv(input_dir / "overview_lives.csv")
    video_rows = read_csv(input_dir / "overview_videos.csv")
    segment_rows = read_csv(input_dir / "segments.csv")
    status_rows = read_csv(input_dir / "api_status.csv")

    bloggers_by_id = {row_id(row): row for row in bloggers if row_id(row)}
    summaries_by_id = {row_id(row): row for row in summaries if row_id(row)}

    commerce_by_id: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: {"category": [], "brand": []})
    for row in commerce_rows:
        bid = row_id(row)
        group = row.get("type", "")
        if not bid or group not in {"category", "brand"}:
            continue
        amount = parse_number(row.get("Ratio"))
        commerce_by_id[bid][group].append({
            "name": row.get("Name", ""),
            "amount": amount or 0,
            "amountText": row.get("Ratio", ""),
        })

    trends_by_id: dict[str, dict[str, dict[str, dict[str, Any]]]] = defaultdict(lambda: defaultdict(dict))
    for row in trend_rows:
        bid = row_id(row)
        series = row.get("series", "")
        date = row.get("Date", "")
        if not bid or not series or not date:
            continue
        trends_by_id[bid][date][series] = row

    lives_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in live_rows:
        bid = row_id(row)
        if not bid:
            continue
        lives_by_id[bid].append(compact_item(row, ["DisplayWatchCount", "TotalVolume", "TotalPrice"]))

    videos_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in video_rows:
        bid = row_id(row)
        if not bid:
            continue
        videos_by_id[bid].append(compact_item(row, ["LikeCount", "CommentCount", "ViewCount"]))

    segments_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in segment_rows:
        bid = row_id(row)
        if not bid:
            continue
        count = parse_number(row.get("Count"))
        segments_by_id[bid].append({
            "group": row.get("group", ""),
            "segment": row.get("Segment", ""),
            "count": as_int(count) or 0,
            "countText": row.get("CountStr", ""),
        })

    status_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in status_rows:
        bid = row_id(row)
        if bid:
            status_by_id[bid].append(row)

    all_ids = sorted(set(bloggers_by_id) | set(summaries_by_id), key=lambda value: int(value) if value.isdigit() else value)
    profiles = []
    details_by_id = {}
    sort_values = set()
    category_values = set()

    for bid in all_ids:
        blogger = bloggers_by_id.get(bid, {})
        summary = summaries_by_id.get(bid, {})
        commerce = commerce_by_id.get(bid, {"category": [], "brand": []})
        categories = sorted(commerce["category"], key=lambda row: row["amount"], reverse=True)[:TOP_COMMERCE]
        brands = sorted(commerce["brand"], key=lambda row: row["amount"], reverse=True)[:TOP_COMMERCE]
        commerce_total = sum(item["amount"] for item in categories)
        top_category = categories[0] if categories else {}
        top_brand = brands[0] if brands else {}

        trend_series = build_trend_series(trends_by_id.get(bid, {}))
        trend_summary = summarize_trend(trend_series)
        recent_lives = sorted(lives_by_id.get(bid, []), key=lambda row: row.get("Date", ""), reverse=True)[:10]
        recent_videos = sorted(videos_by_id.get(bid, []), key=lambda row: row.get("Date", ""), reverse=True)[:10]
        top_segments = sorted(segments_by_id.get(bid, []), key=lambda row: row.get("count", 0), reverse=True)[:TOP_SEGMENTS]

        live_total_price = sum(parse_number(item.get("TotalPrice")) or item.get("TotalPrice_num") or 0 for item in recent_lives)
        live_total_volume = sum(parse_number(item.get("TotalVolume")) or item.get("TotalVolume_num") or 0 for item in recent_lives)
        video_total_views = sum(parse_number(item.get("ViewCount")) or item.get("ViewCount_num") or 0 for item in recent_videos)
        video_total_likes = sum(parse_number(item.get("LikeCount")) or item.get("LikeCount_num") or 0 for item in recent_videos)
        video_total_comments = sum(parse_number(item.get("CommentCount")) or item.get("CommentCount_num") or 0 for item in recent_videos)

        source_sorts = extract_source_sorts(blogger)
        sort_values.update(source_sorts)
        if top_category.get("name"):
            category_values.add(top_category["name"])

        profile = {
            "blogger_id": bid,
            "nick": first_nonempty(blogger.get("Nick"), summary.get("Nick")),
            "kwaiId": first_nonempty(blogger.get("KwaiId"), summary.get("KwaiId")),
            "fansText": first_nonempty(blogger.get("Fans"), summary.get("SearchFans")),
            "fans": as_int(parse_number(first_nonempty(blogger.get("Fans"), summary.get("SearchFans")))),
            "score": parse_number(blogger.get("Score")),
            "jumpUrl": first_nonempty(blogger.get("BloggerJumpUrl"), summary.get("BloggerJumpUrl")),
            "sourceSorts": source_sorts,
            "sourceBestRank": extract_best_rank(blogger),
            "videoPlays": as_int(parse_number(summary.get("视频_播放数_当前"))),
            "videoLikes": as_int(parse_number(summary.get("视频_点赞数_当前"))),
            "videoComments": as_int(parse_number(summary.get("视频_评论数_当前"))),
            "videoShares": as_int(parse_number(summary.get("视频_分享数_当前"))),
            "liveCount": as_int(parse_number(summary.get("直播_直播数_当前"))),
            "liveSalesAmount": as_int(parse_number(summary.get("直播_预估直播销售额_当前"))),
            "liveSalesVolume": as_int(parse_number(summary.get("直播_预估直播销量_当前"))),
            "commerceAmount": as_int(commerce_total),
            "topCategory": top_category.get("name", ""),
            "topCategoryAmount": as_int(top_category.get("amount")),
            "topBrand": top_brand.get("name", ""),
            "topBrandAmount": as_int(top_brand.get("amount")),
            "fansStart": trend_summary["fansStart"],
            "fansEnd": trend_summary["fansEnd"],
            "fansGrowth": trend_summary["fansGrowth"],
            "viewsGrowth": trend_summary["viewsGrowth"],
            "likesGrowth": trend_summary["likesGrowth"],
            "commentsGrowth": trend_summary["commentsGrowth"],
            "recentLiveCount": len(recent_lives),
            "recentLiveSalesAmount": as_int(live_total_price),
            "recentLiveVolume": as_int(live_total_volume),
            "recentVideoCount": len(recent_videos),
            "recentVideoViews": as_int(video_total_views),
            "recentVideoLikes": as_int(video_total_likes),
            "recentVideoComments": as_int(video_total_comments),
            "hasDetail": bid in summaries_by_id,
            "hasCommerce": bool(categories or brands),
            "hasTrend": bool(trend_series["dates"]),
            "hasLives": bool(recent_lives),
            "hasVideos": bool(recent_videos),
            "hasSegments": bool(top_segments),
        }
        profiles.append(profile)

        details_by_id[bid] = {
            "profile": profile,
            "trend": trend_series,
            "commerce": {"categories": categories, "brands": brands},
            "lives": recent_lives,
            "videos": recent_videos,
            "segments": top_segments,
            "apiStatus": status_by_id.get(bid, []),
        }

    global_stats = {
        "bloggers": len(profiles),
        "details": sum(1 for item in profiles if item["hasDetail"]),
        "commerce": sum(1 for item in profiles if item["hasCommerce"]),
        "trend": sum(1 for item in profiles if item["hasTrend"]),
        "lives": sum(1 for item in profiles if item["hasLives"]),
        "videos": sum(1 for item in profiles if item["hasVideos"]),
        "segments": sum(1 for item in profiles if item["hasSegments"]),
        "inputDir": str(input_dir),
    }

    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "globalStats": global_stats,
        "filterOptions": {
            "sorts": sorted(sort_values),
            "categories": sorted(category_values),
        },
        "profiles": profiles,
        "detailsById": details_by_id,
    }


def build_trend_series(date_map: dict[str, dict[str, dict[str, str]]]) -> dict[str, list[Any]]:
    dates = sorted(date_map)
    result = {
        "dates": [],
        "fans": [],
        "incFans": [],
        "views": [],
        "likes": [],
        "comments": [],
    }
    for date in dates:
        data = date_map[date]
        total_fans = data.get("total_fans", {})
        inc_fans = data.get("increment_fans", {})
        inc_video = data.get("increment_video", {})
        result["dates"].append(date)
        result["fans"].append(as_int(parse_number(total_fans.get("Fans"))))
        result["incFans"].append(as_int(parse_number(inc_fans.get("Fans"))))
        result["views"].append(as_int(parse_number(inc_video.get("TotalViews"))))
        result["likes"].append(as_int(parse_number(inc_video.get("Likes"))))
        result["comments"].append(as_int(parse_number(inc_video.get("TotalComments"))))
    return result


def summarize_trend(series: dict[str, list[Any]]) -> dict[str, int | None]:
    fans = [value for value in series.get("fans", []) if value is not None]
    views = [value for value in series.get("views", []) if value is not None]
    likes = [value for value in series.get("likes", []) if value is not None]
    comments = [value for value in series.get("comments", []) if value is not None]
    fans_start = fans[0] if fans else None
    fans_end = fans[-1] if fans else None
    return {
        "fansStart": fans_start,
        "fansEnd": fans_end,
        "fansGrowth": fans_end - fans_start if fans_start is not None and fans_end is not None else None,
        "viewsGrowth": sum(views) if views else None,
        "likesGrowth": sum(likes) if likes else None,
        "commentsGrowth": sum(comments) if comments else None,
    }


def write_dashboard(output_dir: Path, data: dict[str, Any]) -> None:
    assets = output_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (assets / "dashboard.css").write_text(DASHBOARD_CSS, encoding="utf-8")
    (assets / "dashboard.js").write_text(DASHBOARD_JS, encoding="utf-8")
    data_text = "window.KS_FEIGUA_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (assets / "data.js").write_text(data_text, encoding="utf-8")
    (output_dir / "README.txt").write_text(
        "Open index.html in a browser. If your browser blocks local scripts, run a local static server in this directory.\n",
        encoding="utf-8",
    )


def csv_cell(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else value


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
            writer.writerow({key: csv_cell(row.get(key, "")) for key in headers})


def write_mart_csv(output_dir: Path, data: dict[str, Any]) -> Path:
    mart_dir = output_dir / "mart"
    profiles = data.get("profiles", [])
    details_by_id = data.get("detailsById", {})

    profile_rows = []
    trend_rows = []
    commerce_rows = []
    live_rows = []
    video_rows = []
    segment_rows = []
    quality_rows = []

    for profile in profiles:
        bid = profile.get("blogger_id", "")
        detail = details_by_id.get(bid, {})
        profile_rows.append({
            **profile,
            "sourceSorts": ",".join(str(v) for v in profile.get("sourceSorts", [])),
        })

        trend = detail.get("trend", {})
        dates = trend.get("dates", [])
        for index, day in enumerate(dates):
            trend_rows.append({
                "blogger_id": bid,
                "Nick": profile.get("nick", ""),
                "Date": day,
                "fans": value_at(trend, "fans", index),
                "incFans": value_at(trend, "incFans", index),
                "views": value_at(trend, "views", index),
                "likes": value_at(trend, "likes", index),
                "comments": value_at(trend, "comments", index),
            })

        for group, items in (("category", detail.get("commerce", {}).get("categories", [])), ("brand", detail.get("commerce", {}).get("brands", []))):
            for rank, item in enumerate(items, 1):
                commerce_rows.append({
                    "blogger_id": bid,
                    "Nick": profile.get("nick", ""),
                    "type": group,
                    "rank": rank,
                    "name": item.get("name", ""),
                    "amount": item.get("amount", ""),
                    "amountText": item.get("amountText", ""),
                })

        for rank, item in enumerate(detail.get("lives", []), 1):
            live_rows.append({"blogger_id": bid, "Nick": profile.get("nick", ""), "rank": rank, **item})

        for rank, item in enumerate(detail.get("videos", []), 1):
            video_rows.append({"blogger_id": bid, "Nick": profile.get("nick", ""), "rank": rank, **item})

        for rank, item in enumerate(detail.get("segments", []), 1):
            segment_rows.append({"blogger_id": bid, "Nick": profile.get("nick", ""), "rank": rank, **item})

        quality_rows.append({
            "blogger_id": bid,
            "Nick": profile.get("nick", ""),
            "hasDetail": profile.get("hasDetail", False),
            "hasCommerce": profile.get("hasCommerce", False),
            "hasTrend": profile.get("hasTrend", False),
            "hasLives": profile.get("hasLives", False),
            "hasVideos": profile.get("hasVideos", False),
            "hasSegments": profile.get("hasSegments", False),
            "commerceRows": len(detail.get("commerce", {}).get("categories", [])) + len(detail.get("commerce", {}).get("brands", [])),
            "trendRows": len(dates),
            "liveRows": len(detail.get("lives", [])),
            "videoRows": len(detail.get("videos", [])),
            "segmentRows": len(detail.get("segments", [])),
        })

    profile_headers = [
        "blogger_id", "nick", "kwaiId", "fansText", "fans", "score", "jumpUrl",
        "sourceSorts", "sourceBestRank", "videoPlays", "videoLikes", "videoComments",
        "videoShares", "liveCount", "liveSalesAmount", "liveSalesVolume",
        "commerceAmount", "topCategory", "topCategoryAmount", "topBrand",
        "topBrandAmount", "fansStart", "fansEnd", "fansGrowth", "viewsGrowth",
        "likesGrowth", "commentsGrowth", "recentLiveCount", "recentLiveSalesAmount",
        "recentLiveVolume", "recentVideoCount", "recentVideoViews",
        "recentVideoLikes", "recentVideoComments", "hasDetail", "hasCommerce",
        "hasTrend", "hasLives", "hasVideos", "hasSegments",
    ]

    write_csv(mart_dir / "mart_blogger_profile.csv", profile_rows, profile_headers)
    write_csv(mart_dir / "fact_blogger_trend.csv", trend_rows, ["blogger_id", "Nick", "Date", "fans", "incFans", "views", "likes", "comments"])
    write_csv(mart_dir / "fact_commerce.csv", commerce_rows, ["blogger_id", "Nick", "type", "rank", "name", "amount", "amountText"])
    write_csv(mart_dir / "fact_recent_lives.csv", live_rows)
    write_csv(mart_dir / "fact_recent_videos.csv", video_rows)
    write_csv(mart_dir / "fact_segments.csv", segment_rows, ["blogger_id", "Nick", "rank", "group", "segment", "count", "countText"])
    write_csv(mart_dir / "quality_report.csv", quality_rows)
    return mart_dir


def value_at(mapping: dict[str, list[Any]], key: str, index: int) -> Any:
    values = mapping.get(key, [])
    return values[index] if index < len(values) else ""


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>飞瓜快手达人分析</title>
  <link rel="stylesheet" href="assets/dashboard.css" />
</head>
<body>
  <div class="app">
    <header class="topbar">
      <div>
        <h1>飞瓜快手达人分析</h1>
        <p id="metaText"></p>
      </div>
      <div class="badge">离线静态看板</div>
    </header>

    <section class="kpis" id="kpis"></section>

    <section class="filters">
      <label>搜索<input id="q" type="search" placeholder="昵称 / 快手号" /></label>
      <label>sort来源<select id="sortFilter"><option value="">全部</option></select></label>
      <label>粉丝区间<select id="fansFilter"><option value="">全部</option><option value="0-100000">10万以下</option><option value="100000-1000000">10万-100万</option><option value="1000000-10000000">100万-1000万</option><option value="10000000-">1000万以上</option></select></label>
      <label>带货金额<select id="commerceFilter"><option value="">全部</option><option value="1-1000000">100万以下</option><option value="1000000-10000000">100万-1000万</option><option value="10000000-100000000">1000万-1亿</option><option value="100000000-">1亿以上</option></select></label>
      <label class="check"><input id="hasTrend" type="checkbox" /> 有趋势</label>
      <label class="check"><input id="hasCommerce" type="checkbox" /> 有带货</label>
      <label class="check"><input id="hasVideos" type="checkbox" /> 有视频</label>
      <label class="check"><input id="hasLives" type="checkbox" /> 有直播</label>
    </section>

    <main class="layout">
      <section class="panel list-panel">
        <div class="panel-head">
          <h2>达人列表</h2>
          <span id="listCount"></span>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>达人</th><th>粉丝</th><th>播放</th><th>直播销售额</th><th>增粉</th><th>主品类</th><th>覆盖</th></tr></thead>
            <tbody id="bloggerRows"></tbody>
          </table>
        </div>
      </section>

      <section class="panel detail-panel">
        <div class="panel-head">
          <div>
            <h2 id="detailTitle">选择一个达人</h2>
            <p id="detailSub"></p>
          </div>
        </div>
        <div id="detailBody" class="detail-body"></div>
      </section>
    </main>
  </div>
  <script src="assets/data.js"></script>
  <script src="assets/dashboard.js"></script>
</body>
</html>
"""


DASHBOARD_CSS = """
:root{--bg:#f6f7f9;--panel:#fff;--ink:#1f2933;--muted:#6b7280;--line:#d8dde6;--accent:#0f766e;--accent2:#2563eb;--warn:#b45309}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}
.app{max-width:1600px;margin:0 auto;padding:20px}.topbar{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:16px}h1{margin:0;font-size:28px}h2{margin:0;font-size:16px}p{margin:4px 0;color:var(--muted)}.badge{border:1px solid var(--line);background:#eef8f6;color:var(--accent);padding:6px 10px;border-radius:6px}
.kpis{display:grid;grid-template-columns:repeat(6,minmax(120px,1fr));gap:10px;margin-bottom:14px}.kpi{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px}.kpi b{display:block;font-size:22px}.kpi span{color:var(--muted)}
.filters{display:grid;grid-template-columns:2fr 1fr 1fr 1fr repeat(4,auto);gap:10px;align-items:end;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;margin-bottom:14px}
label{display:flex;flex-direction:column;gap:4px;color:var(--muted);font-size:12px}.check{flex-direction:row;align-items:center;font-size:13px;color:var(--ink)}input,select{height:34px;border:1px solid var(--line);border-radius:6px;padding:0 8px;background:#fff;color:var(--ink)}
.layout{display:grid;grid-template-columns:minmax(620px,1fr) minmax(520px,.9fr);gap:14px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;min-width:0}.panel-head{display:flex;justify-content:space-between;align-items:center;padding:12px;border-bottom:1px solid var(--line)}.table-wrap{max-height:720px;overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:9px 10px;border-bottom:1px solid #eef1f5;text-align:left;white-space:nowrap}th{position:sticky;top:0;background:#f8fafc;z-index:1;color:#4b5563;font-weight:600}tbody tr{cursor:pointer}tbody tr:hover,tbody tr.active{background:#eef8f6}.name{font-weight:600}.muted{color:var(--muted)}.chips{display:flex;gap:4px;flex-wrap:wrap}.chip{font-size:11px;padding:2px 6px;border-radius:999px;background:#eef2ff;color:#3730a3}.chip.off{background:#f3f4f6;color:#9ca3af}
.detail-body{padding:12px;display:grid;gap:12px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.mini{border:1px solid var(--line);border-radius:8px;padding:10px}.mini b{display:block;font-size:18px}.section{border:1px solid var(--line);border-radius:8px;padding:12px;min-width:0}.section h3{margin:0 0 10px;font-size:14px}.chart{width:100%;height:220px}.bars{display:grid;gap:8px}.bar-row{display:grid;grid-template-columns:120px 1fr 80px;gap:8px;align-items:center}.bar{height:10px;background:#e5e7eb;border-radius:999px;overflow:hidden}.bar i{display:block;height:100%;background:var(--accent2)}.empty{padding:26px;text-align:center;color:var(--muted);border:1px dashed var(--line);border-radius:8px}.tooltip{font-size:12px;fill:#6b7280}.line1{stroke:var(--accent);fill:none;stroke-width:2}.line2{stroke:var(--accent2);fill:none;stroke-width:2}.line3{stroke:var(--warn);fill:none;stroke-width:2}.axis{stroke:#cbd5e1;stroke-width:1}
@media(max-width:1100px){.layout{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(3,1fr)}.filters{grid-template-columns:1fr 1fr}.cards{grid-template-columns:repeat(2,1fr)}}
"""


DASHBOARD_JS = """
const DATA = window.KS_FEIGUA_DATA || {profiles:[],detailsById:{},globalStats:{}};
const fmt = n => n == null || Number.isNaN(n) ? '-' : Number(n).toLocaleString('zh-CN');
const money = n => n == null ? '-' : n >= 1e8 ? (n/1e8).toFixed(2)+'亿' : n >= 1e4 ? (n/1e4).toFixed(1)+'万' : fmt(n);
const $ = id => document.getElementById(id);
let filtered = [...DATA.profiles];
let selectedId = filtered[0]?.blogger_id;

function init(){
  $('metaText').textContent = `生成时间 ${DATA.generatedAt || '-'} · 数据源 ${DATA.globalStats?.inputDir || '-'}`;
  renderKpis();
  populateFilters();
  bindFilters();
  applyFilters();
}
function renderKpis(){
  const s=DATA.globalStats||{};
  const items=[['达人',s.bloggers],['详情',s.details],['带货',s.commerce],['趋势',s.trend],['直播',s.lives],['视频',s.videos]];
  $('kpis').innerHTML=items.map(([k,v])=>`<div class="kpi"><b>${fmt(v)}</b><span>${k}</span></div>`).join('');
}
function populateFilters(){
  $('sortFilter').insertAdjacentHTML('beforeend',(DATA.filterOptions?.sorts||[]).map(v=>`<option value="${v}">sort ${v}</option>`).join(''));
}
function bindFilters(){
  ['q','sortFilter','fansFilter','commerceFilter','hasTrend','hasCommerce','hasVideos','hasLives'].forEach(id=>$(id).addEventListener('input',applyFilters));
}
function inRange(value, range){
  if(!range) return true;
  const [a,b]=range.split('-'); const min=a?Number(a):null; const max=b?Number(b):null;
  if(value == null) return false;
  return (min==null || value>=min) && (max==null || value<max);
}
function applyFilters(){
  const q=$('q').value.trim().toLowerCase(), sort=$('sortFilter').value;
  filtered = DATA.profiles.filter(p=>{
    if(q && !`${p.nick||''} ${p.kwaiId||''}`.toLowerCase().includes(q)) return false;
    if(sort && !(p.sourceSorts||[]).map(String).includes(sort)) return false;
    if(!inRange(p.fans,$('fansFilter').value)) return false;
    if(!inRange(p.commerceAmount,$('commerceFilter').value)) return false;
    if($('hasTrend').checked && !p.hasTrend) return false;
    if($('hasCommerce').checked && !p.hasCommerce) return false;
    if($('hasVideos').checked && !p.hasVideos) return false;
    if($('hasLives').checked && !p.hasLives) return false;
    return true;
  }).sort((a,b)=>(b.commerceAmount||0)-(a.commerceAmount||0) || (b.fans||0)-(a.fans||0));
  if(!filtered.find(p=>p.blogger_id===selectedId)) selectedId=filtered[0]?.blogger_id;
  renderList(); renderDetail(selectedId);
}
function renderList(){
  $('listCount').textContent=`${fmt(filtered.length)} / ${fmt(DATA.profiles.length)}`;
  $('bloggerRows').innerHTML=filtered.slice(0,500).map(p=>`
    <tr class="${p.blogger_id===selectedId?'active':''}" data-id="${p.blogger_id}">
      <td><div class="name">${p.nick||'-'}</div><div class="muted">${p.kwaiId||p.blogger_id}</div></td>
      <td>${p.fansText||money(p.fans)}</td><td>${money(p.videoPlays)}</td><td>${money(p.liveSalesAmount||p.commerceAmount)}</td>
      <td>${money(p.fansGrowth)}</td><td>${p.topCategory||'-'}</td><td>${chips(p)}</td>
    </tr>`).join('');
  document.querySelectorAll('#bloggerRows tr').forEach(tr=>tr.addEventListener('click',()=>{selectedId=tr.dataset.id;renderList();renderDetail(selectedId)}));
}
function chips(p){return `<div class="chips">${[['货',p.hasCommerce],['趋',p.hasTrend],['播',p.hasLives],['视',p.hasVideos]].map(([t,on])=>`<span class="chip ${on?'':'off'}">${t}</span>`).join('')}</div>`}
function renderDetail(id){
  const d=DATA.detailsById[id]; if(!d){$('detailTitle').textContent='没有匹配达人';$('detailSub').textContent='';$('detailBody').innerHTML='<div class="empty">调整筛选条件</div>';return}
  const p=d.profile; $('detailTitle').textContent=p.nick||id; $('detailSub').textContent=`${p.kwaiId||id} · 粉丝 ${p.fansText||money(p.fans)} · sort ${(p.sourceSorts||[]).join(',')||'-'}`;
  $('detailBody').innerHTML=`
    <div class="cards">
      ${mini('带货金额',money(p.commerceAmount))}${mini('增粉',money(p.fansGrowth))}${mini('近10视频播放',money(p.recentVideoViews))}${mini('近10直播销售额',money(p.recentLiveSalesAmount))}
    </div>
    <div class="section"><h3>粉丝趋势</h3>${lineChart(d.trend.dates,d.trend.fans,'fans')}</div>
    <div class="section"><h3>播放 / 点赞 / 评论增量</h3>${multiLineChart(d.trend.dates,[d.trend.views,d.trend.likes,d.trend.comments])}</div>
    <div class="section"><h3>近10视频</h3>${barList(d.videos,'Title','ViewCount_num','播放')}</div>
    <div class="section"><h3>近10直播</h3>${barList(d.lives,'Title','TotalPrice_num','销售额')}</div>
    <div class="section"><h3>带货品类</h3>${barList(d.commerce.categories,'name','amount','金额')}</div>
    <div class="section"><h3>高频词段</h3>${barList(d.segments,'segment','count','次数')}</div>`;
}
function mini(k,v){return `<div class="mini"><b>${v}</b><span class="muted">${k}</span></div>`}
function lineChart(labels, values){return multiLineChart(labels,[values])}
function multiLineChart(labels, series){
  if(!labels?.length || !series.some(s=>s?.some(v=>v!=null))) return '<div class="empty">暂无趋势数据</div>';
  const w=720,h=220,p=28; const all=series.flat().filter(v=>v!=null); const min=Math.min(...all),max=Math.max(...all); const span=max-min||1;
  const lines=series.map((s,i)=>{const pts=s.map((v,idx)=>v==null?null:[p+idx*(w-2*p)/Math.max(1,labels.length-1), h-p-(v-min)*(h-2*p)/span]).filter(Boolean);return `<polyline class="line${i+1}" points="${pts.map(p=>p.join(',')).join(' ')}"/>`}).join('');
  return `<svg class="chart" viewBox="0 0 ${w} ${h}"><line class="axis" x1="${p}" y1="${h-p}" x2="${w-p}" y2="${h-p}"/><line class="axis" x1="${p}" y1="${p}" x2="${p}" y2="${h-p}"/>${lines}<text class="tooltip" x="${p}" y="18">${fmt(max)}</text><text class="tooltip" x="${p}" y="${h-6}">${labels[0]} - ${labels[labels.length-1]}</text></svg>`
}
function barList(rows,labelKey,valueKey,valueName){
  rows=(rows||[]).filter(r=>r && (r[valueKey]!=null || r.amount!=null || r.count!=null)).slice(0,12);
  if(!rows.length) return '<div class="empty">暂无数据</div>';
  const max=Math.max(...rows.map(r=>Number(r[valueKey]||0)),1);
  return `<div class="bars">${rows.map(r=>{const v=Number(r[valueKey]||0);return `<div class="bar-row"><span title="${r[labelKey]||'-'}">${(r[labelKey]||'-').slice(0,16)}</span><div class="bar"><i style="width:${Math.max(2,v/max*100)}%"></i></div><b>${valueName==='次数'?fmt(v):money(v)}</b></div>`}).join('')}</div>`
}
init();
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build offline Feigua Kuaishou dashboard")
    parser.add_argument("--input", default=None, help="Input ks_feigua_csv_* directory. Defaults to latest.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = latest_csv_dir(args.input)
    data = build_dashboard_data(input_dir)
    output_dir = DATA_DIR / f"ks_feigua_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    write_dashboard(output_dir, data)
    mart_dir = write_mart_csv(output_dir, data)
    stats = data["globalStats"]
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Mart CSV: {mart_dir}")
    print(
        "Summary: "
        f"bloggers={stats['bloggers']}, details={stats['details']}, "
        f"commerce={stats['commerce']}, trend={stats['trend']}, "
        f"lives={stats['lives']}, videos={stats['videos']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
