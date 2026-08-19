# -*- coding: utf-8 -*-
import sqlite3
import os

conn = sqlite3.connect(os.path.join('data', 'news.db'))
conn.row_factory = sqlite3.Row

agnes_count = conn.execute(
    "SELECT COUNT(*) FROM articles WHERE title LIKE '%Agnes%' OR keywords LIKE '%Agnes%'"
).fetchone()[0]
print(f'本地数据库 Agnes 文章数: {agnes_count}')

rows = conn.execute(
    "SELECT id, title, source_url, published_at FROM articles WHERE title LIKE '%Agnes%' ORDER BY id DESC"
).fetchall()
for r in rows:
    print(f'  [{r["id"]}] {r["title"][:50]}... | {r["published_at"]}')
conn.close()
