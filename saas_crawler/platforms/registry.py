"""Known platform definitions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Platform:
    key: str
    name: str
    script: str
    description: str


PLATFORMS: dict[str, Platform] = {
    "huohua": Platform(
        key="huohua",
        name="火花",
        script="scripts/scraper_browser.py",
        description="B站火花平台 UP 主列表和详情采集",
    ),
    "feigua": Platform(
        key="feigua",
        name="飞瓜",
        script="scripts/feigua_scraper.py",
        description="飞瓜平台 B站 UP 主和 MCN 数据采集",
    ),
    "ks_feigua": Platform(
        key="ks_feigua",
        name="飞瓜快手",
        script="scripts/ks_feigua_scraper.py",
        description="飞瓜快手达人搜索、达人详情概览、直播/视频/带货/粉丝趋势数据采集",
    ),
    "magnetic_juxing": Platform(
        key="magnetic_juxing",
        name="磁力聚星",
        script="scripts/magnetic_juxing_scraper.py",
        description="磁力聚星热点榜单达人数据采集，支持首页榜单、完整热点榜单和接口探测",
    ),
    "xingtu": Platform(
        key="xingtu",
        name="星图",
        script="scripts/xingtu_scraper.py",
        description="星图达人市场 search_for_author_square 浏览器探测与响应结构采集",
    ),
}


def list_platforms() -> list[Platform]:
    return list(PLATFORMS.values())
