"""
WSGI 入口文件 - 供 gunicorn 等生产服务器使用
gunicorn wsgi:app
"""
from app import app, initialize

# 生产环境启动前初始化数据库和爬虫
initialize()

app.config['ENV'] = 'production'
