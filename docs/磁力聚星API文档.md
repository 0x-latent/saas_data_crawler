# 磁力聚星 API 调研记录

调研时间：2026-06-04

## 结论

- 用户给出的 `https://k.kuaishou.com/rest/web/star/list` 已触达，但当前直接 GET 返回 `result=11`，直接 POST 返回 `result=209`，没有返回达人字段。
- 前端主包未发现 `/rest/web/star/list` 调用；当前磁力聚星首页/榜单实际使用的是热点榜单接口：
  - `/rest/web/hot/homePage`
  - `/rest/web/hot/star/list`
- `/rest/web/hot/star/list` 必须带 UC 账号拦截器使用的 `ACCOUNT-ID` 请求头；不带时返回 `result=209`，响应会给出可选 `accountInfos` 和登录跳转 URL。
- 不同筛选模型会导致结果不同。已确认至少存在首页推荐榜单、完整热点榜单、活动/购物车匹配榜单等模型；同一达人池在不同 `hotId`、`starType`、`starTagIds` 下排序和返回数量不同。

## 鉴权与请求头

公共请求头：

```text
Cookie: <本地登录 cookie>
User-Agent: Mozilla/5.0 ...
Accept: application/json, text/plain, */*
Content-Type: application/json;charset=UTF-8
Origin: https://k.kuaishou.com
Referer: https://k.kuaishou.com/
```

完整热点榜单额外需要：

```text
ACCOUNT-ID: <账号主体 ID>
```

本次 209 响应中观察到两个账号主体：

| accountId | accountName | reviewStatus |
|---:|---|---:|
| 112250379 | 快手用户1764579652423 | 0 |
| 90363030 | 三九胃泰 | 2 |

脚本默认使用 `112250379`，可在 `config.yaml` 的 `magnetic_juxing.account_id` 或命令行 `--account-id` 覆盖。

## 已验证接口

### 前端达人详情页

样本：

```text
https://k.kuaishou.com/?penetrationJSON=...&pathSource=no_filter_video&__accountId__=90363030#/promotion/star/90779?openBy=user
```

可解析参数：

| 参数 | 值 | 用途 |
|---|---|---|
| `starId` | `90779` | 来自 hash 路由 `/promotion/star/90779` |
| `__accountId__` | `90363030` | 应作为请求头 `ACCOUNT-ID` |
| `pathSource` | `no_filter_video` | 详情来源场景，可随详情 payload 保存 |
| `penetrationJSON.sessionId` | `7059738ab6b5095539d5d3e019b36e28` | 前端穿透参数，用于来源/会话追踪 |

榜单接口没有返回直接的详情页 URL，详情页主要靠 `starId` 组装路由。

### 裸列表接口

```http
GET /rest/web/star/list
POST /rest/web/star/list
```

早期不带 `ACCOUNT-ID` 的探测结果：

| 请求 | 结果 |
|---|---|
| GET | `result=11`，`error_msg=请检查下网络连接是否正常` |
| POST `{}` | `result=209` |
| POST `{pageNum,pageSize}` | `result=209` |

带 `ACCOUNT-ID=90363030` 后，`POST /rest/web/star/list` 可以返回达人广场/直播达人列表，返回结构不是 `data.starList`，而是顶层：

- `result`
- `total`
- `currentPage`
- `starList[]`
- `recoTraceId`
- `messages`

这个接口不是靠某个特殊 header 区分“直播达人榜”。已观察到的必要 header 是 `Cookie` 和 `ACCOUNT-ID`，业务差异主要由 POST JSON body 决定，例如：

```json
{
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
  "pathSource": "no_filter_live"
}
```

说明：

- `ACCOUNT-ID`：账号主体/权限上下文，不决定榜单类型。
- `taskType`: 已观察直播达人榜为 `4`。
- `starOrderTag`: 排序指标，已观察直播达人榜为 `2`。
- `starOrderType`: 排序方向/类型，已观察直播达人榜为 `2`。
- `currentPage/pageSize`：分页。
- `pathSource`：页面来源场景，例如 `no_filter_live`、`no_filter_video`。
- `viewerCityPercentage`、`fansCityPercentage`、`starTagIds`、`pickList`、`advertiserPickList`: 筛选条件数组，空数组表示不限制。
- 其他筛选项应来自前端筛选面板的 request payload，例如内容形式、内容标签、行业、搜索词等。

本次用上述 payload 验证成功：

- `total=5000`
- 第 1 页 `starList=20`
- 输出样本：`data/magnetic_juxing_live_list_20260604_141029.json`

### 首页热点榜单

```http
POST /rest/web/hot/homePage
```

请求体：`{}`

返回：

- `result`: 成功时为 `1`
- `data[]`: 首页榜单组
- `data[].name`: 榜单组名
- `data[].fieldConfs`: 字段配置
- `data[].starList[]`: 达人列表

本次返回 3 组、45 条：

| 首页组 | 条数 |
|---|---:|
| 发展力表现榜 | 15 |
| 性价比表现榜 | 15 |
| 带货实力榜 | 15 |

### 完整热点榜单

```http
POST /rest/web/hot/star/list
```

请求体示例：

```json
{
  "hotId": 104,
  "starTagIds": [],
  "starType": 1,
  "userId": "5174709324"
}
```

返回：

- `result`: 成功时为 `1`
- `data.total`: 总条数
- `data.createTime`: 榜单生成时间戳
- `data.cartType`: 加购类型
- `data.starTags[]`: 可用标签筛选项
- `data.conf.description`: 榜单说明
- `data.conf.fieldConf[]`: 当前榜单展示/下载字段
- `data.starList[]`: 达人列表

已验证榜单：

| rank key | hotId | starType | 名称 | 本次 total |
|---|---:|---:|---|---:|
| `develop` | 104 | 1 | 发展力表现榜 / 涨粉黑马榜 | 50 |
| `cost_performance` | 5 | 1 | 性价比表现榜 | 30 |
| `live_sales` | 7 | 4 | 带货实力榜 | 30 |
| `spread` | 105 | 1 | 传播力表现榜 | 50 |
| `live_popularity` | 8 | 4 | 人气主播榜 | 30 |
| `fans` | 6 | 1 | 涨粉表现榜 | 需按业务确认 |

注意：`hotId=100`、`hotId=101` 可请求成功但本次 `total=0`，前端代码对这类视频播放/点赞榜有特殊分支，可能不是同一个列表模型。

### 达人基础资料

```http
POST /rest/web/star/match/starPage/baseInfo
```

最小可用请求体：

```json
{
  "starId": 90779,
  "starType": 1
}
```

也可附加详情页来源：

```json
{
  "starId": 90779,
  "starType": 1,
  "pathSource": "no_filter_video",
  "penetrationJSON": "{\"contentFormIdList\":[],\"contentTagIdList\":[],\"otherQueryField\":[],\"otherQueryFieldDetail\":[],\"queryText\":\"\",\"industry\":[],\"sessionId\":\"7059738ab6b5095539d5d3e019b36e28\"}"
}
```

本次验证：

- 只传 `starId` 返回 `result=11`。
- 传 `starId + starType` 返回 `result=1`。
- `pathSource`、`penetrationJSON` 不是基础资料必需参数，但建议保留，便于追踪来源模型。

返回字段示例：

| 字段 | 说明 |
|---|---|
| `userId`, `starId`, `profileId`, `profileUrl` | 快手用户和主页信息 |
| `headUrl`, `name`, `gender`, `address`, `introduction` | 基础资料 |
| `fansNumber`, `fansIncreaseRate` | 粉丝量和涨粉率 |
| `mcnId`, `mcnName` | MCN 信息 |
| `contentTypeTag`, `contentFormTag` | 内容类型/形式标签 |
| `identify`, `styleDetail`, `platformTargetIdentityInfo` | 达人身份和风格 |
| `businessReportIndustries` | 商单行业分布 |
| `priceShowInfo[]` | 报价 |
| `active`, `liveActive`, `putStatus`, `liveStatus` | 可投放/直播状态 |
| `starRiskLevel`, `starCreditScore` | 风险/信用字段 |

### 视频代表作品

```http
POST /rest/web/post/video/representative/works/info/list
```

最小可用请求体：

```json
{
  "starId": 90779
}
```

浏览器 Network 中观察到的请求体：

```json
{
  "starId": 196223,
  "nature": false
}
```

`nature` 用于控制作品口径。当前脚本默认发送 `nature=false`，也支持通过 `--works-nature true|false|omit` 调整。

本次验证返回 `data.detailList` 22 条。字段示例：

| 字段 | 说明 |
|---|---|
| `photoId` | 作品 ID |
| `coverUrl`, `url`, `webpUrl` | 封面、视频、短视频页 |
| `caption` | 标题/文案 |
| `likeCnt`, `viewCnt`, `forwardCnt`, `commentCnt` | 互动指标 |
| `releaseTimeMillis` | 发布时间 |
| `business`, `productName`, `containsPaid` | 商业/植入信息 |
| `worksRankType` | 作品榜单类型 |
| `qualityHot`, `quantityHot`, `qualityAndQuantityHot` | 热门标记 |
| `firstIndustryId`, `firstIndustryName` | 行业 |
| `spuReport` | 商品报告，可能为空 |

### 粉丝画像 / 观众画像

```http
POST /rest/web/star/listPortrait
```

粉丝画像和观众画像使用同一个接口。最小可用请求体：

```json
{
  "starId": 90779,
  "starType": 1
}
```

本次验证：

- 只传 `starId` 返回 `result=11`。
- 传 `starId + starType` 返回 `result=1`。
- 增加 `portraitType/type/userType/dataType` 不改变返回结构；接口一次返回两套画像。

返回结构：

- `data.fansPortrait`: 粉丝画像
- `data.viewerPortrait`: 观众画像

画像组字段示例：

| 画像组 | 说明 |
|---|---|
| `sexPercentage` | 性别占比 |
| `agePercentage` | 年龄占比 |
| `areaPercentage` / `areaTopWithRadio` | 省份/区域分布 |
| `cityLevelPercentage` | 城市分布 |
| `cityPercentage` | 城市线级 |
| `mobileBrandPercentage` | 手机品牌 |
| `mobilePricePercentage` | 手机价格段 |
| `activityPercentage` | 活跃度，可能为空 |
| `mobilePercentage` | 设备分布，可能为空 |

每个分布项通常包含：

| 字段 | 说明 |
|---|---|
| `label` | 标签 |
| `value` | 占比 |
| `tgi` | TGI 指数 |

本地脚本会把画像展开为长表：`_portrait` 为 `fansPortrait` 或 `viewerPortrait`，`_group` 为分布组名。

### 履约表现

```http
POST /rest/web/post/video/business/report/get
```

本次用 `starId`、`starType`、`userId`、分页等组合探测，均返回：

```json
{
  "result": -1,
  "error_msg": "参数校验失败，不在取值范围内"
}
```

这个接口需要从浏览器 Network 里捕获真实 Request Payload 后再接入。它很可能不是只按 `starId` 查询，可能还需要作品、行业、时间范围或任务/履约类型参数。

### 视频作品统计

```http
POST /rest/web/post/video/works/statistics/get
```

本次仅用 `starId`、`photoId`、`photoIdList`、`postId` 等常见组合探测，均返回：

```json
{
  "result": -1,
  "error_msg": "参数校验失败，不在取值范围内,参数校验失败，不在取值范围内"
}
```

该接口仍需从浏览器 Network 中捕获真实 payload 后再接入；当前不应阻塞 `baseInfo` 和代表作品采集。

## 达人字段

`starList[]` 首条样本观察到字段：

| 字段 | 说明 |
|---|---|
| `newRank`, `oldRank` | 新/旧排名 |
| `name`, `starId`, `userId`, `gender` | 达人基础信息 |
| `fansNumber`, `headUrl` | 粉丝数、头像 |
| `mmuStarTagStr`, `starTagStr`, `starTagIds` | 标签 |
| `photoExpectPlay`, `photoExpectCpm` | 视频预期播放、预期 CPM |
| `liveExpectCpm`, `liveExpectViewer`, `liveMaxViewer` | 直播预期指标 |
| `photoInteractionRate`, `liveInteractionRate` | 视频/直播互动率 |
| `spreadScore`, `conversionScore`, `costEffectiveScore`, `fanGrowScore`, `sellGoodsScore`, `popularScore` | 模型评分 |
| `videoDevelopIndex`, `videoSpreadingIndex`, `videoPerformancePriceIndex`, `videoStarIndex` | 视频相关指数 |
| `fansIncreaseNum`, `sexPercentage` | 涨粉量、男女粉比例 |
| `pplayMedianData`, `bplayMedianData`, `pcompletePlayRateData` | 播放/完播相关统计 |
| `rankingTimes`, `rankingRange` | 上榜次数/区间 |
| `priceShowInfo[]` | 报价明细 |
| `starRiskLevel[]` | 风险等级 |
| `platformTargetIdentityInfo` | 平台身份信息 |
| `active`, `liveActive`, `putStatus`, `liveStatus` | 可用/投放/直播状态 |
| `extData` | JSON 字符串，常含 `hotName`、`sessionId` |

不同榜单的 `fieldConf` 不同。例如：

- `develop`: 粉丝数、涨粉指数、涨粉量、预期播放量、预期 CPM、视频播放中位数、互动率、男女粉比例、上榜次数。
- `cost_performance`: 粉丝数、预期播放量、预期 CPM、互动率、性价比指数。
- `live_sales`: 粉丝数、预期观看人数、带货表现分。

## 筛选模型差异

已观察到的差异来源：

1. `hotId`: 决定榜单模型，例如发展力、性价比、带货、传播力、人气主播。
2. `starType`: `1` 偏视频达人，`4` 偏直播达人。
3. `starTagIds`: 垂类标签筛选，接口返回 `starTags` 作为可选项。
4. 首页模型：`/hot/homePage` 返回每组 15 条，更像首页精选/推荐，不等于完整榜单。
5. 账号主体：不带 `ACCOUNT-ID` 会触发 209，账号主体可能影响权限、可见字段、报价或加购状态。
6. 活动/购物车模型：前端还存在 `/rest/web/star/match/cart/star/list`，用于活动详情的“更多面孔”，请求参数是 `activityId/currentPage/pageSize`，和热点榜单不是同一模型。

因此后续如果要做稳定采集，需要把榜单模型参数作为抓取维度保存，至少记录：`endpoint`、`account_id`、`hotId`、`starType`、`starTagIds`、`rank_name`、`createTime`。

## 本地脚本

新增脚本：

```powershell
.\.venv\Scripts\python.exe -m scripts.magnetic_juxing_scraper --action probe
.\.venv\Scripts\python.exe -m scripts.magnetic_juxing_scraper --action hot-home
.\.venv\Scripts\python.exe -m scripts.magnetic_juxing_scraper --action hot-list --hot-ranks develop,cost_performance,live_sales
.\.venv\Scripts\python.exe -m scripts.magnetic_juxing_scraper --action hot-list --hot-ranks all
.\.venv\Scripts\python.exe -m scripts.magnetic_juxing_scraper --action live-list --account-id 90363030 --max-pages 1
.\.venv\Scripts\python.exe -m scripts.magnetic_juxing_scraper --action detail --star-id 90779 --star-type 1 --account-id 90363030 --path-source no_filter_video
```

代表作品口径可选：

```powershell
.\.venv\Scripts\python.exe -m scripts.magnetic_juxing_scraper --action detail --star-id 196223 --star-type 1 --account-id 90363030 --path-source no_filter_video --works-nature false
```

输出：

- raw JSON: `data/magnetic_juxing_*.json`
- 扁平 CSV: `data/magnetic_juxing_*_items_*.csv`

本次验证产物：

- `data/magnetic_juxing_probe_20260604_124554.json`
- `data/magnetic_juxing_hot_home_20260604_125018.json`
- `data/magnetic_juxing_hot_home_items_20260604_125018.csv`
- `data/magnetic_juxing_hot_list_20260604_125012.json`
- `data/magnetic_juxing_hot_list_items_20260604_125012.csv`
- `data/magnetic_juxing_detail_20260604_131117.json`
- `data/magnetic_juxing_detail_base_20260604_131117.csv`
- `data/magnetic_juxing_detail_works_20260604_131117.csv`
- `data/magnetic_juxing_detail_20260604_140444.json`
- `data/magnetic_juxing_detail_portrait_20260604_140444.csv`
- `data/magnetic_juxing_live_list_20260604_141029.json`
- `data/magnetic_juxing_live_list_items_20260604_141029.csv`

## SQLite first workflow

当前建议先把采集结果统一落到 SQLite，后续再按业务口径导出 CSV：

```powershell
.\.venv\Scripts\python.exe -m scripts.magnetic_juxing_scraper --action interactive --account-id 90363030
```

交互菜单会提供：

1. `smoke test`: 5 页直播榜 + 全部热点榜 + 100 个详情。
2. `daily discovery`: 50 页直播榜 + 全部热点榜，不抓详情。
3. `daily detail batch`: 20 页直播榜 + 全部热点榜 + 200 个详情。
4. `large batch`: 100 页直播榜 + 全部热点榜 + 500 个详情。
5. `deep discovery only`: 250 页直播榜 + 全部热点榜，不抓详情。
6. `custom`: 手动输入榜单、页数、详情数量和刷新间隔。

也可以直接传参数运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.magnetic_juxing_scraper --action full --account-id 90363030 --hot-ranks all --max-pages 1 --detail-limit 50
```

默认输出：

```text
data/magnetic_juxing.sqlite
```

主要表：

| table | purpose |
|---|---|
| `v_star_overview` | 日常优先看：达人一行一条，带来源数、详情时间、作品数、画像组数 |
| `v_star_source_latest` | 日常优先看：达人最新来源、榜单、页码、排序模型 |
| `v_run_summary` | 日常优先看：每次采集任务的汇总 |
| `v_star_work_latest` | 日常优先看：代表作品明细，已带达人名称 |
| `v_star_portrait_latest` | 日常优先看：粉丝/观众画像长表，已带达人名称 |
| `runs` | 每次采集任务的参数、状态、起止时间 |
| `raw_api_response` | 每个接口原始响应，便于回放和补字段 |
| `dim_star` | 达人主表，按 `star_id` 去重 |
| `fact_star_source` | 达人来自哪个榜单/列表/页码/排序模型 |
| `star_detail_base` | 达人详情页基础资料 |
| `star_work` | 代表作品明细 |
| `star_portrait` | 粉丝画像和观众画像的长表展开 |

查看当前库里有哪些表/视图以及行数：

```powershell
.\.venv\Scripts\python.exe -m scripts.magnetic_juxing_scraper --action db-summary
```

建议使用顺序：

1. 先看 `v_star_overview`，它是达人总览。
2. 再看 `v_star_source_latest`，确认达人来自哪个榜单/筛选模型。
3. 需要作品时看 `v_star_work_latest`。
4. 需要画像时看 `v_star_portrait_latest`。
5. 只有排查接口、补字段、还原 payload 时才看 `raw_api_response`。

推荐策略：

1. 高频任务只跑榜单/列表，设置 `--skip-details`，用于发现新达人和更新排名来源。
2. 详情页低频增量补采，默认 `--detail-refresh-days 7`，避免每天重复抓同一批达人详情。
3. `--detail-limit 0` 表示补齐所有到期达人；常规运行建议设置上限，控制接口压力。
4. `raw_api_response` 必须保留，因为磁力聚星不同筛选模型会返回不同字段，后续补字段可以直接从原始 JSON 回填。
