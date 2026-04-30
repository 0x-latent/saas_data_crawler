# 火花平台 API 文档

---

## API 总览

| # | API | URL | 请求方式 | 说明 |
|---|---|---|---|---|
| 1 | UP主广场列表 | `/advertiser/upper_square/search` | 按页批量(20条/页) | 核心指标、报价、效果、带货、直播 |
| 2 | UP主详情画像 | `/advertiser/portrait` | 逐个UP主 | 完整画像、分布数据、互动均值 |
| 3 | 投稿趋势 | `/advertiser/portrait/draft/trend_extra` | 逐个UP主 x4类型 | 每条视频的播放/点赞/评论/弹幕 |
| 4 | 粉丝趋势 | `/advertiser/portrait/attention_user/trend_extra` | 逐个UP主 x2类型 | 粉丝总量/增量每日数据 |
| 5 | 代表作品 | `/advertiser/representative/list` | 逐个UP主 x2类型 | 个人/商业代表作品明细 |

URL前缀均为: `https://huahuo.bilibili.com/commercialorder/api/web_api/v1`

---

## API 字段重叠与独有分析

### 两者都有的字段（33个）

以下字段在 API1(search) 和 API2(portrait) 中**都能获取到**：

| 字段 | 说明 |
|---|---|
| `nickname`, `upper_mid`, `mapping_id` | 基本标识 |
| `gender_desc`, `region_desc`, `second_region_desc` | 性别、地区 |
| `partition_id`, `partition_name`, `second_partition_id`, `second_partition_name` | 分区 |
| `mcn_id`, `mcn_company_name` | MCN |
| `head_img`, `upper_type` | 头像、类型 |
| `fans_num`, `average_play_cnt` | 粉丝数、播放量中位数 |
| `median_play_30d`, `median_play_vt` | 30天播放中位数 |
| `app_vv_percent`, `pc_vv_percent` | 播放端占比 |
| `active_status`, `is_live`, `is_new_upper`, `is_new_enter`, `is_treasure_up` | 状态标记 |
| `is_collected`, `prohibit_take_order` | 收藏、禁单 |
| `tags`, `character_tag`, `occupation_tag`, `spark_tag`, `state_types` | 标签 |
| `up_popular` | 人气 |

### API1(search) 独有字段（90个）

以下字段**只能从列表接口获取**，portrait 中没有：

**核心指标:**
| 字段 | 说明 |
|---|---|
| `fans_inc` | 涨粉量 |
| `fans_inc_rate` | 涨粉率(%) |
| `interactive_rate` | 互动率 |
| `synthetical_score` | 综合评分 |
| `magnetic_value` | 磁力值 |
| `dynamic_score` | 动态评分 |
| `hot_avid_rate` | 热门稿件率 |
| `hot_avid_cnt_180d` | 180天热门稿件数 |
| `avid_cnt_30d` / `avid_cnt_90d` / `avid_cnt_180d` | 近30/90/180天投稿数 |
| `draft_duration` | 投稿时长 |
| `commercial_avid_cnt` | 商业视频数 |
| `play_median` | 播放中位数 |
| `estimated_play` | 预估播放量 |
| `estimated_cost` | 预估花费 |
| `is_boosting` | 是否助推中 |
| `is_high_potential` | 是否高潜UP主 |

**报价:**
| 字段 | 说明 |
|---|---|
| `price_infos` | 报价列表(植入/定制/直发/转发) |
| `brand_embedding_platform_price_cpm` | 品牌植入CPM |
| `content_customized_platform_price_cpm` | 内容定制CPM |
| `cpm` / `cpc` / `cpe` | 效果指标 |
| `blue_url_ctr` / `blue_url_click_cost` | 蓝链数据 |

**效果数据 (up_draft_data_view):**
| 字段 | 说明 |
|---|---|
| `play_median_all_7d/15d/30d` | 全部流量播放中位数(7/15/30天) |
| `play_median_nature_7d/15d/30d` | 自然流量播放中位数(7/15/30天) |
| `cpm_all_7d/15d/30d` | 全部流量CPM(7/15/30天) |
| `cpm_nature_7d/15d/30d` | 自然流量CPM(7/15/30天) |
| `cpc_all_7d/15d/30d` | 全部流量CPC(7/15/30天) |
| `cpc_nature_7d/15d/30d` | 自然流量CPC(7/15/30天) |
| `cpe_all_7d/30d` / `cpe_nature_7d/30d` | CPE |

**画像摘要 (upper_user_portrait_info):**
| 字段 | 说明 |
|---|---|
| `sax_distributions_1` / `sax_distributions_0` | 关注用户男/女占比(单个数值) |
| `age_distributions_0_17/18_24/25_30/30_999` | 关注用户年龄占比 |
| `age_distributions_audience_0_17/18_24/25_30/30_999` | 观看用户年龄占比 |
| `fans_vv_distributions_audience` | 观看用户中粉丝占比(单个数值) |

**带货数据 (goods_up_data_view):**
| 字段 | 说明 |
|---|---|
| `goods_up_level` | 带货等级 |
| `goods_category` | 带货品类 |
| `goods_avg_price` / `goods_avg_price_desc` | 带货均价 |
| `goods_gpm` / `goods_gpm_desc` | 带货GPM |
| `all_click_rate` / `all_click_rate_desc` | 全部点击率 |
| `comment_all_click_rate` / `comment_all_click_rate_desc` | 评论区点击率 |

**直播数据:**
| 字段 | 说明 |
|---|---|
| `live_audience_h_avg_30d` | 直播场均观看人数 |
| `live_danmu_h_avg_30d` | 直播场均弹幕数 |
| `live_level` / `popularity` | 直播等级/人气 |
| `live_gmv_avg_desc` | GMV均值说明 |
| `live_per_viewing_time` | 人均观看时长 |
| `live_good_price_avg` | 带货均价 |
| `live_sale_amount_90day` | 90天带货金额 |
| `live_good_category` | 带货品类 |
| `goods_permission` | 带货权限 |

**DMP人群:**
| 字段 | 说明 |
|---|---|
| `dmp_fans_rate` / `dmp_cover_rate` / `dmp_cover_count` | DMP匹配数据 |

**其他:**
| 字段 | 说明 |
|---|---|
| `special_tags` / `cooperation_mode_tags` / `high_convert_tags` | 特殊标签 |
| `representative_info_view` | 代表作封面 |
| `video_right_tag` | 视频权益标签 |
| `app_vv_percent_desc` / `pc_vv_percent_desc` | 播放占比说明 |
| 以及一批 `huahuo_*`、`dmp_pkg_*`、`live_guild_*` 等字段 | |

### API2(portrait) 独有字段（58个）

以下字段**只能从详情画像接口获取**，search 中没有：

**互动均值:**
| 字段 | 说明 |
|---|---|
| `average_comment_cnt` | 平均评论数 |
| `average_like_cnt` | 平均点赞数 |
| `average_collect_cnt` | 平均收藏数 |
| `average_barrage_cnt` | 平均弹幕数 |
| `average_interactive_rate` | 平均互动率 |

**非花火商单数据 (_other_h):**
| 字段 | 说明 |
|---|---|
| `average_play_cnt_other_h` | 非花火平均播放量 |
| `average_comment_cnt_other_h` | 非花火平均评论数 |
| `average_collect_cnt_other_h` | 非花火平均收藏数 |
| `average_like_cnt_other_h` | 非花火平均点赞数 |
| `average_barrage_cnt_other_h` | 非花火平均弹幕数 |
| `average_interactive_rate_other_h` | 非花火平均互动率 |

**动态数据:**
| 字段 | 说明 |
|---|---|
| `dyn_median_interact_num` | 动态互动中位数 |
| `dyn_median_view_num` | 动态观看中位数 |

**基本信息补充:**
| 字段 | 说明 |
|---|---|
| `fans_like_num` | 总获赞数 |
| `video_num` | 总视频数 |
| `signature` / `introduction` | 签名/简介 |
| `upper_type_desc` | UP主类型描述(如"个人UP主") |
| `category_names` | 适合投放的商业品类(14个) |
| `magnetic_level` | 磁力等级 |

**完整分布数据（数组形式，含每项的名称和占比）:**
| 字段 | 说明 |
|---|---|
| `sax_distributions` | 关注用户性别分布 [{section_desc:"男",count:65.85},...] |
| `age_distributions` | 关注用户年龄分布(4段) |
| `device_distributions` | 关注用户设备分布(7种) |
| `top_region_distributions` | 关注用户地区分布(35省) |
| `city_distributions` | 关注用户城市等级分布(一线/新一线/二三四五线) |
| `sax_distributions_audience` | 观看用户性别分布 |
| `age_distributions_audience` | 观看用户年龄分布 |
| `device_distributions_audience` | 观看用户设备分布 |
| `top_region_distributions_audience` | 观看用户地区分布 |
| `fans_vv_distributions_audience` | 观看用户中粉丝vs路人占比 |
| `tag_profile` | 关注用户兴趣标签(200个) |
| `tag_profile_audience` | 观看用户兴趣标签(200个) |
| `first_categories_profile` / `_audience` | 一级品类偏好(Top5) |
| `second_categories_profile` / `_audience` | 二级品类偏好(Top5) |
| `up_tid_distributions` | UP主投稿分区分布 |
| `up_duration_distributions` | UP主投稿时长分布 |
| `upper_card_info` | UP主卡片(婚姻/孩子/学历等) |

### API3(投稿趋势) 独有

| 数据 | 说明 |
|---|---|
| 每条视频的播放量/点赞量/评论量/弹幕量 | 视频粒度明细 |
| `min_cnt` / `max_cnt` / `median` | 各指标的最小/最大/中位数 |
| `is_history_hot` / `is_history_explode` | 每条视频的热门/爆款标记 |

### API4(粉丝趋势) 独有

| 数据 | 说明 |
|---|---|
| `fans_inc7/30/90/180/365` | 多周期涨粉量(API1只有一个涨粉量) |
| `fans_inc_rate7/30/90/180/365` | 多周期涨粉率 |
| `data_statistics_by_day_vos` | 366天每日粉丝总数/增量 |

### API5(代表作品) 独有

| 数据 | 说明 |
|---|---|
| 商业/个人代表作品列表 | 每条含播放/点赞/评论/弹幕/互动率 |
| `cooperation_type` | 商业作品的合作类型 |
| `category_names` | 商业作品的投放品类 |
| `archive_highlights_vo` | 作品亮点(热门/爆款标记) |

---

## 各 API 详细字段

### API 1: UP主广场列表

**URL**: `GET /advertiser/upper_square/search`

| 参数 | 说明 |
|---|---|
| `ct_id` | 请求token |
| `page` | 页码，从1开始，每页20条 |

**返回字段按类别:**

#### 基本信息
| 字段 | 中文名 | 说明 |
|---|---|---|
| `nickname` | UP主昵称 | |
| `upper_mid` | UP主MID | B站用户ID |
| `gender_desc` | 性别 | |
| `region_desc` | 地区 | 省份 |
| `second_region_desc` | 城市 | |
| `partition_name` | 一级分区 | |
| `second_partition_name` | 二级分区 | |
| `mcn_company_name` | MCN公司 | |
| `head_img` | 头像URL | |
| `is_high_potential` | 是否高潜UP主 | 0/1 |
| `upper_type` | UP主类型 | |
| `active_status` | 活跃状态 | |
| `is_new_upper` | 是否新UP主 | 0/1 |
| `is_new_enter` | 是否新入驻 | 0/1 |
| `is_live` | 是否直播中 | |

#### 核心指标
| 字段 | 中文名 | 说明 |
|---|---|---|
| `fans_num` | 粉丝量 | |
| `fans_inc` | 涨粉量 | |
| `fans_inc_rate` | 涨粉率(%) | |
| `average_play_cnt` | 播放量中位数 | 网页显示名 |
| `play_median` | 播放中位数(另一字段) | |
| `median_play_30d` | 30天播放中位数 | |
| `interactive_rate` | 互动率 | |
| `hot_avid_rate` | 热门稿件率 | |
| `draft_duration` | 投稿时长 | |
| `avid_cnt_30d` | 近30天投稿数 | |
| `avid_cnt_90d` | 近90天投稿数 | |
| `avid_cnt_180d` | 近180天投稿数 | |
| `hot_avid_cnt_180d` | 180天热门稿件数 | |
| `commercial_avid_cnt` | 商业视频数 | |
| `app_vv_percent` | 移动端播放占比 | |
| `pc_vv_percent` | PC端播放占比 | |
| `app_vv_percent_desc` | 移动端播放占比说明 | 如"70~80%" |
| `pc_vv_percent_desc` | PC端播放占比说明 | 如"<50%" |
| `synthetical_score` | 综合评分 | |
| `magnetic_value` | 磁力值 | |
| `dynamic_score` | 动态评分 | |
| `estimated_play` | 预估播放量 | |
| `estimated_cost` | 预估花费 | |
| `is_boosting` | 是否助推中 | 0/1 |

#### 报价
| 字段 | 中文名 | 说明 |
|---|---|---|
| `price_infos[type=1].platform_price` | 植入视频报价 | cooperation_type=1 |
| `price_infos[type=2].platform_price` | 定制视频报价 | cooperation_type=2 |
| `price_infos[type=3].platform_price` | 直发动态报价 | cooperation_type=3 |
| `price_infos[type=4].platform_price` | 转发动态报价 | cooperation_type=4 |
| `brand_embedding_platform_price_cpm` | 品牌植入CPM | |
| `content_customized_platform_price_cpm` | 内容定制CPM | |
| `cpm` | CPM | |
| `cpc` | CPC | |
| `cpe` | CPE | |
| `blue_url_ctr` | 蓝链点击率 | |
| `blue_url_click_cost` | 蓝链点击成本 | |

#### 效果数据 (up_draft_data_view)
| 字段 | 中文名 |
|---|---|
| `play_median_all_7d/15d/30d` | 全部流量_播放中位数_7/15/30天 |
| `play_median_nature_7d/15d/30d` | 自然流量_播放中位数_7/15/30天 |
| `cpm_all_7d/15d/30d` | 全部流量_CPM_7/15/30天 |
| `cpm_nature_7d/15d/30d` | 自然流量_CPM_7/15/30天 |
| `cpc_all_7d/15d/30d` | 全部流量_CPC_7/15/30天 |
| `cpc_nature_7d/15d/30d` | 自然流量_CPC_7/15/30天 |
| `cpe_all_7d/30d` | 全部流量_CPE_7/30天 |
| `cpe_nature_7d/30d` | 自然流量_CPE_7/30天 |

#### 画像摘要 (upper_user_portrait_info)
| 字段 | 中文名 |
|---|---|
| `sax_distributions_1` / `sax_distributions_0` | 关注用户_男/女性占比(%) |
| `age_distributions_0_17/18_24/25_30/30_999` | 关注用户_各年龄段占比(%) |
| `age_distributions_audience_0_17/18_24/25_30/30_999` | 观看用户_各年龄段占比(%) |
| `fans_vv_distributions_audience` | 观看用户_粉丝观看占比(%) |

#### 带货数据 (goods_up_data_view)
| 字段 | 中文名 |
|---|---|
| `goods_up_level` | 带货等级 |
| `goods_category` | 带货品类 |
| `goods_avg_price` / `goods_avg_price_desc` | 带货均价 |
| `goods_gpm` / `goods_gpm_desc` | 带货GPM |
| `all_click_rate` / `all_click_rate_desc` | 全部点击率 |
| `comment_all_click_rate` / `comment_all_click_rate_desc` | 评论区点击率 |

#### 直播数据
| 字段 | 中文名 |
|---|---|
| `live_audience_h_avg_30d` | 直播_场均观看人数_30天 |
| `live_danmu_h_avg_30d` | 直播_场均弹幕数_30天 |
| `popularity` | 直播_人气值 |
| `live_level` | 直播_等级 |
| `live_gmv_avg_desc` | 直播_GMV均值说明 |
| `live_per_viewing_time` | 直播_人均观看时长 |
| `live_good_price_avg` | 直播_带货均价 |
| `live_sale_amount_90day` | 直播_90天带货金额 |
| `live_good_category` | 直播_带货品类 |
| `goods_permission` | 带货权限 |

#### DMP人群
| 字段 | 中文名 |
|---|---|
| `dmp_fans_rate` | DMP粉丝匹配率 |
| `dmp_cover_rate` | DMP覆盖率 |
| `dmp_cover_count` | DMP覆盖人数 |

#### 标签
| 字段 | 中文名 |
|---|---|
| `special_tags` | 特殊标签(marriage/kid/education等) |
| `cooperation_mode_tags` | 合作模式标签 |
| `high_convert_tags` | 高转化标签 |

---

### API 2: UP主详情画像

**URL**: `GET /advertiser/portrait`

| 参数 | 说明 |
|---|---|
| `upper_mid` | UP主的B站用户ID |

**返回字段按类别:**

#### 基本信息(与API1重叠)
`nickname`, `upper_mid`, `mapping_id`, `gender_desc`, `region_desc`, `second_region_desc`, `partition_name`, `second_partition_name`, `mcn_company_name`, `head_img`, `fans_num`, `average_play_cnt`, `median_play_30d`, `app_vv_percent`, `pc_vv_percent`, `active_status`, `is_live`, `is_new_upper`, `is_new_enter`, `upper_type`, `is_treasure_up`

#### 独有 - 互动均值
| 字段 | 中文名 | 示例值 |
|---|---|---|
| `average_comment_cnt` | 平均评论数 | 1740 |
| `average_like_cnt` | 平均点赞数 | 50121 |
| `average_collect_cnt` | 平均收藏数 | 6427 |
| `average_barrage_cnt` | 平均弹幕数 | 2688 |
| `average_interactive_rate` | 平均互动率 | 0.1037 |

#### 独有 - 非花火商单数据
| 字段 | 中文名 | 示例值 |
|---|---|---|
| `average_play_cnt_other_h` | 非花火平均播放量 | 973191 |
| `average_comment_cnt_other_h` | 非花火平均评论数 | 2057 |
| `average_collect_cnt_other_h` | 非花火平均收藏数 | 8676 |
| `average_like_cnt_other_h` | 非花火平均点赞数 | 45206 |
| `average_barrage_cnt_other_h` | 非花火平均弹幕数 | 2182 |
| `average_interactive_rate_other_h` | 非花火平均互动率 | 0.0889 |

#### 独有 - 动态数据
| 字段 | 中文名 | 示例值 |
|---|---|---|
| `dyn_median_interact_num` | 动态互动中位数 | 52008 |
| `dyn_median_view_num` | 动态观看中位数 | 1174340 |

#### 独有 - 补充信息
| 字段 | 中文名 | 示例值 |
|---|---|---|
| `fans_like_num` | 总获赞数 | 70928929 |
| `video_num` | 总视频数 | 386 |
| `signature` | 个性签名 | "发一些科普..." |
| `introduction` | 简介 | |
| `upper_type_desc` | UP主类型描述 | "个人UP主" |
| `category_names` | 适合投放品类(14个) | ["3C数码",...] |
| `magnetic_level` | 磁力等级 | 7 |
| `upper_prices` | 报价列表(与API1的price_infos结构相似) | |

#### 独有 - 完整分布数据
| 字段 | 中文名 | 数据格式 |
|---|---|---|
| `sax_distributions` | 关注用户_性别分布 | [{section_desc:"男",count:65.85},...] |
| `age_distributions` | 关注用户_年龄分布 | 4段 |
| `device_distributions` | 关注用户_设备分布 | 7种(苹果/小米/华为/vivo/荣耀/OPPO/三星) |
| `top_region_distributions` | 关注用户_地区分布 | 35省 |
| `city_distributions` | 关注用户_城市等级分布 | 一线/新一线/二/三/四/五线 |
| `sax_distributions_audience` | 观看用户_性别分布 | 同上 |
| `age_distributions_audience` | 观看用户_年龄分布 | 同上 |
| `device_distributions_audience` | 观看用户_设备分布 | 同上 |
| `top_region_distributions_audience` | 观看用户_地区分布 | 同上 |
| `fans_vv_distributions_audience` | 观看用户_粉丝vs路人 | [{section_desc:"粉丝",count:53.25},...] |
| `tag_profile` | 关注用户_兴趣标签 | 200个 |
| `tag_profile_audience` | 观看用户_兴趣标签 | 200个 |
| `first_categories_profile` / `_audience` | 一级品类偏好 | Top5 |
| `second_categories_profile` / `_audience` | 二级品类偏好 | Top5 |
| `up_tid_distributions` | UP主投稿分区分布 | |
| `up_duration_distributions` | UP主投稿时长分布 | 4段(1-3min/3-5min/5-10min/10min+) |
| `upper_card_info` | UP主卡片信息 | 含婚姻/孩子/学历/宠物等 |

---

### API 3: 投稿趋势数据

**URL**: `GET /advertiser/portrait/draft/trend_extra`

| 参数 | 说明 |
|---|---|
| `upper_mid` | UP主的B站用户ID |
| `trend_type` | **3**=播放量, **4**=点赞量, **5**=评论量, **6**=弹幕量 |
| `ct_id` | 请求token |

**ct_id 对照表**:
| trend_type | 含义 | ct_id示例 |
|---|---|---|
| 3 | 播放量 | `9VCL6myChGkKrKnx8tl1Z` |
| 4 | 点赞量 | `d86tmQpGI8LjNMb_Axuct` |
| 5 | 评论量 | `OM2HySMUxx824kgNKlQYZ` |
| 6 | 弹幕量 | `uOHpmYB3VsTb1Ac1tshTZ` |

**返回字段**:
| 字段 | 示例值 | 说明 |
|---|---|---|
| `min_cnt` | 240973 | 最小值 |
| `max_cnt` | 4079802 | 最大值 |
| `median` | 817462.5 | 中位数 |
| `upper_draft_trend_info_vos[].av_id` | "115899726109985" | 视频AV号 |
| `upper_draft_trend_info_vos[].bv_id` | "BV1JQkwByEJr" | 视频BV号 |
| `upper_draft_trend_info_vos[].title` | "..." | 视频标题 |
| `upper_draft_trend_info_vos[].pub_date` | "2026-01-16 15:00:00" | 发布时间 |
| `upper_draft_trend_info_vos[].trend_cnt` | 341383 | **趋势值**(播放/点赞/评论/弹幕) |
| `upper_draft_trend_info_vos[].play` | 341383 | 播放量 |
| `upper_draft_trend_info_vos[].is_spark_avid` | 0 | 是否花火商单视频 |
| `upper_draft_trend_info_vos[].is_history_hot` | 1 | 是否历史热门 |
| `upper_draft_trend_info_vos[].is_history_explode` | 0 | 是否历史爆款 |
| `upper_draft_trend_info_vos[].is_current_high_interact` | 0 | 是否当前高互动 |

---

### API 4: 粉丝趋势数据

**URL**: `GET /advertiser/portrait/attention_user/trend_extra`

| 参数 | 说明 |
|---|---|
| `upper_mid` | UP主的B站用户ID |
| `query_type` | **1**=粉丝总量, **2**=粉丝增量 |
| `ct_id` | 请求token |

**ct_id 对照表**:
| query_type | 含义 | ct_id示例 |
|---|---|---|
| 1 | 粉丝总量 | `cgZtA93RngtGbAo_tADPK` |
| 2 | 粉丝增量 | `wFre1PSwogq_xLuSMb9XR` |

**返回字段**:
| 字段 | 示例值 | 说明 |
|---|---|---|
| `fans_inc7` / `fans_inc_rate7` | 134 / 0 | 7天涨粉量/率 |
| `fans_inc30` / `fans_inc_rate30` | 5709 / 0.05 | 30天涨粉量/率 |
| `fans_inc90` / `fans_inc_rate90` | 31 / 0 | 90天涨粉量/率 |
| `fans_inc180` / `fans_inc_rate180` | 106552 / 1.02 | 180天涨粉量/率 |
| `fans_inc365` / `fans_inc_rate365` | 317946 / 3.1 | 365天涨粉量/率 |
| `data_statistics_by_day_vos` | [...] | 366天每日数据 |

query_type=1时 `count` 为当日粉丝**总数**，query_type=2时为当日**新增数**。

---

### API 5: 代表作品列表

**URL**: `GET /advertiser/representative/list`

| 参数 | 说明 |
|---|---|
| `upper_mid` | UP主的B站用户ID |
| `type` | **1**=个人作品, **2**=商业作品 |
| `ct_id` | 请求token |

**ct_id 对照表**:
| type | 含义 | ct_id示例 |
|---|---|---|
| 1 | 个人作品 | `Y3qhV4AfU6LpZrYnbuEzu` |
| 2 | 商业作品 | `phq1tDjufRQy0-XKWwXM4` |

**每条作品字段**:
| 字段 | 示例值 | 说明 |
|---|---|---|
| `av_id` | "115738731877498" | 视频AV号 |
| `bv_id` | "BV1iGqHB5EE7" | 视频BV号 |
| `title` | "..." | 视频标题 |
| `pub_time` | 1766052000 | 发布时间(Unix时间戳) |
| `duration` | 444 | 视频时长(秒) |
| `play_cnt` | 7005478 | 播放量 |
| `like_cnt` | 312591 | 点赞数 |
| `comment_cnt` | 26563 | 评论数 |
| `danmu_cnt` | 125584 | 弹幕数 |
| `interact_cnt` | 502685 | 互动总数 |
| `interact_rate` | 7.18 | 互动率(%) |
| `vt` | 9881242 | 总播放量(含推荐等) |
| `cooperation_type` | 2 | 合作类型(商业有值，个人None) |
| `type_desc` | "商业合作" | 类型描述 |
| `category_names` | ["美妆护肤"] | 商业品类 |
| `archive_highlights_vo.is_popular` | 1 | 是否热门 |
| `archive_highlights_vo.is_hot` | 1 | 是否爆款 |
| `archive_highlights_vo.play` | "百万播放" | 播放量描述 |

---

## 注意事项

1. **API 1 是唯一的批量接口**，一次返回20个UP主，500页覆盖10000个UP主
2. **API 2/3/4/5 是逐个UP主查询**，需要 `upper_mid` 参数
3. **频率限制**: 请求过快返回 `code: 1031`，建议每个Cookie保持 >=2s 间隔
4. **ct_id**: 不同接口/参数组合对应不同的 ct_id，可能会变化
5. **Cookie 过期**: `_pickup` 中的 JWT token 有过期时间，过期后需重新从浏览器获取
6. **请求量估算**: 全量抓取10000个UP主所有数据约需 10000*(1+4+2+2)=90000 次请求(API2~5)
