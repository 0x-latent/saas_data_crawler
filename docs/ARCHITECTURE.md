# 架构说明

这个项目定位为垂直 SaaS 数据采集工具，已接入 4 个平台、覆盖 B 站和快手：火花（B 站官方）、飞瓜·B 站、飞瓜·快手、磁力聚星（快手官方）。

## 分层

```text
saas_crawler/
├── core/               # 平台无关基础设施
│   ├── paths.py        # 仓库路径、data/checkpoints/config 约定
│   ├── config.py       # YAML 配置和 Cookie Header 构造
│   ├── checkpoint.py   # JSON 断点读写
│   ├── exporters.py    # Excel 导出
│   └── dependencies.py # 本地依赖加载
├── platforms/          # 平台注册和后续平台适配器
└── cli.py              # 项目级 CLI

scripts/
├── scraper.py                    # 火花 API 采集
├── scraper_browser.py            # 火花浏览器详情采集
├── feigua_scraper.py             # 飞瓜·B 站采集
├── merge_data.py                 # 火花 + 飞瓜数据合并
├── ks_feigua_scraper.py          # 飞瓜·快手采集
├── ks_feigua_build_dashboard.py  # 飞瓜·快手 Mart / 看板生成
├── magnetic_juxing_scraper.py    # 磁力聚星采集（SQLite 工作流）
└── windows/                      # Windows 辅助脚本
```

## 接入新平台的建议流程

1. 在 `saas_crawler/platforms/registry.py` 注册平台元信息。
2. 在 `scripts/` 下新增平台采集入口，复用 `saas_crawler.core` 中的配置、断点和导出能力。
3. 平台专属字段映射先保留在平台脚本内，稳定后再抽到平台模块或 YAML 配置。
4. 输出文件统一写入 `data/`，断点统一写入 `checkpoints/`。
5. 真实 Cookie 只写入本地 `config.yaml`，不要提交。

## 当前边界

- 各平台（火花、飞瓜·B 站、飞瓜·快手、磁力聚星）的业务采集逻辑仍保留在现有脚本中，以降低稳定采集流程的回归风险。
- 公共能力已经下沉到 `saas_crawler.core`，后续新增平台时应优先复用这些模块。
- CLI 当前用于项目发现，真正采集入口仍保持脚本形式，便于沿用现有运行方式。
