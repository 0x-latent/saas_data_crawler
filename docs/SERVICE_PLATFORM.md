# SaaS 数据平台服务说明

第一期服务使用 PostgreSQL、FastAPI、Redis/RQ、Playwright、React 和 Docker Compose。

## 服务结构

```text
saas_crawler/storage/      SQLAlchemy 模型、仓储与 Alembic 迁移
saas_crawler/ingestion/    历史资产发现和平台导入器
saas_crawler/tasks/        采集任务队列和执行器
saas_crawler/accounts/     凭据加密、登录会话和登录 worker
saas_crawler/api/          FastAPI 路由
frontend/                  React + Vite + Ant Design
scripts/verify_*.py        数据、API、队列和星图任务验证脚本
```

## 本地运行

先启动基础服务并升级数据库：

```powershell
docker compose up -d postgres redis
.\.venv\Scripts\python.exe -m alembic upgrade head
```

启动 API 和两个 worker：

```powershell
.\.venv\Scripts\python.exe -m saas_crawler.cli api
.\.venv\Scripts\python.exe -m saas_crawler.cli worker
.\.venv\Scripts\python.exe -m saas_crawler.cli login-worker
```

本地前端：

```powershell
cd frontend
npm install
npm run dev
```

默认地址：

```text
前端开发服务：http://localhost:5173
后端 API：http://localhost:8000/api
API 文档：http://localhost:8000/docs
```

如果 `8000` 已被占用，可以通过 `VITE_API_PROXY` 指定前端代理目标。

## 历史数据迁移

发现本地资产：

```powershell
.\.venv\Scripts\python.exe -m saas_crawler.cli discover-assets
```

导入指定资产：

```powershell
.\.venv\Scripts\python.exe -m saas_crawler.cli ingest-asset 1
```

相同文件指纹的成功批次再次执行时会复用原批次，不会重复插入快照。文件大小、mtime 或内容摘要变化后，资产会重新变为 `pending`。

大型 raw JSON、checkpoint、zip 和 html 第一阶段只登记到 `data_asset`，不深解析。

迁移完成后运行核对：

```powershell
.\.venv\Scripts\python.exe scripts\verify_service_data.py
```

## 登录中心

- 用户名、手机号、密码、Cookie 和 storage state 使用 `CRAWLER_SECRET_KEY` 加密保存。
- 登录请求进入独立 `login` 队列，避免扫码等待阻塞采集 worker。
- 扫码模式生成二维码或页面截图，前端每两秒轮询。
- 短信模式通过 Redis 临时传递验证码，验证码不会写入数据库。
- 登录成功后自动回存加密 Cookie 和 storage state。
- 滑块和复杂安全验证只显示截图与人工提示，不做自动破解。
- 用户取消登录会话后，worker 会关闭对应浏览器上下文。

平台登录页面经常变化。当前提供星图、磁力聚星、飞瓜快手和飞瓜入口，账号密码与短信输入使用兼容选择器；平台页面改版后需要更新对应适配器。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\verify_service_data.py
.\.venv\Scripts\python.exe scripts\verify_service_api.py
.\.venv\Scripts\python.exe scripts\verify_workers.py
.\.venv\Scripts\python.exe scripts\verify_xingtu_task.py
.\.venv\Scripts\python.exe scripts\verify_login_capture.py
```

前端验证：

```powershell
cd frontend
npm run build
npm audit --omit=dev
```

## Docker Compose

创建 `.env`，至少设置：

```text
POSTGRES_DB=saas_crawler
POSTGRES_USER=crawler
POSTGRES_PASSWORD=<strong-password>
CRAWLER_SECRET_KEY=<stable-random-secret>
LOGIN_HEADLESS=1
```

启动：

```bash
docker compose up -d --build
```

Compose 会先执行 `alembic upgrade head`，成功后再启动 API、采集 worker、登录 worker、前端和 nginx。统一入口为 `http://服务器:8080`。

生产环境必须保持 `CRAWLER_SECRET_KEY` 稳定，否则已有凭据无法解密。建议只通过 VPN、零信任网关或带身份认证的反向代理开放管理端，并配置 PostgreSQL 备份、HTTPS 和日志保留策略。
