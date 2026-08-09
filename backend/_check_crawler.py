# -*- coding: utf-8 -*-
"""查看最新一轮爬取明细 + 清理测试用户"""
import sqlite3

db = sqlite3.connect('data/news.db')
cur = db.cursor()

print('--- 最新一轮爬取明细 ---')
cur.execute('''SELECT platform, status, articles_fetched, articles_new,
    COALESCE(error_message, '') FROM crawl_logs
    WHERE started_at >= datetime('now', '-5 minutes')
    ORDER BY id''')
for row in cur.fetchall():
    print(f"{row[0]:12s} | {row[1]:7s} | fetched={row[2]:3d} | new={row[3]:3d} | {row[4][:60]}")

print('\n--- 清理测试用户 ---')
cur.execute("SELECT id, email FROM users WHERE email LIKE '%@test.com'")
rows = cur.fetchall()
for uid, email in rows:
    cur.execute('DELETE FROM sessions WHERE user_id = ?', (uid,))
    cur.execute('DELETE FROM favorites WHERE user_id = ?', (uid,))
    cur.execute('DELETE FROM users WHERE id = ?', (uid,))
    print('cleaned:', email)
db.commit()

cur.execute('SELECT COUNT(*) FROM articles')
print('articles total now:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM users')
print('users now:', cur.fetchone()[0])
db.close()
