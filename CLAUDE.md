# TechNews 资讯聚合站 — AI 协作手册（CLAUDE.md）

> 本文件供 Claude Code / Hermes / Codex 等 AI 编程工具自动读取，快速接手项目。
> 人类可读的完整文档见 `PROJECT_GUIDE.md`。

---

## 1. 项目一句话

科技资讯聚合网站：Flask 后端 + 原生前端，定时从 GitHub / Hacker News / Bilibili / 博客 RSS / Reddit / YouTube / GitHub Trending / AI 科技媒体 RSS 抓取内容，统一展示、搜索、收藏。数据存 SQLite。

- **线上地址**：https://technews.dedyn.io
- **技术栈**：Flask 3 + SQLite + 原生 HTML/CSS/JS（无前端框架）+ Gunicorn + Docker
- **Python**：3.10+（本地 3.13）

---

## 2. 目录结构（关键文件）

```
news-aggregator/
├── backend/
│   ├── app.py                  # Flask 主应用（API + 页面路由 + 定时任务调度）
│   ├── crawler.py              # 爬虫引擎（6 个核心数据源 + run_crawl_job 调度）
│   ├── crawler_enhancements.py # 扩展爬虫：GitHub Trending + AI 科技 RSS（已接入主调度）
│   ├── database.py             # SQLite 封装（建表 + 全部 CRUD）
│   ├── add_agnes_articles.py   # 手动插入 Agnes 文章脚本（一次性历史数据）
│   ├── requirements.txt        # flask / flask-cors / gunicorn
│   └── data/news.db            # ⚠️ 数据库文件（不是 data/technews.db！）
├── frontend/
│   ├── templates/              # 7 个 Jinja2 页面（SSR 预渲染）
│   ├── js/                     # 原生 JS（app.js / auth.js / admin.js ...）
│   └── css/style.css           # 全局样式（CSS 变量主题）
├── docker-compose.yml          # 容器名 technews，端口 5000:5000
├── Dockerfile                  # 构建镜像
└── PROJECT_GUIDE.md            # 完整人类文档
```

---

## 3. 本地运行

```bash
cd D:\Workbuddy.Web\8.4\news-aggregator\backend
pip install -r requirements.txt
python app.py          # 访问 http://localhost:5000
```

环境变量：`PORT`（默认 5000）、`FLASK_DEBUG`（默认 0）。

---

## 4. 部署到 VPS（重要）

VPS 信息（腾讯云轻量，广州七区，Ubuntu 22.04，2026-09-09 到期）：
- **IP**：`106.53.58.166`
- **用户**：`ubuntu`（不是 root、不是 user）
- **SSH 登录**：密钥 `~/.ssh/id_ed25519_vps`；密码仅存于腾讯云控制台/本地机密，不写入仓库
- **项目路径**：`/home/ubuntu/news-aggregator`
- **容器名**：`technews`
- **GitHub**：`jiaming-lng/news-aggregator`（SSH 免密推送）

更新部署命令（改完代码后，在 VPS 上执行）：
```bash
cd /home/ubuntu/news-aggregator
git pull origin main
docker compose up -d --build     # 必须 --build：git pull 只更新宿主机代码，容器镜像需重建
```

手动触发一次爬取（重建后）：
```bash
docker exec technews python backend/crawler.py
```

> ⚠️ 本地 `backend/data/news.db` 与 VPS 的 `news.db` 是**互相独立的文件**，修改本地库不会自动同步到 VPS。要更新线上数据，要么推代码后让爬虫跑，要么在容器内执行插入脚本。

---

## 5. 爬虫数据源清单

| 标识 | 函数 | 状态 | 说明 |
|------|------|------|------|
| `github` | `crawl_github` | ✅ | GitHub Search API，近 7 天 star>50 |
| `hackernews` | `crawl_hackernews` | ✅ | HN Algolia，近 3 天 points>30 |
| `bilibili` | `crawl_bilibili` | ✅ | 关键词搜索（含 'Agnes AI'），WBI 签名降级 |
| `blog` | `crawl_blogs` | ✅ | 10 个科技博客 RSS |
| `reddit` | `crawl_reddit` | ⚠️ GFW | 国内连不上，优雅降级返回 0 |
| `youtube` | `crawl_youtube` | ⚠️ 超时 | 需外网 |
| `github_trending` | `crawl_github_trending` | ⚠️ 偶发失败 | 爬 github.com/trending HTML；VPS 上曾因 IncompleteRead 失败，已加 500KB 读取上限，待观察 |
| `ai_news` | `crawl_ai_news` | ✅ | IT之家/雷峰网/少数派/Solidot/开源中国 RSS，按 AI 关键词过滤 |

**调度入口**：`crawler.py` 的 `run_crawl_job()`，每 30 分钟自动跑一次；新数据源已在 `sources` 列表注册。

**分类逻辑**：`_categorize()` 优先判 `ai`，再判 `opensource`，默认 `tech`。AI 关键词列表 `AI_KEYWORDS` 已含 `agnes` 系列。

---

## 6. 开发约定（改代码必看）

1. **改完 Python 必须清 `__pycache__`**：`Remove-Item -Recurse -Force backend\__pycache__`，否则跑旧代码。
2. **改前端必须递增 `app.py` 里的 `ASSET_VERSION`**，否则浏览器缓存旧 JS/CSS。
3. **数据库是 SQLite 单写者**：不适合高并发；MVP 够用。
4. **新增数据源**：在 `crawler.py` 写 `crawl_xxx()`（返回 `(new, fetched)`），加入 `run_crawl_job` 的 `sources` 列表；平台展示信息在 `app.py` 的 PLATFORM 映射。
5. **去重**：`insert_article()` 按 `source_url` 或 `title` 去重，重复会跳过。
6. **博客 API 无认证**：POST/PUT/DELETE `/api/blog/*` 没有鉴权，部署公网前需加。

---

## 7. 当前待办 / 已知坑

- [ ] `crawl_github_trending` 在 VPS 上偶发 `IncompleteRead`，已加 500KB 读取上限，需持续观察。
- [ ] Reddit / YouTube 在国内环境无法抓取（GFW），属预期降级，不影响其他源。
- [ ] VPS 2026-09-09 到期，需续费或迁移。
- [ ] 博客 API（`/api/blog/*` 的 POST/PUT/DELETE）缺鉴权，部署公网前需加。

---

## 8. 提交约定

```bash
git add -A
git commit -m "feat/fix: 简述"
git push origin main
# 然后去 VPS 执行第 4 节的部署命令
```

---

*本文件由 QClaw 生成（2026-08-19），供 AI 工具接手维护。*
