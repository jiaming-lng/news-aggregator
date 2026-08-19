# ============================================================
# TechNews (news-aggregator) Dockerfile
# 后端 Flask + gunicorn + SQLite，前端为纯静态文件
# 无需 Node 构建步骤
# ============================================================

# 基础镜像：官方 Python 3.13 slim（精简版，约 150MB）
FROM python:3.13-slim

# 环境变量
# - PYTHONDONTWRITEBYTECODE: 不写 .pyc，减小镜像
# - PYTHONUNBUFFERED: 日志实时输出到 Docker logs（调试友好）
# - FLASK_DEBUG=0: 生产模式（关闭调试器，避免任意代码执行漏洞）
# - PORT: gunicorn 绑定端口
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_DEBUG=0 \
    PORT=5000

# 工作目录 = 项目根
# 关键：backend/ 与 frontend/ 必须保持兄弟关系，
# 因为 backend/app.py 用 __file__ 推导 ../frontend 路径（与 CWD 无关）
WORKDIR /app

# ---- 层缓存优化 ----
# 先只复制依赖清单并安装，这样改业务代码不会导致依赖层失效、重新下载
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r backend/requirements.txt

# 复制源代码（backend/data 等被 .dockerignore 排除）
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# ---- 安全：用非 root 用户运行 ----
RUN useradd -m -u 1000 appuser \
    # 提前建好数据目录并赋予正确权限，bind mount 时宿主机目录需与之属主对齐
    && mkdir -p /app/backend/data \
    && chown -R appuser:appuser /app
USER appuser

# 容器监听端口（需与 gunicorn --bind 一致）
EXPOSE 5000

# 启动命令：与仓库 Procfile / render.yaml 一致
# --preload：让 wsgi.py 的 initialize() 只在 master 进程执行一次，
# 否则 2 个 worker 会各自启动一套爬虫调度器/看门狗/备份线程，导致重复爬取
# --chdir backend 保证 gunicorn 能 import wsgi:app
# wsgi.py 导入时自动 initialize()：建库 + 种子数据 + 启动爬虫调度/看门狗
CMD ["gunicorn", "--chdir", "backend", "--preload", "wsgi:app", \
     "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120"]
