# 文档索引

本目录存放各平台的 API 调研记录、数据加工方案和字段说明。命名统一为「平台-用途」。

## 架构

- [ARCHITECTURE.md](ARCHITECTURE.md) — 项目分层、公共包 `saas_crawler` 说明、接入新平台的流程。

## 按平台

### 火花（B 站官方商业平台）

- [火花-API文档.md](火花-API文档.md) — 火花平台 API 接口、字段、查询逻辑。
- 对应脚本：`scripts/scraper.py`（API 采集）、`scripts/scraper_browser.py`（浏览器详情采集）。

### 飞瓜·B 站（第三方数据平台）

- [飞瓜B站-API文档.md](飞瓜B站-API文档.md) — 飞瓜 B 站 API 调研，含字体混淆等已知问题。
- 对应脚本：`scripts/feigua_scraper.py`。
- 与火花数据合并：`scripts/merge_data.py`。

### 飞瓜·快手（第三方数据平台）

- [飞瓜快手-API文档.md](飞瓜快手-API文档.md) — 快手飞瓜 API 调研（达人搜索、详情、直播、带货、趋势等）。
- [飞瓜快手-数据方案.md](飞瓜快手-数据方案.md) — 原始 CSV → Mart 清洗表的设计规范（字段类型、ID 去重、聚合规则）。
- [飞瓜快手-Mart字段说明.md](飞瓜快手-Mart字段说明.md) — Mart 表的实现说明与字段定义。
- 对应脚本：`scripts/ks_feigua_scraper.py`（采集）、`scripts/ks_feigua_build_dashboard.py`（生成 Mart / 看板）。

### 磁力聚星（快手官方商业平台 k.kuaishou.com）

- [磁力聚星-API文档.md](磁力聚星-API文档.md) — 磁力聚星 API 调研、SQLite 工作流、`ACCOUNT-ID` 账户选择要点。
- 对应脚本：`scripts/magnetic_juxing_scraper.py`。
