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

# 停掉旧的 systemd 服务，避免端口 5000 冲突（服务名是 news-aggregator）
sudo systemctl stop news-aggregator
sudo systemctl disable news-aggregator   # 防止 VPS 重启后抢端口
```

> **数据零丢失**：compose 用的是 bind mount（`./backend/data:/app/backend/data`），
> 直接挂载 VPS 上现有的 `backend/data`，里面的 415 篇 SQLite 数据原地复用，无需迁移
> （2026-08-11 实测：容器启动日志 `[Seeder] 数据库已有 415 条数据，跳过种子填充`）。
>
> **Linux 权限提示**：容器内以 uid:gid=1000 运行（Dockerfile 固定 `useradd -u 1000`，compose 里 `user: "1000:1000"`，与 VPS 首个用户 ubuntu uid=1000 对齐）。若启动后报 `Permission denied` 写库，
> 在宿主机执行一次：`sudo chown -R 1000:1000 backend/data`，再 `docker compose restart`。

镜像升级流程（CI/CD 雏形）：
```bash
git pull                 # 拉最新代码
docker compose up -d --build   # 自动重建并零停机替换
```

## 四、VPS 实测记录（2026-08-11，国内网络）

腾讯云轻量（Ubuntu 22.04，2核2G）从零到 Docker 跑通的完整踩坑：

### 1. 装 Docker：官方源被墙，用阿里云镜像

```bash
# download.docker.com 在国内连接被 reset，改用阿里云
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 2. 拉镜像：Docker Hub 被墙，配国内镜像加速

```bash
# /etc/docker/daemon.json（注意：文件必须无 BOM、无 CRLF、纯 UTF-8）
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com",
    "https://docker.nju.edu.cn",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
sudo systemctl daemon-reload && sudo systemctl restart docker
```

⚠️ 坑1：**用 PowerShell here-string 写 daemon.json 会转义损坏 JSON**（`invalid character ':' in string escape code`），
最稳做法：本地写好 → `scp` 上传 → `sudo cp`。

⚠️ 坑2：dockerd 启动失败后 systemd 会进重启限频（`Start request repeated too quickly`），
导致看起来"改完配置还是起不来"。清掉计数再启：

```bash
sudo systemctl reset-failed docker.service
sudo systemctl start docker.service
```

### 3. 开机自愈链路（重启不用管）

```bash
sudo systemctl enable docker          # Docker 开机自启（装完默认 enabled）
sudo systemctl disable news-aggregator # 旧服务禁用，防止抢 5000 端口
# compose 里 restart: unless-stopped → 容器随 Docker 自动拉起
```

### 4. 免 sudo 用 docker

```bash
sudo usermod -aG docker $USER   # 重新登录生效
```

### 5. 验证清单

```bash
docker compose ps            # 容器 Up (healthy)
curl -s http://127.0.0.1:5000/api/articles | head -c 200   # HTTP 200 + JSON
curl -s http://127.0.0.1:5000/api/articles/hot | head -c 200  # 热门榜（混合榜 10 条）
```

## 五、进阶：推到镜像仓库（可选，便于多机部署）

```bash
# 用 GitHub 容器仓库 GHCR（免费，和 GitHub 账号打通）
docker tag technews:latest ghcr.io/jiaming-lng/technews:latest
docker push ghcr.io/jiaming-lng/technews:latest
# 之后 compose 里改成 image: ghcr.io/jiaming-lng/technews:latest 并删掉 build:
```

## 六、学习要点（面试常问）

1. **层缓存**：先 `COPY requirements.txt` 再装依赖，改业务代码不触发重装。
2. **多阶段构建**：本项目无编译步骤，故单阶段即可；有前端构建时才需要。
3. **数据与镜像分离**：SQLite 在 `backend/data/`，用 named volume 持久化，镜像本身无状态。
4. **最小权限**：用非 root 的 `appuser` 运行 gunicorn。
5. **健康检查**：`healthcheck` 让 Docker 知道容器是否真活（不只是进程在）。
6. **调度器单实例**：已通过 gunicorn `--preload` 解决——`wsgi.py` 的 `initialize()` 只在 master 进程执行一次，worker 不会重复启动爬虫调度/看门狗/备份线程；若将来拆出独立 crawler 服务可进一步解耦。

## 七、排错

- **前端页面空白/JS 报 404**：确认 `backend/` 和 `frontend/` 是兄弟目录（app.py 用 `__file__` 推导 frontend 路径）。
- **数据库写入 Permission denied**：确认 `technews-data` 卷权限；本 Dockerfile 已预建 `/app/backend/data` 并赋权。
- **端口冲突**：改 `docker-compose.yml` 的 `"8080:5000"` 等。
