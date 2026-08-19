# -*- coding: utf-8 -*-
import sqlite3
import os

conn = sqlite3.connect(os.path.join('data', 'news.db'))
conn.row_factory = sqlite3.Row

print("=== 所有含 Agnes 的文章 ===")
rows = conn.execute(
    "SELECT id, title, source_url, published_at, keywords FROM articles WHERE title LIKE '%Agnes%' OR keywords LIKE '%Agnes%' ORDER BY id DESC"
).fetchall()
for r in rows:
    print(f'[{r["id"]}] {r["published_at"]}')
    print(f'  {r["title"][:60]}')
    print(f'  {r["source_url"][:60]}')
    print()

print(f"\n总计: {len(rows)} 篇")
conn.close()
