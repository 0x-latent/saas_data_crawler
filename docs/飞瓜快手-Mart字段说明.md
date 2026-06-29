# 飞瓜快手 Mart 数据说明

本文档说明本地仪表盘生成的清洗分析表。当前参考输出目录:

```text
data/ks_feigua_dashboard_20260601_115052/mart/
```

这些表由 `scripts/ks_feigua_build_dashboard.py` 从 `data/ks_feigua_csv_*` 清洗生成，和离线 HTML 看板使用同一套口径。

## 目录结构

```text
mart/
  mart_blogger_profile.csv
  fact_blogger_trend.csv
  fact_commerce.csv
  fact_recent_lives.csv
  fact_recent_videos.csv
  fact_segments.csv
  quality_report.csv
```

## 表关系

核心主键:

```text
blogger_id
```

推荐使用方式:

- `mart_blogger_profile.csv`: 主分析表，一行一个达人。
- `quality_report.csv`: 数据覆盖率和可用性检查，一行一个达人。
- `fact_*.csv`: 明细事实表，需要看趋势、带货、直播、视频、词段时再按 `blogger_id` 关联。

不要把所有 `fact_*.csv` 直接横向 join 到主表，否则会因为一对多关系产生重复膨胀。

## 1. mart_blogger_profile.csv

粒度: 一行一个达人。

当前行数: `1387`

用途:

- 达人筛选
- 排行榜
- 主宽表分析
- 和其他事实表关联

字段说明:

| 字段                      | 说明                 |
| ----------------------- | ------------------ |
| `blogger_id`            | 飞瓜快手达人 ID，主键       |
| `nick`                  | 达人昵称               |
| `kwaiId`                | 快手号                |
| `fansText`              | 粉丝数原始展示值           |
| `fans`                  | 粉丝数数值化             |
| `score`                 | 飞瓜评分数值化            |
| `jumpUrl`               | 达人详情跳转地址           |
| `sourceSorts`           | 达人来自哪些搜索 sort，逗号分隔 |
| `sourceBestRank`        | 达人在搜索来源中的最好排名      |
| `videoPlays`            | 周期内视频播放数           |
| `videoLikes`            | 周期内视频点赞数           |
| `videoComments`         | 周期内视频评论数           |
| `videoShares`           | 周期内视频分享数           |
| `liveCount`             | 周期内直播数             |
| `liveSalesAmount`       | 周期内预估直播销售额         |
| `liveSalesVolume`       | 周期内预估直播销量          |
| `commerceAmount`        | 带货品类金额汇总           |
| `topCategory`           | 金额最高的带货品类          |
| `topCategoryAmount`     | Top 品类金额           |
| `topBrand`              | 金额最高的带货品牌          |
| `topBrandAmount`        | Top 品牌金额           |
| `fansStart`             | 趋势期初粉丝数            |
| `fansEnd`               | 趋势期末粉丝数            |
| `fansGrowth`            | 趋势期粉丝增长            |
| `viewsGrowth`           | 趋势期播放增量汇总          |
| `likesGrowth`           | 趋势期点赞增量汇总          |
| `commentsGrowth`        | 趋势期评论增量汇总          |
| `recentLiveCount`       | 近 10 直播条数          |
| `recentLiveSalesAmount` | 近 10 直播预估销售额汇总     |
| `recentLiveVolume`      | 近 10 直播销量汇总        |
| `recentVideoCount`      | 近 10 视频条数          |
| `recentVideoViews`      | 近 10 视频播放汇总        |
| `recentVideoLikes`      | 近 10 视频点赞汇总        |
| `recentVideoComments`   | 近 10 视频评论汇总        |
| `hasDetail`             | 是否有详情汇总数据          |
| `hasCommerce`           | 是否有带货明细            |
| `hasTrend`              | 是否有趋势数据            |
| `hasLives`              | 是否有近 10 直播         |
| `hasVideos`             | 是否有近 10 视频         |
| `hasSegments`           | 是否有词段数据            |

## 2. fact_blogger_trend.csv

粒度: `blogger_id + Date`

当前行数: `180754`

用途:

- 粉丝趋势折线图
- 播放/点赞/评论增长分析
- 增长异常日期识别

字段说明:

| 字段           | 说明     |
| ------------ | ------ |
| `blogger_id` | 达人 ID  |
| `Nick`       | 达人昵称   |
| `Date`       | 日期     |
| `fans`       | 当日总粉丝数 |
| `incFans`    | 当日增粉   |
| `views`      | 当日播放增量 |
| `likes`      | 当日点赞增量 |
| `comments`   | 当日评论增量 |

## 3. fact_commerce.csv

粒度: `blogger_id + type + rank`

当前行数: `7597`

用途:

- 达人带货品类分析
- 达人带货品牌分析
- 品类/品牌 TopN

字段说明:

| 字段           | 说明                           |
| ------------ | ---------------------------- |
| `blogger_id` | 达人 ID                        |
| `Nick`       | 达人昵称                         |
| `type`       | `category` 表示品类，`brand` 表示品牌 |
| `rank`       | 在该达人该类型下的金额排名                |
| `name`       | 品类名或品牌名                      |
| `amount`     | 金额数值                         |
| `amountText` | 金额原始展示值                      |

## 4. fact_recent_lives.csv

粒度: `blogger_id + rank`

当前行数: `8120`

用途:

- 近 10 场直播表现
- 直播销售额、销量、人气峰值分析

字段说明:

| 字段                      | 说明                                 |
| ----------------------- | ---------------------------------- |
| `blogger_id`            | 达人 ID                              |
| `Nick`                  | 达人昵称                               |
| `rank`                  | 该达人直播记录排名                          |
| `KwaiId`                | 快手号                                |
| `SearchFans`            | 搜索列表粉丝展示值                          |
| `BloggerJumpUrl`        | 达人跳转地址                             |
| `group`                 | 来源分组，如 `live_rank` / `live_rank_2` |
| `Date`                  | 直播日期                               |
| `ShortTime`             | 短日期                                |
| `DisplayWatchCount`     | 人气峰值原始值                            |
| `DisplayWatchCountStr`  | 人气峰值展示值                            |
| `TotalVolume`           | 销量原始值                              |
| `TotalVolumeStr`        | 销量展示值                              |
| `TotalPrice`            | 销售额原始值                             |
| `TotalPriceStr`         | 销售额展示值                             |
| `Title`                 | 直播标题                               |
| `CoverImage`            | 封面图                                |
| `LiveDetailUrl`         | 直播详情跳转                             |
| `DisplayWatchCount_num` | 人气峰值数值化                            |
| `TotalVolume_num`       | 销量数值化                              |
| `TotalPrice_num`        | 销售额数值化                             |

## 5. fact_recent_videos.csv

粒度: `blogger_id + rank`

当前行数: `9217`

用途:

- 近 10 视频表现
- 播放、点赞、评论分析

字段说明:

| 字段                 | 说明        |
| ------------------ | --------- |
| `blogger_id`       | 达人 ID     |
| `Nick`             | 达人昵称      |
| `rank`             | 该达人视频记录排名 |
| `KwaiId`           | 快手号       |
| `SearchFans`       | 搜索列表粉丝展示值 |
| `BloggerJumpUrl`   | 达人跳转地址    |
| `Date`             | 视频日期      |
| `ShortTime`        | 短日期       |
| `LikeCount`        | 点赞原始值     |
| `CommentCount`     | 评论原始值     |
| `ViewCount`        | 播放原始值     |
| `LikeCountStr`     | 点赞展示值     |
| `CommentCountStr`  | 评论展示值     |
| `ViewCountStr`     | 播放展示值     |
| `Title`            | 视频标题      |
| `CoverImage`       | 视频封面      |
| `PhotoId`          | 作品 ID     |
| `BloggerId`        | 原始达人 ID   |
| `LikeCount_num`    | 点赞数值化     |
| `CommentCount_num` | 评论数值化     |
| `ViewCount_num`    | 播放数值化     |

## 6. fact_segments.csv

粒度: `blogger_id + group + rank`

当前行数: `53944`

用途:

- 评论/词段分析
- 高频词排行
- 达人内容标签初筛

字段说明:

| 字段           | 说明                                 |
| ------------ | ---------------------------------- |
| `blogger_id` | 达人 ID                              |
| `Nick`       | 达人昵称                               |
| `rank`       | 词段排名                               |
| `group`      | `live_segments` 或 `video_segments` |
| `segment`    | 词段                                 |
| `count`      | 出现次数数值                             |
| `countText`  | 出现次数展示值                            |

## 7. quality_report.csv

粒度: 一行一个达人。

当前行数: `1387`

用途:

- 判断数据缺失原因
- 筛选可分析达人
- 生成覆盖率统计

字段说明:

| 字段             | 说明         |
| -------------- | ---------- |
| `blogger_id`   | 达人 ID      |
| `Nick`         | 达人昵称       |
| `hasDetail`    | 是否有详情数据    |
| `hasCommerce`  | 是否有带货明细    |
| `hasTrend`     | 是否有趋势数据    |
| `hasLives`     | 是否有近 10 直播 |
| `hasVideos`    | 是否有近 10 视频 |
| `hasSegments`  | 是否有词段数据    |
| `commerceRows` | 该达人带货明细行数  |
| `trendRows`    | 该达人趋势日期行数  |
| `liveRows`     | 该达人直播明细行数  |
| `videoRows`    | 该达人视频明细行数  |
| `segmentRows`  | 该达人词段明细行数  |

## 数值清洗规则

脚本会将展示型数值转成分析用数值:

| 原始值       | 清洗结果        |
| --------- | -----------:|
| `1.9w`    | `19000`     |
| `1.50亿`   | `150000000` |
| `9999.0w` | `99990000`  |
| `-`       | 空值          |
| 空字符串      | 空值          |

说明:

- 原始展示值通常仍保留在 `*Text`、`*Str` 或原字段中。
- 数值化字段通常是纯数字字段或 `_num` 后缀字段。
- 金额字段单位按接口展示值转换，不额外做币种换算。

## 推荐分析入口

常规分析优先使用:

```text
mart_blogger_profile.csv
```

常见筛选:

- `hasCommerce = True`: 有带货数据达人
- `hasTrend = True`: 有趋势数据达人
- `hasVideos = True`: 有近 10 视频达人
- `hasLives = True`: 有近 10 直播达人

需要看明细时再关联:

- 带货分析: `fact_commerce.csv`
- 增长分析: `fact_blogger_trend.csv`
- 直播分析: `fact_recent_lives.csv`
- 视频分析: `fact_recent_videos.csv`
- 词段分析: `fact_segments.csv`

# 
