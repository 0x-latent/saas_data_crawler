# 飞瓜快手 API 文档

平台域名: `https://ks.feigua.cn`

本文档字段基于 2026-05-28 使用真实 Cookie 请求得到的响应确认。不同达人、不同权限下，部分字段可能返回 `null`、`-`、空列表或脱敏值。

## 配置

飞瓜 B 站和飞瓜快手 Cookie 必须区分:

```yaml
feigua_cookies:
  - "your_bz_feigua_cookie_here"

ks_feigua_cookies:
  - "your_ks_feigua_cookie_here"

# 只用于手工抓单个达人详情。
# 全量采集会从搜索结果 BloggerJumpUrl 中读取每个达人的 timestamp/signature。
ks_feigua:
  timestamp: ""
  signature: ""
```

`scripts/ks_feigua_scraper.py` 只读取 `ks_feigua_cookies`，不会读取 `feigua_cookies`。

## 通用响应结构

详情类接口通用外层字段:

| 字段 | 说明 |
| --- | --- |
| `Data` | 业务数据 |
| `Code` | 状态码，实测成功为 `200` |
| `Msg` | 状态消息，实测成功为 `操作成功` |
| `Status` | 成功状态 |
| `IsExample` | 是否示例数据 |
| `ClientAction` | 客户端动作，通常为 `null` |

搜索接口 `GET` 会返回 `405`，实际应使用 `POST`。

## 1. 达人搜索

- 接口: `POST /api/v1/blogger/search`
- 脚本方法: `search_bloggers`
- 用途: 分页获取达人列表；全量采集以此接口为入口

请求参数:

| 位置 | 字段 | 说明 |
| --- | --- | --- |
| query | `_` | 毫秒时间戳 |
| JSON body | `keyword` | 搜索关键词，可为空 |
| JSON body | `pageIndex` | 页码 |
| JSON body | `pageSize` | 每页数量，实测用 `20` |
| JSON body | `sort` | 排序类型；实测 `sort=0` 返回低活跃小号，`sort=5` 返回高带货达人 |

`Data` 字段:

| 字段 | 说明 |
| --- | --- |
| `SurplusCount` | 剩余可查看数量 |
| `SearchExportCount` | 搜索导出数量 |
| `TotalCount` | 搜索结果总数，实测空关键词为 `1000` |
| `PermissionCount` | 当前账号权限可查看数量，实测为 `500` |
| `FakePage` | 是否虚拟分页 |
| `ItemList` | 达人列表 |

`Data.ItemList[]` 字段:

| 字段 | 说明 |
| --- | --- |
| `BloggerId` | 飞瓜快手达人 ID，详情接口使用 |
| `IsLiving` | 是否正在直播 |
| `LivingJumpUrl` | 直播跳转地址 |
| `BloggerHeadUrl` | 头像 URL |
| `BloggerJumpUrl` | 达人详情跳转地址，包含 `id/timestamp/signature`，全量详情采集依赖这个字段 |
| `UserDesc` | 达人简介 |
| `KwaiId` | 快手号 |
| `Nick` | 昵称 |
| `CateName` | 分类名称 |
| `FormerName` | 曾用名 |
| `Fans` | 粉丝数，字符串格式 |
| `VideoCount` | 视频数 |
| `LiveProductScore` | 直播带货评分 |
| `Score` | 飞瓜评分 |
| `AvgPlay` | 平均播放 |
| `LiveCount` | 直播数 |
| `AvgDisPlayWatch` | 平均人气峰值/观看指标 |
| `ShopLiveCount` | 带货直播数 |
| `AvgVolumn` | 平均销量 |
| `AvgSalesPrice` | 平均销售额 |
| `CompetitionLiveCount` | 竞品/竞争直播数 |
| `GiftPriceTop1` | 礼物/打赏相关 Top1 字段 |
| `GiftPriceTop2` | 礼物/打赏相关 Top2 字段 |
| `BloggerType` | 达人类型 |
| `Volumn` | 销量 |
| `SalesPrice` | 销售额 |
| `AvgCustomerPrice` | 客单价 |
| `Verified` | 是否认证 |
| `VerifiedDescription` | 认证说明 |
| `VerifiedBlueV` | 是否蓝 V |
| `VerifiedType` | 认证类型 |
| `VerifiedImage` | 认证图标 |
| `Hasmcn` | 是否有 MCN |
| `HasLive` | 是否有直播 |
| `HasTel` | 是否有联系方式 |
| `ShowTelMessage` | 联系方式提示 |
| `ShopTypeSource` | 店铺类型来源 |
| `MainProductCate` | 主要带货品类 |
| `MainShorVedioTags` | 主要短视频标签 |
| `SimilarKeyWord` | 相似达人关键词 |
| `SimilarText` | 相似达人说明 |
| `FocusLimit` | 关注限制 |
| `FocusId` | 关注 ID |
| `FocusJumpurl` | 关注跳转地址 |
| `Fav` | 是否收藏 |
| `Tag` | 标签 |
| `BrandName` | 品牌名称 |
| `BrandJumpUrl` | 品牌跳转地址 |
| `BloggerSearchExtProduct` | 扩展商品信息对象 |
| `IsVideoMarket` | 是否视频市场相关 |
| `HasBriefHistory` | 是否有简介历史 |
| `VideoExpectedPlayCnt` | 视频预期播放 |
| `VideoExpectedCpm` | 视频预期 CPM |
| `PersonalVideoInteractionRate30Day` | 近 30 天个人视频互动率 |
| `PersonalVideoCompletePlayRate30Day` | 近 30 天个人视频完播率 |
| `VideoCooperationPrice` | 视频合作价格 |
| `BloggerUserId` | 达人用户 ID |
| `ShopName` | 店铺名称 |
| `ShopDetailUrl` | 店铺详情地址 |
| `BloggerStatus` | 达人状态 |
| `PrincipalBrandList` | 主理/关联品牌列表 |

`BloggerSearchExtProduct` 字段:

| 字段 | 说明 |
| --- | --- |
| `IsShow` | 是否展示扩展商品 |
| `JumpUrl` | 商品跳转地址 |
| `BloggerProducts` | 商品列表 |

脚本额外解析字段:

| 字段 | 来源 | 说明 |
| --- | --- | --- |
| `_detail_auth.blogger_id` | `BloggerJumpUrl.id` | 详情达人 ID |
| `_detail_auth.timestamp` | `BloggerJumpUrl.timestamp` | 详情接口签名时间戳 |
| `_detail_auth.signature` | `BloggerJumpUrl.signature` | 详情接口签名 |

## 2. 达人详情页视频数据

- 接口: `GET /api/v1/blogger/BloggerOverview_Total_2`
- 脚本方法: `blogger_total(..., total_type=2, ...)`
- 用途: 获取达人详情页的视频汇总指标

请求参数:

| 字段 | 说明 |
| --- | --- |
| `period` | 周期，实测 `year` |
| `beginDate` | 开始日期，如 `2026/01/01` |
| `endDate` | 结束日期，如 `2026-05-27` |
| `bloggerId` | 达人 ID |
| `_` | 毫秒时间戳 |
| `timestamp` | 签名时间戳 |
| `signature` | 签名 |

`Data` 字段:

| 字段 | 说明 |
| --- | --- |
| `VideoData` | 视频汇总指标数组 |

`VideoData[]` 字段:

| 字段 | 说明 |
| --- | --- |
| `Text` | 指标名 |
| `Value` | 指标值数组，实测为 `[当前值, 对比值, 变化率]` |

实测 `Text` 指标:

| 指标 | 说明 |
| --- | --- |
| `视频数` | 周期内视频数量 |
| `播放数` | 周期内播放数 |
| `点赞数` | 周期内点赞数 |
| `评论数` | 周期内评论数 |
| `分享数` | 周期内分享数 |

## 3. 达人详情页直播数据

- 接口: `GET /api/v1/blogger/BloggerOverview_Total_1`
- 脚本方法: `blogger_total(..., total_type=1, ...)`
- 用途: 获取达人详情页的直播汇总指标
- 请求参数同 `BloggerOverview_Total_2`

`Data` 字段:

| 字段 | 说明 |
| --- | --- |
| `LiveData` | 直播汇总指标数组 |

`LiveData[]` 字段:

| 字段 | 说明 |
| --- | --- |
| `Text` | 指标名 |
| `Value` | 指标值数组，实测为 `[当前值, 对比值, 变化率]` |

实测 `Text` 指标:

| 指标 | 说明 |
| --- | --- |
| `直播数` | 周期内直播数量 |
| `带货直播` | 周期内带货直播数量 |
| `推广商品` | 周期内推广商品数量 |
| `预估直播销量` | 周期内预估直播销量 |
| `预估直播销售额` | 周期内预估直播销售额 |

## 4. 达人带货数据

- 接口: `GET /api/v1/blogger/BloggerOverview_Total_3`
- 脚本方法: `blogger_total(..., total_type=3, ...)`
- 用途: 获取达人带货品类和品牌分布
- 请求参数同 `BloggerOverview_Total_2`

`Data` 字段:

| 字段 | 说明 |
| --- | --- |
| `LiveShopData_Cate` | 带货品类分布 |
| `LiveShopData_Brand` | 带货品牌分布 |

`LiveShopData_Cate[]` / `LiveShopData_Brand[]` 字段:

| 字段 | 说明 |
| --- | --- |
| `Name` | 品类名或品牌名 |
| `Samples` | 样本数，实测常为 `0` |
| `Ratio` | 具体带货金额，数值类型 |

## 5. 达人粉丝数和视频量化趋势

- 接口: `GET /api/v1/blogger/BloggerOverview_Total_4`
- 脚本方法: `blogger_total(..., total_type=4, period="custom", ...)`
- 用途: 获取粉丝数、增粉、视频互动/播放及增量趋势

请求参数:

| 字段 | 说明 |
| --- | --- |
| `period` | 周期，实测 `custom` |
| `beginDate` | 开始日期，如 `2026-04-28` |
| `endDate` | 结束日期，如 `2026-05-27` |
| `bloggerId` | 达人 ID |
| `_` | 毫秒时间戳 |
| `timestamp` | 签名时间戳 |
| `signature` | 签名 |

`Data` 字段:

| 字段 | 说明 |
| --- | --- |
| `Fans` | 当前粉丝数展示值 |
| `LstFansData` | 每日总粉丝数序列 |
| `LstIncFansData` | 每日增粉序列 |
| `LstVideoData` | 每日视频累计评论、点赞、播放序列 |
| `LstIncVideoData` | 每日视频新增评论、点赞、播放序列 |

趋势序列元素字段:

| 字段 | 说明 |
| --- | --- |
| `Date` | 日期，格式如 `2026-04-28` |
| `ShortTime` | 短日期，格式如 `04/28` |
| `Fans` | 粉丝数或增粉数；视频序列中可能为 `null` |
| `TotalComments` | 评论数；粉丝序列中可能为 `null` |
| `Likes` | 点赞数；粉丝序列中可能为 `null` |
| `TotalViews` | 播放数；粉丝序列中可能为 `null` |
| `FansStr` | 粉丝数展示值 |
| `TotalCommentsStr` | 评论数展示值 |
| `LikesStr` | 点赞数展示值 |
| `TotalViewsStr` | 播放数展示值 |

## 6. 达人近 10 场直播和视频数据

- 接口: `GET /api/v1/blogger/BloggerOverview`
- 脚本方法: `blogger_overview`
- 用途: 获取近 10 场直播、近 10 条视频和评论/词段数据

请求参数:

| 字段 | 说明 |
| --- | --- |
| `bloggerId` | 达人 ID |
| `_` | 毫秒时间戳 |
| `timestamp` | 签名时间戳 |
| `signature` | 签名 |

`Data` 字段:

| 字段 | 说明 |
| --- | --- |
| `Top10Lives` | 近 10 场直播指标汇总 |
| `Top10LiveDatas` | 近 10 场直播列表 |
| `Top10Lives2` | 第二组近 10 场直播指标汇总 |
| `Top10LiveDatas2` | 第二组近 10 场直播列表 |
| `Top10Video` | 近 10 条视频指标汇总 |
| `Top10VideoDatas` | 近 10 条视频列表 |
| `LiveSegments` | 直播评论/词段统计 |
| `VideoSegments` | 视频评论/词段统计 |

`Top10Lives[]` / `Top10Lives2[]` 字段:

| 字段 | 说明 |
| --- | --- |
| `Text` | 指标名 |
| `Value` | 指标展示值 |

实测直播指标:

| 指标 | 说明 |
| --- | --- |
| `场均人气峰值` | 近 10 场场均人气峰值 |
| `预估场均销量` | 近 10 场预估场均销量 |
| `预估场均销售额` | 近 10 场预估场均销售额 |

`Top10LiveDatas[]` / `Top10LiveDatas2[]` 字段:

| 字段 | 说明 |
| --- | --- |
| `Date` | 直播日期 |
| `ShortTime` | 短日期 |
| `DisplayWatchCount` | 人气峰值/观看指标原始值 |
| `DisplayWatchCountStr` | 人气峰值/观看指标展示值 |
| `TotalVolume` | 预估销量原始值 |
| `TotalVolumeStr` | 预估销量展示值 |
| `TotalPrice` | 预估销售额原始值 |
| `TotalPriceStr` | 预估销售额展示值 |
| `Title` | 直播标题 |
| `CoverImage` | 直播封面 |
| `LiveDetailUrl` | 直播详情跳转地址 |

`Top10Video[]` 字段:

| 字段 | 说明 |
| --- | --- |
| `Text` | 指标名 |
| `Value` | 指标展示值 |

实测视频指标:

| 指标 | 说明 |
| --- | --- |
| `平均播放` | 近 10 条平均播放 |
| `平均点赞` | 近 10 条平均点赞 |
| `平均评论` | 近 10 条平均评论 |

`Top10VideoDatas[]` 字段:

| 字段 | 说明 |
| --- | --- |
| `Date` | 视频发布日期 |
| `ShortTime` | 短日期 |
| `LikeCount` | 点赞数原始值 |
| `CommentCount` | 评论数原始值 |
| `ViewCount` | 播放数原始值 |
| `LikeCountStr` | 点赞数展示值 |
| `CommentCountStr` | 评论数展示值 |
| `ViewCountStr` | 播放数展示值 |
| `Title` | 视频标题 |
| `CoverImage` | 视频封面 |
| `PhotoId` | 快手视频/作品 ID |
| `BloggerId` | 达人 ID |

`LiveSegments[]` / `VideoSegments[]` 字段:

| 字段 | 说明 |
| --- | --- |
| `Segment` | 词段 |
| `Count` | 出现次数原始值 |
| `CountStr` | 出现次数展示值 |

## 全量采集与自动解析

全量采集搜索结果中的所有达人，并自动抓详情和解析:

```powershell
.venv\Scripts\python.exe scripts\ks_feigua_scraper.py --action full
```

实测当前账号返回 `TotalCount=1000`、`PermissionCount=500`。第 26 页开始接口返回空列表，并提示品牌版仅展示前 500 条结果；因此脚本按 `min(TotalCount, PermissionCount)` 作为可抓取总量，当前可抓取 25 页、500 个达人。

搜索排序会显著影响数据质量。实测:

| sort | 现象 |
| --- | --- |
| `0` | 返回大量低活跃小号，详情接口多数只有视频/直播汇总字段，带货、趋势、近 10 场列表大面积为空 |
| `5` | 返回高带货达人，第一页包括老葛、初瑞雪、蛋蛋等，详情接口信息更完整 |
| `9` / `10` | 也返回高带货/高销售额达人，但排序与 `5` 不同 |

脚本默认使用 `--sort 5`。如需复现原始默认搜索，可显式传 `--sort 0`。

不同排序结果会叠加到同一个断点里，按 `BloggerId` 去重合并，不会因为切换 `--sort` 清空已有达人和详情。断点会在 `search_runs` 中分别记录每组搜索参数的页码进度，并在达人字段 `_search_sources` 中记录来源排序、页码和页内排名。

可以依次运行多种排序来扩大有效达人覆盖:

```powershell
.venv\Scripts\python.exe scripts\ks_feigua_scraper.py --action full --sort 5
.venv\Scripts\python.exe scripts\ks_feigua_scraper.py --action full --sort 1
.venv\Scripts\python.exe scripts\ks_feigua_scraper.py --action full --sort 9
.venv\Scripts\python.exe scripts\ks_feigua_scraper.py --action full --sort 10
```

测试全量流程时可限制页数和详情数:

```powershell
.venv\Scripts\python.exe scripts\ks_feigua_scraper.py --action full --max-pages 1 --max-bloggers 3
```

断点文件:

```text
checkpoints/ks_feigua_full.json
```

断点内容:

| 字段 | 说明 |
| --- | --- |
| `search_pages` | 已抓取搜索页 |
| `bloggers` | 搜索得到的达人字典 |
| `detail_raw` | 已完成详情原始响应 |
| `detail_parsed` | 已完成详情解析数据 |
| `detail_failures` | 失败达人及错误原因 |
| `completed_pages` | 已完成搜索页码 |
| `total_count` | 搜索结果总数 |
| `permission_count` | 当前账号权限可查看数量 |

输出文件:

| 文件 | 说明 |
| --- | --- |
| `data/ks_feigua_<action>_raw_<timestamp>.json` | 单次动作原始响应 |
| `data/ks_feigua_<action>_parsed_<timestamp>.json` | 单次动作解析数据 |
| `data/ks_feigua_full_raw_<timestamp>.json` | 全量原始响应 |
| `data/ks_feigua_full_parsed_<timestamp>.json` | 全量解析数据 |

导出 CSV:

```powershell
.venv\Scripts\python.exe scripts\ks_feigua_scraper.py --action export-csv
```

CSV 输出目录:

```text
data/ks_feigua_csv_<timestamp>/
```

CSV 文件:

| 文件 | 说明 |
| --- | --- |
| `bloggers.csv` | 搜索接口达人列表字段 |
| `detail_summary.csv` | 每个达人的视频/直播汇总指标 |
| `commerce.csv` | 带货品类和品牌分布 |
| `fans_trend.csv` | 粉丝、增粉、视频播放/互动趋势明细 |
| `overview_metrics.csv` | 近 10 场直播/视频汇总指标 |
| `overview_lives.csv` | 近 10 场直播列表 |
| `overview_videos.csv` | 近 10 条视频列表 |
| `segments.csv` | 直播/视频词段统计 |
| `api_status.csv` | 每个达人、每个详情 API 的状态码和各 Data 字段数量，用于判断是解析缺失还是接口返回为空 |
| `raw_api_items.csv` | 每个达人、每个详情 API 的 Data 原始明细逐行展开，作为不丢字段的兜底导出 |

解析后的详情结构:

| 字段 | 来源 |
| --- | --- |
| `detail.metrics.video` | `BloggerOverview_Total_2.Data.VideoData` |
| `detail.metrics.live` | `BloggerOverview_Total_1.Data.LiveData` |
| `detail.commerce.categories` | `BloggerOverview_Total_3.Data.LiveShopData_Cate` |
| `detail.commerce.brands` | `BloggerOverview_Total_3.Data.LiveShopData_Brand` |
| `detail.fans_trend` | `BloggerOverview_Total_4.Data` |
| `detail.overview` | `BloggerOverview.Data` |
