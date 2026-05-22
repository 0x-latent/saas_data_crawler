# 飞瓜平台 API 文档

---

## 平台信息

- 网站: https://bz.feigua.cn
- 用途: B站UP主数据分析（第三方平台）
- 认证: 需要登录Cookie

---

## API 总览

| # | API | URL | 说明 | 状态 |
|---|---|---|---|---|
| 1 | UP主粉丝榜 | `/v1/Rank/GetFansRank` | 按粉丝数排名的UP主榜单，50页x20条=1000人 | 已梳理 |
| 2 | UP主详情 | `/V1/BloggerInfo/DetailNew` | 单个UP主完整数据（基本信息+视频均值+直播） | 已梳理 |
| 3 | MCN机构搜索 | `/v1/BloggerInfo/SearchMcn` | MCN机构列表，含旗下UP主数、粉丝量、分类占比 | 已梳理 |
| 4 | MCN旗下达人 | `/v1/BloggerInfo/SearchBlogger` | 按MCN名称查旗下UP主，含报价、数据、带货 | 已梳理 |

URL前缀: `https://bz.feigua.cn/`

---

## API 1: UP主粉丝榜

### 请求

```
GET https://bz.feigua.cn/v1/Rank/GetFansRank
```

### 参数

| 参数 | 类型 | 说明 | 示例 |
|---|---|---|---|
| `pageSize` | int | 每页条数 | 20 |
| `page` | int | 页码（从1开始） | 1 |
| `Cate` | int | 分类筛选，0=全部 | 0 |
| `BloggerFansType` | int | 粉丝类型筛选，0=全部 | 0 |
| `_` | int | 时间戳（防缓存） | 1779154261253 |

### 请求头

```
Cookie: （登录Cookie）
User-Agent: Mozilla/5.0 ...
Referer: https://bz.feigua.cn/
```

### 响应结构

```json
{
  "Code": 0,
  "Msg": "",
  "Data": {
    "TotalCount": 1000,
    "MemberLevel": 0,
    "PermissionCount": 0,
    "UpdateTime": "2026-05-19 05:00:00",
    "Stat": null,
    "Result": [ ... ]
  }
}
```

### 外层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `Code` | int | 状态码，0=成功 |
| `Msg` | str | 错误信息 |
| `Data.TotalCount` | int | 总记录数（固定1000） |
| `Data.MemberLevel` | int | 当前账号会员等级 |
| `Data.PermissionCount` | int | 权限数量 |
| `Data.UpdateTime` | str | 数据更新时间 |
| `Data.Stat` | null | 统计信息（当前为空） |
| `Data.Result` | list | UP主列表 |

### 分页信息

- 每页: 20条
- 总量: 1000条
- 总页数: 50页

### Result 字段明细（每条UP主记录）

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `RankNum` | int | 1 | 排名序号 |
| `Id` | int | 582 | 飞瓜内部ID，用于详情页路由 |
| `UId` | str | "321173469" | B站UID |
| `NickName` | str | "哔哩哔哩大会员" | UP主昵称 |
| `HeadImage` | str | "//imgs-bz.feigua.cn/..." | 头像URL（需补 https: 前缀） |
| `Sex` | int | 0 / 1 / 2 | 性别：0=未知, 1=男, 2=女 |
| `CateName` | str | "生活-日常" | 分区（格式: 一级分区-二级分区） |
| `SecondClassId` | int | 21 | 二级分区ID |
| `Score` | str | "1486.6" | 飞瓜评分（字符串格式） |
| `Fans` | str | "4936.2w" | 粉丝数（带单位展示用） |
| `FanCount` | int | 49361894 | 粉丝数（精确数值） |
| `LevelNumber` | int | 6 | UP主等级（B站等级） |
| `CertificationMark` | int | 1 / 2 | 认证标记：1=个人认证, 2=机构认证 |
| `OfficialTitle` | str | "哔哩哔哩大会员官方账号" | 官方认证头衔 |
| `OfficialVerifiedType` | str | "机构认证" / "个人认证" | 认证类型文字 |
| `UpDetailUlr` | str | "#/ContentV2/upDetail?id=582" | 详情页路由（SPA hash路由） |

共 **16个字段**。

### 榜单ID与详情ID的关系

- 榜单 `Result[].Id` = 详情接口的 `bloggerId` 参数
- 榜单 `Result[].UId` = B站UID = 详情 `BloggerInfo.MId`

---

## API 2: UP主详情

### 请求

```
GET https://bz.feigua.cn/V1/BloggerInfo/DetailNew
```

### 参数

| 参数 | 类型 | 说明 | 示例 |
|---|---|---|---|
| `bloggerId` | int | 飞瓜内部ID（即榜单的 `Id` 字段） | 953997 |
| `_` | int | 时间戳（防缓存） | 1779154461597 |

### 响应结构

```json
{
  "Code": 200,
  "Msg": "成功",
  "Data": {
    "ViewRight": true,
    "BloggerInfo": { ... },
    "BloggerVideo": { ... },
    "BloggerLive": { ... },
    "BrandInfo": { ... },
    "UpdateTime": "2026-05-19 05:53:30",
    "BloggerRankCount": 526,
    "BloggerVideoRankCount": 89,
    ...
  }
}
```

> 注意：榜单API成功码是 `Code: 0`，详情API成功码是 `Code: 200`，不一致。

### Data 外层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `ViewRight` | bool | 是否有查看权限 |
| `UpdateStatus` | int | 更新状态 |
| `IsFavorite` | bool | 是否已收藏 |
| `IsFocus` | bool | 是否已关注 |
| `UpdateTime` | str | 数据更新时间 |
| `BloggerRankCount` | int | UP主上榜次数 |
| `BloggerVideoRankCount` | int | 视频上榜次数 |
| `BrandInfo` | dict | 品牌合作信息（可能为空） |

### BloggerInfo（UP主基本信息，34个字段）

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `MId` | str | "604003146" | B站UID |
| `BloggerName` | str | "帕梅拉PamelaReif" | UP主昵称 |
| `AvatarUrl` | str | "https://i0.hdslb.com/..." | 头像URL（hdslb源） |
| `HeadUrl` | str | "//imgs-bz.feigua.cn/..." | 头像URL（飞瓜CDN） |
| `Sex` | int | 2 | 性别：0=未知, 1=男, 2=女 |
| `LevelNumber` | int | 6 | B站等级 |
| `VipType` | int | 2 | 大会员类型 |
| `TName` | str | "生活-日常" | 分区 |
| `Score` | str | "1628.1" | 飞瓜评分 |
| `Fans` | str | "1441.5w" | 粉丝数（带单位） |
| `RegionName` | str | "上海" | 所在地区 |
| `SecondRegionName` | str | "上海" | 所在城市 |
| `IpRegionName` | str | "广西" | IP归属地 |
| `OfficialVerified` | bool | true | 是否官方认证 |
| `OfficialRole` | int | 2 | 认证角色 |
| `CertificationMark` | int | 1 | 认证标记：1=个人, 2=机构 |
| `OfficialTitle` | str | "2024百大UP主..." | 认证头衔 |
| `McnName` | str | "格琳恩商贸" | MCN机构名称 |
| `Sign` | str | "帕梅拉 Pamela Reif 合作..." | 个性签名 |
| `Props` | str | "知名UP主认证、头部达人" | 标签/属性 |
| `URL` | str | "https://space.bilibili.com/..." | B站主页 |
| `LiveUrl` | str | "https://live.bilibili.com/..." | 直播间地址 |
| `HasLive` | bool | true | 是否有直播 |
| `HasGame` | bool | false | 是否有游戏内容 |
| `IsLiving` | bool | false | 是否正在直播 |
| `ChargeTotal` | int | 1615 | 充电总数 |
| `GuardNum` | int | 0 | 舰长数 |
| `HeartRankNum` | str | "10" | 心动排名 |
| `BloggerVideoTags` | list | ["帕梅拉", "用健身的方式打开新年"] | 视频标签 |
| `Email` | str/null | null | 联系邮箱 |
| `WeiXin` | str/null | null | 微信号 |
| `QQ` | str/null | null | QQ号 |
| `BaseId` | null | null | 基础ID |
| `Title` | null | null | 标题 |

### BloggerVideo（视频数据均值，8个字段）

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `AvgPlayCount` | str | "105.8w" | 平均播放量 |
| `AvgLikeCount` | str | "3.2w" | 平均点赞数 |
| `AvgCollectCount` | str | "8.7w" | 平均收藏数 |
| `AvgCoinCount` | str | "5798" | 平均投币数 |
| `AvgReplyCount` | str | "953" | 平均评论数 |
| `AvgDanmuCount` | str | "1947" | 平均弹幕数 |
| `InteractRate` | str | "12.41%" | 互动率 |
| `PlayFansRate` | str | "7.34%" | 播放粉丝比 |

> 注意：数值均为字符串格式，带"w"(万)后缀或"%"后缀，需解析。

### BloggerLive（直播数据均值，4个字段）

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `AvgDanmuCount` | str | "0" | 场均弹幕数 |
| `AvgMaxOnlineCount` | str | "0" | 场均最高在线 |
| `AvgGiftsValue` | str | "0" | 场均礼物价值 |
| `AvgWatchedCount` | str | "0" | 场均观看人数 |

### 详情API字段汇总

| 模块 | 字段数 | 说明 |
|---|---|---|
| Data外层 | 8 | 权限、状态、榜单计数 |
| BloggerInfo | 34 | 基本信息、认证、联系方式、标签 |
| BloggerVideo | 8 | 视频互动均值 |
| BloggerLive | 4 | 直播数据均值 |
| BrandInfo | 0+ | 品牌合作（可能为空） |
| **合计** | **~54** | |

---

## 两个API字段对比

### 重叠字段（榜单和详情都有）

| 榜单字段 | 详情字段 | 说明 |
|---|---|---|
| `UId` | `BloggerInfo.MId` | B站UID |
| `NickName` | `BloggerInfo.BloggerName` | 昵称 |
| `Sex` | `BloggerInfo.Sex` | 性别 |
| `Score` | `BloggerInfo.Score` | 飞瓜评分 |
| `Fans` | `BloggerInfo.Fans` | 粉丝数 |
| `LevelNumber` | `BloggerInfo.LevelNumber` | B站等级 |
| `CertificationMark` | `BloggerInfo.CertificationMark` | 认证标记 |
| `OfficialTitle` | `BloggerInfo.OfficialTitle` | 认证头衔 |
| `CateName` | `BloggerInfo.TName` | 分区 |
| `HeadImage` | `BloggerInfo.HeadUrl` | 头像 |

### 详情独有字段（榜单没有）

- 地区信息: `RegionName`, `SecondRegionName`, `IpRegionName`
- MCN: `McnName`
- 个性签名: `Sign`
- 联系方式: `Email`, `WeiXin`, `QQ`
- 视频标签: `BloggerVideoTags`
- B站主页/直播间: `URL`, `LiveUrl`
- 大会员: `VipType`
- 充电/舰长: `ChargeTotal`, `GuardNum`
- 视频均值: `AvgPlayCount`, `AvgLikeCount`, `AvgCollectCount` 等8项
- 直播均值: `AvgDanmuCount`, `AvgMaxOnlineCount` 等4项
- 上榜统计: `BloggerRankCount`, `BloggerVideoRankCount`

### 榜单独有字段（详情没有）

- `FanCount` — 精确粉丝数（int），详情只有带单位的字符串
- `RankNum` — 排名序号
- `SecondClassId` — 二级分区ID
- `OfficialVerifiedType` — 认证类型文字

---

## API 3: MCN机构搜索

### 请求

```
GET https://bz.feigua.cn/v1/BloggerInfo/SearchMcn
```

### 参数

| 参数 | 类型 | 说明 | 示例 |
|---|---|---|---|
| `pageSize` | int | 每页条数 | 10 |
| `Page` | int | 页码（从1开始，注意大写P） | 3 |
| `keyWord` | str | 搜索关键词，空=全部 | "" |
| `sort` | int | 排序方式，0=默认 | 0 |
| `Cate` | int | 分类筛选，0=全部 | 0 |
| `Fans` | int | 粉丝筛选，0=全部 | 0 |
| `BloggerCount` | int | UP主数筛选，0=全部 | 0 |
| `_` | int | 时间戳（防缓存） | 1779154747224 |

### 响应结构

```json
{
  "Code": 200,
  "Msg": "成功",
  "Data": {
    "TotalCount": 0,
    "MemberLevel": 0,
    "PermissionCount": 0,
    "UpdateTime": null,
    "Stat": null,
    "Result": [ ... ]
  }
}
```

> 注意：`TotalCount` 返回 0，但 Result 实际有数据，总数需通过翻页探测。

### Result 字段明细（每条MCN记录）

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `McnName` | str | "麻瓜联盟" | MCN机构名称 |
| `Fans` | str | "4863.2w" | 总粉丝数（带单位） |
| `BloggerCount` | int | 158 | 旗下UP主数量 |
| `Cate` | str | "生活 33.53%,音乐 26.34%" | 分类占比（逗号分隔） |
| `TopBlogger` | list | 见下方 | 头部UP主列表（Top3） |

### TopBlogger 子字段

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `BloggerId` | int | 13724977 | 飞瓜UP主ID（可用于详情API） |
| `BloggerName` | str | "腰细蘑菇" | UP主昵称 |
| `AvatarUrl` | str | "//imgs-bz.feigua.cn/..." | 头像URL |

### 特点

- 每页默认 10 条（与榜单的 20 条不同）
- TotalCount 不可靠（返回0），需翻页到空为止
- MCN记录不含机构ID，只有名称
- TopBlogger 的 BloggerId 可直接用于 API 2（DetailNew）查询

---

## API 4: MCN旗下达人搜索

### 请求

```
GET https://bz.feigua.cn/v1/BloggerInfo/SearchBlogger
```

### 参数

| 参数 | 类型 | 说明 | 示例 |
|---|---|---|---|
| `McnName` | str | MCN机构名称（URL编码） | "星河心合创意" |
| `pageSize` | int | 每页条数 | 10 |
| `Page` | int | 页码（从1开始） | 1 |
| `sort` | int | 排序方式，7=默认 | 7 |
| `Cate` | int | 分类筛选，0=全部 | 0 |
| `_` | int | 时间戳（防缓存） | 1779155758281 |

### 响应结构

```json
{
  "Code": 200,
  "Msg": "查询成功",
  "Data": {
    "list": [ ... ],
    "total": 146,
    "PermissionCount": 1000
  }
}
```

> 注意：此接口返回 `Data.list` + `Data.total`，与其他接口的 `Data.Result` + `Data.TotalCount` 不同。

### Data 外层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `total` | int | 该MCN旗下UP主总数（可靠） |
| `list` | list | UP主列表 |
| `PermissionCount` | int | 可查询总配额 |

### list 字段明细（每条UP主记录，44个字段）

#### 基本信息

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `BloggerId` | int | 52863 | 飞瓜内部ID（可用于DetailNew） |
| `Uid` | str | "26032219" | B站UID |
| `BloggerName` | str | "FoFTG" | UP主昵称 |
| `AvatarUrl` | str | "//imgs-bz.feigua.cn/..." | 头像URL |
| `Sex` | int | 1 | 性别：0=未知, 1=男, 2=女 |
| `LevelNumber` | int | 6 | B站等级 |
| `VipType` | str | "年度大会员" | 大会员类型（字符串） |
| `TName` | str | "游戏-单机游戏" | 分区 |
| `McnName` | str | "星河心合创意" | MCN机构名称 |
| `RegionName` | str | "河北" | 所在地区 |
| `SecondRegionName` | str | "唐山" | 所在城市 |
| `IpRegionName` | str | "河北" | IP归属地 |
| `Sign` | str | "..." | 个性签名 |
| `UpDetail` | str | "#/ContentV2/upDetail?id=52863" | 详情页路由 |

#### 认证与标签

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `OfficialVerified` | int | 1 | 是否认证（注意此处为int，非bool） |
| `OfficialTitle` | str | "bilibili 2022百大UP主..." | 认证头衔 |
| `FansBadge` | bool | true | 是否有粉丝勋章 |
| `Tag` | list | [{"TagName": "\<div\>MC\</div\>"},...] | 标签列表（含HTML标签） |
| `Score` | str | "1569.3" | 飞瓜评分 |

#### 核心数据

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `Fans` | str | "403.6w" | 粉丝数（带单位） |
| `ArchiveCount` | str | "4" | 近期投稿数 |
| `AvgPlayCount` | str | "234.3w" | 平均播放量 |
| `AvgLikeCount` | str | "19.5w" | 平均点赞数 |
| `AvgCollectCount` | str | "12.5w" | 平均收藏数 |
| `AvgReplyCount` | str | "822" | 平均评论数 |
| `AvgCoinCount` | str | "6.1w" | 平均投币数 |
| `InteractRatestr` | str | "16.70%" | 互动率 |
| `MainFansSex` | int | 1 | 主要粉丝性别：1=男, 2=女 |
| `MainFans` | str | "男粉居多" | 粉丝性别描述 |

#### 商业信息

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `HasAdPrice` | bool | true | 是否有广告报价 |
| `ImplantPrice` | str | "12.5w" | 植入报价（带单位） |
| `CustomPrice` | str | "25.0w" | 定制报价（带单位），"0"=未设置 |
| `ImplanttypeStr` | str | "品牌在前1/3露出、品牌露出30s以上" | 植入方式说明 |
| `CustomtypeStr` | str | "品牌在前1/3露出..." | 定制方式说明 |
| `PriceRight` | str | "视频前1/3+30s以上" | 报价权益 |

#### 带货信息

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `HasProduct` | bool | false | 是否有带货数据 |
| `MainProductCate` | str/null | "美食饮品" | 主要带货品类 |
| `ProductCateList` | list | [{"CateName":"美食饮品","Count":1,"Rate":1}] | 带货品类明细 |
| `TotalMainProductCount` | int | 1 | 带货品类总数 |

#### 其他

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `HasLive` | bool | true | 是否有直播 |
| `HasTel` | bool | true | 是否有联系方式 |
| `HasBrand` | bool | true | 是否有品牌合作 |
| `Video` | null | null | 视频数据（当前为空） |
| `Fav` | bool | false | 是否已收藏 |

### 与其他API的区别

此接口是**数据最丰富的列表接口**（44字段），相比：
- API 1（粉丝榜）只有 16 字段，无报价/带货
- API 2（详情）有 54 字段但需逐个查询
- API 4 = 列表级接口中字段最全，含报价+带货+互动率

### ProductCateList 子字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `CateName` | str | 品类名称 |
| `Count` | int | 带货数量 |
| `Rate` | float | 占比（0~1） |

---

## 已知问题

### 文本字体混淆

飞瓜对部分文本字段（NickName、OfficialTitle、CateName等）使用了**自定义字体加密**：
- API返回的原始文本中，部分汉字被替换为特殊Unicode码点
- 浏览器端通过加载自定义 @font-face 字体文件将这些码点渲染为正确汉字
- 直接通过API获取的文本会有部分乱码（如 `哔哩哔哩大会�` 末尾截断）

**影响的字段**: NickName, OfficialTitle, CateName 等文本字段
**不影响的字段**: 数值类字段（FanCount, Score, RankNum等）、ID类字段（UId, Id）

**解决方案**:
1. 浏览器模式抓取（Playwright），利用页面渲染后的文本
2. 解析自定义字体文件（woff/woff2），建立码点→汉字映射表
3. 用UId关联B站原始数据获取真实昵称

---

## 与火花平台对比

| 维度 | 火花平台 (huahuo) | 飞瓜 (feigua) |
|---|---|---|
| 性质 | B站官方商业平台 | 第三方数据分析平台 |
| 数据量 | ~10000 UP主 | 1000 UP主（榜单） |
| 认证方式 | Cookie | Cookie |
| 反爬措施 | 频率限制 + 验证码 | 字体混淆 + Cookie验证 |
| 列表字段 | ~80+ 字段（非常丰富） | 16字段（基础信息） |
| 详情页 | 需逐个访问5个API | 1个API，~54字段 |
| 请求方式 | REST API（直接JSON） | REST API（直接JSON） |

---

## API 字段梳理状态

- [x] API 1: UP主粉丝榜 — `/v1/Rank/GetFansRank`（16字段）
- [x] API 2: UP主详情 — `/V1/BloggerInfo/DetailNew`（~54字段）
- [x] API 3: MCN机构搜索 — `/v1/BloggerInfo/SearchMcn`（5字段+TopBlogger子表）
- [x] API 4: MCN旗下达人 — `/v1/BloggerInfo/SearchBlogger`（44字段）

**全部API已梳理完毕。**

---

## 抓取方案建议

### 推荐抓取路径

```
API 3 (MCN列表) → 遍历每个MCN → API 4 (旗下达人列表) → 可选: API 2 (详情补充)
```

理由：
1. API 4 是字段最丰富的列表接口（44字段），含报价+带货+互动率
2. API 3 提供所有MCN名称，作为 API 4 的入口
3. API 2 可选补充（充电数、舰长数、直播均值等API 4没有的字段）
4. API 1（粉丝榜）字段最少且仅1000人，可作为辅助

### 待解决

- [ ] 字体混淆解密方案（文本字段乱码）
- [ ] API 3 的 TotalCount 不可靠，需翻页探测MCN总数
- [ ] Cate / BloggerFansType / sort 等筛选参数的可选值
- [ ] 反爬策略评估（请求频率限制、Cookie有效期等）
