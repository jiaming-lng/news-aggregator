# TechNews 科技资讯聚合站

实时聚合 GitHub、Hacker News、Bilibili、科技博客、AI 科技媒体等平台资讯的轻量级网站。后端 Flask 3 + SQLite，前端原生 HTML/CSS/JS，每 30 分钟自动抓取更新。

## 在线访问

- 当前地址：`https://106.53.58.166`（HTTPS，首次访问浏览器提示证书不匹配时点"继续前往"即可）
- 正式域名：ICP 备案办理中，备案通过后切换至正式域名

## 功能

- **资讯聚合**：8 个来源自动抓取（GitHub / Hacker News / Bilibili / 科技博客 RSS / GitHub Trending / AI 科技媒体 RSS / Reddit / YouTube）
- **分类浏览**：AI / 开源 / 科技 三大分类
- **搜索与收藏**：全文搜索、个人收藏夹
- **文章详情**：详情页 + 原文跳转
- **博客系统**：Markdown 发布，管理员专属
- **用户系统**：注册 / 登录 / 管理员角色（`ADMIN_EMAILS` 白名单自动授予）
- **体验**：亮暗主题、响应式布局、SEO（sitemap / robots / Open Graph / Schema.org）

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.10+ · Flask 3 · Gunicorn |
| 数据 | SQLite |
| 前端 | 原生 HTML / CSS / JS（Jinja2 SSR，无框架） |
| 部署 | Docker · Docker Compose · Nginx（HTTPS 反代）· Let's Encrypt 证书 |

## 快速开始（本地开发）

```bash
cd backend
pip install -r requirements.txt
python app.py
```

访问 `http://localhost:5000`。

### 环境变量

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `PORT` | 服务端口 | `5000` |
| `FLASK_DEBUG` | 调试模式 | `0` |
| `ADMIN_EMAILS` | 管理员邮箱白名单（逗号分隔），注册命中自动授予管理员 | 空 |
| `BASE_URL` | 站点对外地址（用于 robots / sitemap） | `https://technews.dedyn.io` |

## Docker 部署

```bash
docker compose up -d --build
```

生产环境流量路径：**公网 443 → Nginx（证书 + 反代）→ 容器 `127.0.0.1:5000`**；容器 5000 端口只绑定本机回环，不直接暴露公网。

更完整的部署说明见 [DEPLOY.md](DEPLOY.md) 与 [DOCKER_README.md](DOCKER_README.md)。

## 目录结构

```
news-aggregator/
├── backend/                 # Flask 后端
│   ├── app.py               # 主应用（API + 页面路由 + 定时调度）
│   ├── crawler.py           # 爬虫引擎（核心数据源 + run_crawl_job 调度）
│   ├── crawler_enhancements.py  # 扩展爬虫（GitHub Trending + AI 科技 RSS）
│   ├── database.py          # SQLite 封装（建表 + 全部 CRUD）
│   └── requirements.txt     # flask / flask-cors / gunicorn
├── frontend/
│   ├── templates/           # 7 个 Jinja2 页面（SSR 预渲染）
│   ├── js/                  # 原生 JS（app / auth / admin / theme ...）
│   └── css/style.css        # 全局样式（CSS 变量主题）
├── docker-compose.yml       # 容器编排（technews）
├── Dockerfile
└── AGENTS.md                # AI 协作开发约定
```

## 数据源

| 标识 | 来源 | 状态 |
| --- | --- | --- |
| `github` | GitHub Search API（近 7 天 star>50） | ✅ |
| `hackernews` | Hacker News Algolia（近 3 天 points>30） | ✅ |
| `bilibili` | Bilibili 关键词搜索（WBI 签名） | ✅ |
| `blog` | 10 个科技博客 RSS | ✅ |
| `ai_news` | IT之家 / 雷峰网 / 少数派 / Solidot / 开源中国 RSS（AI 关键词过滤） | ✅ |
| `github_trending` | GitHub Trending HTML | ⚠️ 偶发失败 |
| `reddit` | Reddit | ⛔ GFW 不可达，优雅降级 |
| `youtube` | YouTube | ⛔ 国内环境超时降级 |

调度入口：`crawler.py` 的 `run_crawl_job()`，每 30 分钟自动执行一次。

## 安全说明

- 管理接口全部要求管理员角色（博客增删改 + 管理后台）
- 博客内容服务端 XSS 消毒
- 登录 / 注册接口限流
- 仓库不含任何密码 / Token（VPS 使用 SSH 密钥认证）
- 生产容器仅绑定本机回环端口，公网只暴露 Nginx 443

## 相关文档

- [AGENTS.md](AGENTS.md) — AI 协作开发约定
- [PROJECT_GUIDE.md](PROJECT_GUIDE.md) — 完整项目文档
- [DEPLOY.md](DEPLOY.md) — 部署说明
- [DOCKER_README.md](DOCKER_README.md) — Docker 使用说明
