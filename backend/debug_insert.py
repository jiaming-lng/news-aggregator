# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, '.')
from database import insert_article, get_db

# 测试插入一篇新文章
result = insert_article(
    title='TEST Agnes 文章插入测试 - 20260815',
    summary='这是一篇测试文章',
    source_platform='blog',
    category='ai',
    source_url='https://test.agnes.ai/test-20260815',
    author='Test Bot',
    published_at='2026-08-15 15:45:00',
    thumbnail_url='',
    keywords='AI,Agnes,测试',
)
print(f'插入结果: {result}')

# 验证
conn = get_db()
count = conn.execute("SELECT COUNT(*) FROM articles WHERE title LIKE '%TEST Agnes%'").fetchone()[0]
print(f'TEST Agnes 文章数: {count}')

# 看看所有 Agnes 文章
agnes = conn.execute("SELECT id, title, published_at FROM articles WHERE title LIKE '%Agnes%' ORDER BY id DESC LIMIT 10").fetchall()
for r in agnes:
    print(f'  [{r[0]}] {r[2]} - {r[1][:50]}')
conn.close()
