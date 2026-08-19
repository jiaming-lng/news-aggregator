"""
WSGI 入口文件 - 供 gunicorn 等生产服务器使用
gunicorn wsgi:app
"""
from app import app, initialize

# 生产环境启动前初始化数据库和爬虫
# 注意：必须配合 gunicorn --preload 使用，让 initialize() 只在 master 进程执行一次；
# 否则每个 worker 都会启动一套调度器/看门狗/备份线程，导致重复爬取。
initialize()

app.config['ENV'] = 'production'
