# TechNews Docker 化部署说明

把现有 news-aggregator 项目封装成 Docker 镜像，实现「一次构建、到处运行」。

## 一、文件清单（放进仓库根目录）

| 文件 | 作用 |
|------|------|
| `Dockerfile` | 镜像构建脚本：Python 3.13 slim + Flask/gunicorn 依赖 + 启动命令 |
| `.dockerignore` | 排除 .git、数据库、日志等，避免打进镜像、加速构建 |
| `docker-compose.yml` | 一键编排：端口映射、数据持久化卷、健康检查、开机自启 |

## 二、本地跑起来（Windows / Mac / Linux 通用）

```bash
# 1. 把上面三个文件放到项目根目录（与 backend/、frontend/ 同级）
# 2. 构建并后台启动
docker compose up -d --build

# 3. 看日志（首次会建库 + 爬虫抓取，等 30~60 秒）
docker compose logs -f

# 4. 浏览器打开
http://localhost:5000
```

常用命令：
```bash
docker compose ps            # 查看状态 / 健康
docker compose down          # 停止并删容器（数据卷保留）
docker compose down -v       # 连数据卷一起删（清空数据库）
docker compose restart       # 重启
```

## 三、部署到腾讯云 VPS（替换原 gunicorn+systemd）

VPS 装好 Docker 后：

```bash
# 拉代码
git clone https://github.com/jiaming-lng/news-aggregator.git
cd news-aggregator

# 把三个 Docker 文件放进去后
docker compose up -d --build

# （可选）停掉旧的 systemd 服务，避免端口 5000 冲突
sudo systemctl stop technews
sudo systemctl disable technews
```

> **数据零丢失**：compose 用的是 bind mount（`./backend/data:/app/backend/data`），
> 直接挂载 VPS 上现有的 `backend/data`，里面的 263 篇 SQLite 数据原地复用，无需迁移。
>
> **Linux 权限提示**：容器内以 uid:gid=1000 运行。若启动后报 `Permission denied` 写库，
> 在宿主机执行一次：`sudo chown -R 1000:1000 backend/data`，再 `docker compose restart`。

镜像升级流程（CI/CD 雏形）：
```bash
git pull                 # 拉最新代码
docker compose up -d --build   # 自动重建并零停机替换
```

## 四、进阶：推到镜像仓库（可选，便于多机部署）

```bash
# 用 GitHub 容器仓库 GHCR（免费，和 GitHub 账号打通）
docker tag technews:latest ghcr.io/jiaming-lng/technews:latest
docker push ghcr.io/jiaming-lng/technews:latest
# 之后 compose 里改成 image: ghcr.io/jiaming-lng/technews:latest 并删掉 build:
```

## 五、学习要点（面试常问）

1. **层缓存**：先 `COPY requirements.txt` 再装依赖，改业务代码不触发重装。
2. **多阶段构建**：本项目无编译步骤，故单阶段即可；有前端构建时才需要。
3. **数据与镜像分离**：SQLite 在 `backend/data/`，用 named volume 持久化，镜像本身无状态。
4. **最小权限**：用非 root 的 `appuser` 运行 gunicorn。
5. **健康检查**：`healthcheck` 让 Docker 知道容器是否真活（不只是进程在）。
6. **可改进项**：gunicorn 多 worker 会各自启动爬虫调度线程（render 现状也如此），更优做法是拆出独立 crawler 服务或 `--workers 1`。

## 六、排错

- **前端页面空白/JS 报 404**：确认 `backend/` 和 `frontend/` 是兄弟目录（app.py 用 `__file__` 推导 frontend 路径）。
- **数据库写入 Permission denied**：确认 `technews-data` 卷权限；本 Dockerfile 已预建 `/app/backend/data` 并赋权。
- **端口冲突**：改 `docker-compose.yml` 的 `"8080:5000"` 等。
