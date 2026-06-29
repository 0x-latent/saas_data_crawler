# saas_data_crawler

面向火花、飞瓜、磁力聚星等垂直 SaaS 数据平台的达人数据采集项目，覆盖 B 站和快手。当前保留稳定脚本入口，同时把路径、配置、断点和导出等公共能力抽到 `saas_crawler` 包中，方便后续接入更多类似平台。

## 已接入平台

| 平台 | 渠道 | 采集脚本 | API 文档 |
|---|---|---|---|
| 火花 | B 站官方商业平台 | `scripts/scraper.py`、`scripts/scraper_browser.py` | [火花-API文档](docs/火花-API文档.md) |
| 飞瓜·B 站 | 第三方数据平台 | `scripts/feigua_scraper.py` | [飞瓜B站-API文档](docs/飞瓜B站-API文档.md) |
| 飞瓜·快手 | 第三方数据平台 | `scripts/ks_feigua_scraper.py`、`scripts/ks_feigua_build_dashboard.py` | [飞瓜快手-API文档](docs/飞瓜快手-API文档.md) |
| 磁力聚星 | 快手官方商业平台 | `scripts/magnetic_juxing_scraper.py` | [磁力聚星-API文档](docs/磁力聚星-API文档.md) |

火花 + 飞瓜数据合并：`scripts/merge_data.py`。完整文档导航见 [docs/README.md](docs/README.md)。

## 目录结构

```text
.
├── saas_crawler/       # 项目公共包：配置、断点、导出、平台注册
├── scripts/            # Python 抓取、测试和数据处理脚本
│   └── windows/        # Windows 辅助启动脚本
├── docs/               # API 文档和调研资料
├── data/               # 本地 Excel 数据产物，默认不提交
├── checkpoints/        # 抓取断点，默认不提交
├── config.example.yaml # 配置模板
├── config.yaml         # 本地 Cookie 配置，默认不提交
└── README.md
```

## 常用命令

在仓库根目录运行：

```powershell
.venv\Scripts\pip.exe install -r requirements.txt
```

火花 / 飞瓜 B 站：

```powershell
.venv\Scripts\python.exe scripts\scraper.py
.venv\Scripts\python.exe scripts\scraper_browser.py
.venv\Scripts\python.exe scripts\feigua_scraper.py
.venv\Scripts\python.exe scripts\merge_data.py
```

飞瓜快手（采集 + 生成看板）：

```powershell
.venv\Scripts\python.exe -m scripts.ks_feigua_scraper --action full
.venv\Scripts\python.exe -m scripts.ks_feigua_build_dashboard
```

磁力聚星（交互式工作台，账户已在 config.yaml 配置，无需带 --account-id）：

```powershell
.venv\Scripts\python.exe -m scripts.magnetic_juxing_scraper --action interactive
```

查看已注册平台：

```powershell
.venv\Scripts\python.exe -m saas_crawler.cli platforms
```

如需使用浏览器调试模式，可运行：

```powershell
scripts\windows\launch_chrome.bat
```

## 本地文件约定

- `config.yaml` 存放 Cookie 和账号相关配置，不进入版本控制。
- `data/` 存放抓取和合并生成的 Excel 文件，不进入版本控制。
- `checkpoints/` 存放断点续抓状态，不进入版本控制。
- `docs/` 存放可共享的 API 文档和说明材料。

## 扩展新平台

新增平台时优先复用 `saas_crawler.core`：

- `config.py`：读取 `config.yaml` 和构造 Cookie Header
- `checkpoint.py`：断点读写
- `paths.py`：统一输出目录
- `exporters.py`：Excel 导出

更完整的说明见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。
