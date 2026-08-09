# TechNews 资讯聚合网站 — 项目说明文档

> 本文档供 AI 桌面端助手快速了解项目全貌，直接上手开发维护。

---

## 1. 项目概述

TechNews 是一个科技资讯聚合网站，自动从多个平台抓取热门科技内容，统一展示并提供用户收藏功能。

- **访问地址**：http://localhost:5000
- **局域网地址**：http://192.168.0.152:5000（同 WiFi 设备可访问）
- **运行状态**：服务端常驻后台，30 分钟自动爬取一次

---

## 2. 技术栈

| 层 | 技术 | 版本 | 说明 |
|----|------|------|------|
| 后端框架 | Flask | >=3.0 | 纯 Python，无 ORM，直接写 SQL |
| 数据库 | SQLite | 内置 | 纯文件数据库，零配置，数据文件在 `data/technews.db` |
| 前端 | 原生 HTML/CSS/JS | - | 零框架，无构建步骤，Flask 直接 serve 静态文件 |
| 密码哈希 | Werkzeug | 随 Flask | `generate_password_hash` / `check_password_hash` |
| WSGI 服务器 | Gunicorn | >=21.2 | 生产部署用，本地开发直接 `python app.py` |
| Python | 3.13 | 3.13.12 | 需 Python 3.10+ |

**依赖清单**（`backend/requirements.txt`）：
```
flask>=3.0.0
flask-cors>=4.0.0
gunicorn>=21.2.0
```

---

## 3. 快速启动

```bash
# 1. 进入项目目录
cd D:\Workbuddy.Web\8.4\news-aggregator\backend

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务器
python app.py

# 4. 浏览器访问
# http://localhost:5000
```

**环境变量**（可选）：
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `5000` | 服务端口 |
| `FLASK_DEBUG` | `0` | `1` 开启调试模式 |

**开机自启动**：`start_technews.vbs` 脚本放在 Windows 启动文件夹，用 `pythonw.exe` 无窗口启动。

---

## 4. 项目结构

```
news-aggregator/
├── backend/                          # 后端全部代码
│   ├── app.py                        # Flask 主应用（路由 + API + SSR 渲染 + 定时任务）
│   ├── crawler.py                    # 爬虫引擎（6 个数据源 + RSS 解析 + 分类 + 去重）
│   ├── database.py                   # SQLite 数据库（6 张表 + 全部 CRUD 函数）
│   ├── wsgi.py                       # WSGI 入口（供 Gunicorn 调用）
│   └── requirements.txt              # Python 依赖
│
├── frontend/                         # 前端全部代码
│   ├── templates/                    # Jinja2 HTML 模板（也是 SSR 页面）
│   │   ├── index.html                # 首页（资讯聚合列表）
│   │   ├── article-detail.html       # 文章详情页
│   │   ├── favorites.html            # 用户收藏页
│   │   ├── blog.html                 # 博客列表页
│   │   ├── blog-detail.html          # 博客详情页
│   │   ├── admin.html                # 管理后台（数据统计 + 文章管理）
│   │   └── admin-blog.html           # 博客管理后台（编辑器）
│   ├── js/                           # 前端 JS（原生，无框架）
│   │   ├── app.js                    # 首页逻辑（加载文章 + 搜索 + 筛选 + 排序 + 收藏）
│   │   ├── auth.js                   # 全局认证模块（登录/注册弹窗 + Token 管理 + 收藏切换）
│   │   ├── article-detail.js         # 详情页逻辑（文章详情 + 相关推荐 + 分享 + 收藏）
│   │   ├── favorites.js              # 收藏页逻辑（收藏列表 + 取消收藏 + 分页）
│   │   ├── blog.js                   # 博客列表逻辑
│   │   ├── blog-detail.js            # 博客详情逻辑（含 XSS 防护 sanitizeHtml）
│   │   ├── admin.js                  # 管理后台逻辑（图表 + 文章管理）
│   │   ├── admin-blog.js             # 博客编辑器逻辑（工具栏 + 实时预览）
│   │   └── theme.js                  # 主题切换公共模块（亮/暗模式）
│   ├── css/
│   │   └── style.css                 # 全局样式（CSS 变量 + 响应式 + 暗色主题）
│   └── assets/                       # 静态资源
│
├── data/
│   └── technews.db                   # SQLite 数据库文件（运行时自动创建）
│
├── start_technews.vbs                # Windows 开机自启动脚本
├── Procfile                          # 部署启动命令（gunicorn）
├── render.yaml                       # Render.com 部署配置
├── .gitignore                        # Git 忽略规则
└── DEPLOY.md                         # 部署指南
```

---

## 5. 数据库结构

共 6 张表，全部在 `database.py` 的 `init_db()` 中创建：

### articles（资讯文章）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| title | TEXT | 标题 |
| summary | TEXT | 摘要 |
| source_platform | TEXT | 来源平台（github/hackernews/bilibili/blog/reddit/youtube） |
| category | TEXT | 分类（programming/ai/security/hardware/opensource/mobile/devops） |
| source_url | TEXT | 原文链接 |
| author | TEXT | 作者 |
| published_at | TIMESTAMP | 发布时间 |
| fetched_at | TIMESTAMP | 抓取时间 |
| view_count | INTEGER | 浏览次数 |
| is_hot | BOOLEAN | 是否热门 |
| thumbnail_url | TEXT | 缩略图 |
| keywords | TEXT | 关键词（逗号分隔） |

索引：category, published_at DESC, source_platform, is_hot

### users（用户）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| email | TEXT UNIQUE | 邮箱（唯一） |
| username | TEXT | 用户名 |
| password_hash | TEXT | Werkzeug 密码哈希 |
| created_at | TIMESTAMP | 注册时间 |

### sessions（登录会话）
| 字段 | 类型 | 说明 |
|------|------|------|
| token | TEXT PK | 随机 Token（`secrets.token_urlsafe(32)`） |
| user_id | INTEGER FK | 关联 users.id |
| created_at | TIMESTAMP | 创建时间 |
| expires_at | TIMESTAMP | 过期时间（7 天） |

### favorites（收藏）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| user_id | INTEGER FK | 关联 users.id |
| article_id | INTEGER FK | 关联 articles.id |
| created_at | TIMESTAMP | 收藏时间 |

UNIQUE(user_id, article_id) — 防止重复收藏

### blog_posts（博客文章）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| title | TEXT | 标题 |
| content | TEXT | HTML 内容 |
| excerpt | TEXT | 摘要 |
| author | TEXT | 作者（默认 TechNews） |
| category | TEXT | 分类 |
| status | TEXT | 状态（published/draft） |
| views | INTEGER | 浏览量 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### crawl_logs（爬取日志）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| platform | TEXT | 平台名 |
| status | TEXT | 状态（running/success/failed） |
| articles_fetched | INTEGER | 抓取数量 |
| articles_new | INTEGER | 新增数量 |
| started_at | TIMESTAMP | 开始时间 |
| completed_at | TIMESTAMP | 完成时间 |
| error_message | TEXT | 错误信息 |

---

## 6. API 端点清单

### 资讯文章
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/articles` | 文章列表（支持 page/limit/category/platform/sort/search 参数） | 否 |
| GET | `/api/articles/hot` | 热门文章 | 否 |
| GET | `/api/articles/<id>` | 文章详情 + 5 篇相关推荐 | 否 |
| POST | `/api/articles/<id>/view` | 增加浏览量 | 否 |
| GET | `/api/home` | 首页聚合数据（各平台最新 + 热门） | 否 |
| GET | `/api/platforms` | 平台列表 | 否 |

### 用户认证
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 注册（email + username + password） | 否 |
| POST | `/api/auth/login` | 登录（email + password），返回 Token | 否 |
| POST | `/api/auth/logout` | 登出，删除 session | 是 |
| GET | `/api/auth/me` | 获取当前用户信息 | 是 |

**认证方式**：`Authorization: Bearer <token>` 请求头

### 收藏
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/favorites` | 收藏列表（支持分页） | 是 |
| POST | `/api/favorites/<article_id>` | 添加收藏 | 是 |
| DELETE | `/api/favorites/<article_id>` | 取消收藏 | 是 |

### 博客
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/blog/posts` | 博客列表 | 否 |
| GET | `/api/blog/posts/<id>` | 博客详情 | 否 |
| POST | `/api/blog/posts` | 创建博客 | 否 |
| PUT | `/api/blog/posts/<id>` | 更新博客 | 否 |
| DELETE | `/api/blog/posts/<id>` | 删除博客 | 否 |

### 管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 数据统计 |
| GET | `/api/crawl-logs` | 爬取日志 |
| POST | `/api/crawl/trigger` | 手动触发爬取 |

### 页面路由
| 路径 | 模板 | 说明 |
|------|------|------|
| `/` | index.html | 首页 |
| `/article/<id>` | article-detail.html | 文章详情 |
| `/favorites` | favorites.html | 收藏页 |
| `/blog` | blog.html | 博客列表 |
| `/blog/<id>` | blog-detail.html | 博客详情 |
| `/admin` | admin.html | 管理后台 |
| `/admin/blog` | admin-blog.html | 博客管理 |
| `/robots.txt` | - | 爬虫协议 |
| `/sitemap.xml` | - | 站点地图 |

---

## 7. 爬虫数据源

| 数据源 | 平台标识 | 状态 | API | 说明 |
|--------|----------|------|-----|------|
| GitHub | `github` | 正常 | Search API | 近 7 天 star>50 热门仓库，无 Key 限速 10 次/分钟 |
| Hacker News | `hackernews` | 正常 | Algolia API | 近 3 天 points>30，无限制 |
| Bilibili | `bilibili` | 正常 | Popular API | 科技分类过滤 + 关键词兜底 |
| Blog RSS | `blog` | 正常 | RSS/Atom | 10 个科技博客源（含 solidot/oschina/cnbeta 等中文源） |
| Reddit | `reddit` | GFW 屏蔽 | JSON API | /r/programming+MachineLearning+technology，代码正确但国内无法连接 |
| YouTube | `youtube` | 超时 | RSS | 需外网环境 |

**爬取频率**：30 分钟自动执行一次，过期文章（>30 天）自动清理。

**爬虫入口**：`crawler.py` 的 `run_crawl_job()` 函数，依次调用各数据源的 `crawl_*()` 函数。

---

## 8. 关键技术决策

| 决策 | 原因 |
|------|------|
| SQLite 而非 MySQL/PostgreSQL | 零配置，纯文件，适合单机部署，MVP 阶段足够 |
| 原生 JS 而非 React/Vue | 无构建步骤，Flask 直接 serve，降低复杂度 |
| Bearer Token 而非 JWT | 简单直接，Token 存 sessions 表，7 天有效期，服务端可控注销 |
| `secrets.token_urlsafe(32)` | 密码学安全随机数生成 Token |
| Werkzeug 密码哈希 | Flask 内置，自动加盐，无需额外库 |
| SSR 预渲染 + CSR 降级 | 首屏服务端渲染 HTML 卡片（`<!--SSR:ARTICLES-->`），JS 加载后接管交互 |
| HTML 放 `templates/` 而非 `static/` | 避免 Flask static 路由拦截 SSR 页面路由 |
| URL 去重用 `md5(title+url)` | 确定性 URL，替代随机数，防止重复入库 |
| ASSET_VERSION 机制 | 每次前端更新递增版本号（当前 11），通过 `?v=11` 破浏览器缓存 |
| 平台图标用文本缩写 | YT/GH/HN/BL/BG/RD，不用 emoji |
| CSS 变量主题系统 | `data-theme="dark"` + `var(--color-*)`，7 个页面共用 theme.js |
| Gzip 压缩 | app.py `after_request` 对 HTML/JSON 启用 gzip（level=6） |
| XSS 防护 | `blog-detail.js` 的 `sanitizeHtml()` 移除 script 标签和 on* 事件 |

---

## 9. 前端模块说明

### auth.js — 全局认证模块

暴露两个全局对象：

**`window.TechNewsAuth`**：
- `init()` — 初始化，检查 localStorage 中的 token，恢复登录状态
- `register(email, username, password)` — 注册
- `login(email, password)` — 登录
- `logout()` — 登出
- `isLoggedIn()` — 返回是否已登录
- `toggleFavorite(articleId, btn)` — 切换收藏状态
- `_updateUI()` — 更新 UI（显示/隐藏登录按钮和用户菜单），dispatch `auth:stateChanged` 事件

**`window.TechNewsAuthModal`**：
- `open(mode)` — 打开弹窗（mode: 'login' | 'register'）
- `close()` — 关闭弹窗

**Token 存储**：localStorage（`technews_token` + `technews_user`）

**事件**：`auth:stateChanged` — 登录/登出时触发，其他页面可监听此事件更新 UI

### theme.js — 主题切换

- 暴露 `window.TechNewsTheme`
- SVG 太阳/月亮图标
- 7 个页面共用
- 主题状态存 localStorage（`technews_theme`）

---

## 10. 已知问题与注意事项

1. **Reddit / YouTube 需外网环境**：国内 GFW 屏蔽，爬虫优雅降级（返回 0,0），不影响其他数据源
2. **Bilibili 搜索 API 需 WBI 签名**：当前被拦截，降级用 Popular API
3. **V2EX RSS 偶尔网络超时**：爬虫有 15 秒超时保护
4. **SQLite 并发限制**：单写入者，不适合高并发场景（MVP 够用）
5. **`__pycache__` 缓存**：修改代码后需清除 `backend/__pycache__/`，否则可能运行旧代码
6. **端口 5000 占用**：重启前需先 `netstat -ano | findstr :5000` 查 PID，再 `Stop-Process -Id <PID> -Force`
7. **SSR 卡片收藏状态**：首页加载时已登录用户的收藏按钮不会自动标红（需额外调批量查询 API），这是个待优化点
8. **博客 API 无认证保护**：POST/PUT/DELETE 没有鉴权，部署到公网前需加

---

## 11. 部署信息

### 本地部署
- 默认端口 5000，`python app.py` 启动
- 数据库自动创建在 `data/technews.db`
- 开机自启动：`start_technews.vbs` 放 Windows 启动文件夹

### 生产部署（Render.com）
1. 推送代码到 GitHub
2. Render.com 创建 Web Service，连接 GitHub 仓库
3. Render 自动识别 `render.yaml` 配置
4. 启动命令：`gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4`

### 注意事项
- Render 免费套餐 SQLite 是临时存储（重启清空），持久化需换 PostgreSQL
- 博客 API 需加认证保护后再部署公网

---

## 12. 开发指南

### 添加新数据源

1. 在 `crawler.py` 中新增 `crawl_xxx()` 函数，返回 `(new_count, fetched_count)`
2. 在 `run_crawl_job()` 的 sources 列表加入 `('xxx', crawl_xxx)`
3. 在 `app.py` 的平台映射中加入颜色/缩写/名称
4. 在 `database.py` 不需要改（articles 表是通用的）

### 添加新页面

1. 在 `frontend/templates/` 创建 HTML 模板
2. 在 `app.py` 添加路由
3. 在 `frontend/js/` 创建对应 JS 文件
4. 更新 `ASSET_VERSION` 破缓存

### 修改前端样式

- 全部在 `frontend/css/style.css`，使用 CSS 变量
- 亮色/暗色通过 `[data-theme="dark"]` 选择器切换
- 修改后递增 `app.py` 中的 `ASSET_VERSION`

### 重启服务器

```powershell
# 1. 清除缓存
Remove-Item -Recurse -Force backend\__pycache__

# 2. 杀旧进程
$pid = (netstat -ano | Select-String ":5000.*LISTENING" -split '\s+')[-1]
Stop-Process -Id $pid -Force

# 3. 启动新进程
Start-Process -FilePath "pythonw.exe" -ArgumentList "backend\app.py" -WorkingDirectory "backend" -WindowStyle Hidden
```

---

## 13. API 响应格式约定

所有 API 返回 JSON，统一格式：

```json
{
  "success": true,
  "data": { ... }
}
```

错误时：
```json
{
  "success": false,
  "error": "错误描述"
}
```

分页响应：
```json
{
  "success": true,
  "data": {
    "articles": [...],
    "total": 150,
    "page": 1,
    "limit": 20,
    "total_pages": 8
  }
}
```

---

*文档生成时间：2026-08-09*
*项目版本：ASSET_VERSION 11*
