#!/bin/bash
# TechNews Agnes AI 文章一键部署脚本
# 在 VPS 上执行: bash deploy_agnes.sh

set -e

echo "=== TechNews Agnes AI 部署脚本 ==="
echo ""

# 1. 进入项目目录
cd /opt/news-aggregator || {
    echo "错误: 找不到 /opt/news-aggregator 目录"
    exit 1
}

# 2. 拉取最新代码
echo "[1/4] 拉取 GitHub 最新代码..."
git pull origin main

# 3. 重启容器以加载新代码
echo "[2/4] 重启 Docker 容器..."
docker compose restart

# 4. 等待容器启动
echo "[3/4] 等待容器启动 (5秒)..."
sleep 5

# 5. 执行 Agnes 文章插入脚本
echo "[4/4] 插入 Agnes AI 文章到数据库..."
docker exec technews python backend/add_agnes_articles.py

echo ""
echo "=== 部署完成! ==="
echo ""
echo "验证: 访问 http://106.53.58.166:5000"
echo "搜索 'Agnes' 查看文章是否已添加"
