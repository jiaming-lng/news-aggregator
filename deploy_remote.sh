#!/bin/bash
# 在 VPS 上执行的部署脚本

echo "[1/5] 进入项目目录..."
cd /opt/news-aggregator || exit 1

echo "[2/5] 拉取最新代码..."
git pull origin main

echo "[3/5] 重启容器..."
docker compose restart

echo "[4/5] 等待容器启动..."
sleep 5

echo "[5/5] 插入 Agnes 文章..."
docker exec technews python backend/add_agnes_articles.py

echo ""
echo "=== 部署完成 ==="
echo "访问: http://106.53.58.166:5000"
