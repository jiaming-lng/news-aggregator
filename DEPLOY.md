# TechNews 部署指南

## 方式一：局域网共享（最简单，无需部署）

同一 WiFi 下的设备直接访问：

```
http://192.168.0.134:5000
```

> 注意：电脑需要保持开机和服务器运行状态。

**启动服务器命令：**
```bash
cd D:\Workbuddy.Web\8.4\news-aggregator\backend
python app.py
```

**开启 debug 模式（仅本地开发）：**
```bash
set FLASK_DEBUG=1
python app.py
```

---

## 方式二：部署到 Render.com（免费，公网可访问）

### 步骤

1. **注册 GitHub 账号**（如果没有）
   - 访问 https://github.com/signup

2. **上传项目到 GitHub**
   ```bash
   cd D:\Workbuddy.Web\8.4\news-aggregator
   git init
   git add .
   git commit -m "TechNews 资讯聚合网站"
   ```
   在 GitHub 创建新仓库后：
   ```bash
   git remote add origin https://github.com/你的用户名/technews.git
   git push -u origin main
   ```

3. **在 Render 部署**
   - 访问 https://render.com 注册（可用 GitHub 账号登录）
   - 点击 "New +" → "Web Service"
   - 连接你的 GitHub 仓库
   - Render 会自动识别 `render.yaml` 配置
   - 点击 "Create Web Service"
   - 等待构建完成（约 2-3 分钟）

4. **获取公网地址**
   - 部署完成后，Render 会分配一个地址，如：
   ```
   https://technews-xxxx.onrender.com
   ```
   - 任何人都可以通过这个地址访问

### 注意事项
- 免费套餐：15 分钟无访问会自动休眠，下次访问时需等待约 30 秒冷启动
- SQLite 数据在每次部署/重启后会重置（爬虫会自动重新抓取）
- 如需持久化数据，可升级为付费套餐或接入 PostgreSQL

---

## 方式三：内网穿透（临时分享，无需部署）

适合快速演示给朋友看：

### 使用 cpolar（国内友好）
1. 下载：https://www.cpolar.com/
2. 安装后运行：
   ```
   cpolar http 5000
   ```
3. 得到公网地址，如 `https://xxxx.r2.cpolar.top`

### 使用 ngrok（国际）
1. 下载：https://ngrok.com/
2. 安装后运行：
   ```
   ngrok http 5000
   ```
3. 得到公网地址，如 `https://xxxx.ngrok-free.app`

---

## 部署相关文件说明

| 文件 | 作用 |
|------|------|
| `backend/wsgi.py` | WSGI 入口，供 gunicorn 调用 |
| `backend/requirements.txt` | Python 依赖清单 |
| `Procfile` | 部署启动命令（Render/Heroku 通用） |
| `render.yaml` | Render.com 自动部署配置 |
| `.gitignore` | Git 忽略规则（排除数据库、缓存等） |

## 生产环境安全检查

- [x] debug 模式已关闭（通过环境变量 FLASK_DEBUG 控制）
- [x] XSS 防护已实现（html.escape）
- [x] CORS 已配置
- [x] gzip 压缩已启用
- [ ] HTTPS（部署平台自动提供）
- [ ] 速率限制（如需防止滥用可后续添加）
