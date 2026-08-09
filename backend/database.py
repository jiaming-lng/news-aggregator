"""
资讯聚合网站 - 数据库模块
使用 SQLite 存储资讯数据和爬取日志
"""

import sqlite3
import os
from datetime import datetime, timedelta

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'news.db')


def get_db():
    """获取数据库连接"""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            source_platform TEXT NOT NULL,
            category TEXT NOT NULL,
            source_url TEXT NOT NULL DEFAULT '',
            author TEXT DEFAULT '',
            published_at TIMESTAMP NOT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            view_count INTEGER DEFAULT 0,
            is_hot BOOLEAN DEFAULT 0,
            thumbnail_url TEXT DEFAULT '',
            keywords TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS crawl_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'running',
            articles_fetched INTEGER DEFAULT 0,
            articles_new INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
        CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source_platform);
        CREATE INDEX IF NOT EXISTS idx_articles_hot ON articles(is_hot);

        CREATE TABLE IF NOT EXISTS blog_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            excerpt TEXT DEFAULT '',
            author TEXT DEFAULT 'TechNews',
            category TEXT DEFAULT 'tech',
            status TEXT DEFAULT 'published',
            views INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_blog_status ON blog_posts(status);
        CREATE INDEX IF NOT EXISTS idx_blog_created ON blog_posts(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_blog_category ON blog_posts(category);

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            article_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
            UNIQUE(user_id, article_id)
        );

        CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
        CREATE INDEX IF NOT EXISTS idx_favorites_article ON favorites(article_id);
    """)

    conn.commit()
    conn.close()


def insert_article(title, summary, source_platform, category, source_url='',
                   author='', published_at=None, thumbnail_url='', keywords=''):
    """插入文章，自动去重（基于 source_url 或 title）"""
    conn = get_db()
    cursor = conn.cursor()

    if published_at is None:
        published_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 去重检查：先查 source_url，再查 title（双保险）
    if source_url:
        existing = cursor.execute(
            "SELECT id FROM articles WHERE source_url = ? OR title = ?", (source_url, title)
        ).fetchone()
    else:
        existing = cursor.execute(
            "SELECT id FROM articles WHERE title = ?", (title,)
        ).fetchone()

    if existing:
        conn.close()
        return None  # 已存在，跳过

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        INSERT INTO articles (title, summary, source_platform, category, source_url,
                              author, published_at, fetched_at, thumbnail_url, keywords)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, summary, source_platform, category, source_url,
          author, published_at, now_str, thumbnail_url, keywords))

    conn.commit()
    article_id = cursor.lastrowid
    conn.close()
    return article_id


def get_articles(category=None, search=None, sort='latest', page=1, limit=20):
    """查询文章列表，支持分类筛选、关键词搜索、排序和分页"""
    conn = get_db()
    cursor = conn.cursor()

    conditions = []
    params = []

    if category and category != 'all':
        conditions.append("category = ?")
        params.append(category)

    if search:
        conditions.append("(title LIKE ? OR summary LIKE ? OR keywords LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    if sort == 'hot':
        order = "view_count DESC, published_at DESC"
    else:
        order = "published_at DESC"

    # 获取总数
    count_sql = f"SELECT COUNT(*) FROM articles {where_clause}"
    total = cursor.execute(count_sql, params).fetchone()[0]

    # 分页查询
    offset = (page - 1) * limit
    query_sql = f"""
        SELECT * FROM articles {where_clause}
        ORDER BY {order}
        LIMIT ? OFFSET ?
    """
    rows = cursor.execute(query_sql, params + [limit, offset]).fetchall()

    articles = [dict(row) for row in rows]
    conn.close()

    return {
        'articles': articles,
        'total': total,
        'page': page,
        'limit': limit,
        'total_pages': max(1, (total + limit - 1) // limit)
    }


def get_hot_articles(limit=10):
    """获取热门推荐文章"""
    conn = get_db()
    cursor = conn.cursor()

    rows = cursor.execute("""
        SELECT * FROM articles
        WHERE is_hot = 1 OR view_count > 0
        ORDER BY view_count DESC, published_at DESC
        LIMIT ?
    """, (limit,)).fetchall()

    articles = [dict(row) for row in rows]
    conn.close()
    return articles


def increment_view(article_id):
    """增加文章浏览次数"""
    conn = get_db()
    conn.execute("UPDATE articles SET view_count = view_count + 1 WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()


def get_article_by_id(article_id):
    """根据 ID 获取单篇文章"""
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute(
        "SELECT * FROM articles WHERE id = ?", (article_id,)
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_related_articles(article_id, category=None, platform=None, limit=5):
    """获取相关文章（同分类或同平台，排除自身）"""
    conn = get_db()
    cursor = conn.cursor()

    conditions = ["id != ?"]
    params = [article_id]

    if category:
        conditions.append("category = ?")
        params.append(category)

    query_sql = f"""
        SELECT * FROM articles
        WHERE {' AND '.join(conditions)}
        ORDER BY published_at DESC
        LIMIT ?
    """
    rows = cursor.execute(query_sql, params + [limit]).fetchall()
    articles = [dict(row) for row in rows]
    conn.close()
    return articles


def get_stats():
    """获取统计数据"""
    conn = get_db()
    cursor = conn.cursor()

    total_articles = cursor.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

    today = datetime.now().strftime('%Y-%m-%d')
    today_articles = cursor.execute(
        "SELECT COUNT(*) FROM articles WHERE DATE(fetched_at) = ?", (today,)
    ).fetchone()[0]

    # 按分类统计
    by_category = {}
    for row in cursor.execute(
        "SELECT category, COUNT(*) as cnt FROM articles GROUP BY category"
    ).fetchall():
        by_category[row['category']] = row['cnt']

    # 按平台统计
    by_platform = {}
    for row in cursor.execute(
        "SELECT source_platform, COUNT(*) as cnt FROM articles GROUP BY source_platform"
    ).fetchall():
        by_platform[row['source_platform']] = row['cnt']

    # 爬取统计
    total_crawls = cursor.execute("SELECT COUNT(*) FROM crawl_logs").fetchone()[0]
    success_crawls = cursor.execute(
        "SELECT COUNT(*) FROM crawl_logs WHERE status = 'success'"
    ).fetchone()[0]

    # 最近一周每日新增
    daily_new = {}
    for row in cursor.execute("""
        SELECT DATE(fetched_at) as day, COUNT(*) as cnt
        FROM articles
        WHERE fetched_at >= DATE('now', '-7 days')
        GROUP BY day
        ORDER BY day
    """).fetchall():
        daily_new[row['day']] = row['cnt']

    conn.close()

    return {
        'total_articles': total_articles,
        'today_articles': today_articles,
        'by_category': by_category,
        'by_platform': by_platform,
        'total_crawls': total_crawls,
        'success_crawls': success_crawls,
        'daily_new': daily_new
    }


def insert_crawl_log(platform, status='running', articles_fetched=0, articles_new=0, error_message=''):
    """插入爬取日志（started_at 显式写入本地时间，与 completed_at 时区统一）"""
    conn = get_db()
    cursor = conn.cursor()

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        INSERT INTO crawl_logs (platform, status, articles_fetched, articles_new, error_message, started_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (platform, status, articles_fetched, articles_new, error_message, now_str))

    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id


def update_crawl_log(log_id, status, articles_fetched=None, articles_new=None, error_message=None):
    """更新爬取日志"""
    conn = get_db()
    cursor = conn.cursor()

    updates = ["status = ?", "completed_at = ?"]
    params = [status, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]

    if articles_fetched is not None:
        updates.append("articles_fetched = ?")
        params.append(articles_fetched)
    if articles_new is not None:
        updates.append("articles_new = ?")
        params.append(articles_new)
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)

    params.append(log_id)
    cursor.execute(
        f"UPDATE crawl_logs SET {', '.join(updates)} WHERE id = ?", params
    )

    conn.commit()
    conn.close()


def get_crawl_logs(limit=20):
    """获取最近的爬取日志"""
    conn = get_db()
    cursor = conn.cursor()

    rows = cursor.execute(
        "SELECT * FROM crawl_logs ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall()

    logs = [dict(row) for row in rows]
    conn.close()
    return logs


def cleanup_old_articles(days=30):
    """清理超过指定天数的过期文章，返回删除条数"""
    conn = get_db()
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')

    cursor = conn.execute("DELETE FROM articles WHERE published_at < ?", (cutoff,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted


# ============================================================
# 博客文章 CRUD
# ============================================================

def get_blog_posts(status=None, category=None, page=1, limit=10):
    """获取博客文章列表，支持按状态/分类筛选和分页"""
    conn = get_db()
    cursor = conn.cursor()

    conditions = []
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    else:
        # 默认只查已发布的
        conditions.append("status = 'published'")

    if category and category != 'all':
        conditions.append("category = ?")
        params.append(category)

    where_clause = "WHERE " + " AND ".join(conditions)

    total = cursor.execute(
        f"SELECT COUNT(*) FROM blog_posts {where_clause}", params
    ).fetchone()[0]

    offset = (page - 1) * limit
    rows = cursor.execute(
        f"""SELECT * FROM blog_posts {where_clause}
            ORDER BY created_at DESC LIMIT ? OFFSET ?""",
        params + [limit, offset]
    ).fetchall()

    posts = [dict(row) for row in rows]
    conn.close()

    return {
        'posts': posts,
        'total': total,
        'page': page,
        'limit': limit,
        'total_pages': max(1, (total + limit - 1) // limit)
    }


def get_blog_post(post_id):
    """获取单篇博客文章"""
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute(
        "SELECT * FROM blog_posts WHERE id = ?", (post_id,)
    ).fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def create_blog_post(title, content, excerpt='', author='TechNews', category='tech', status='published'):
    """创建博客文章，返回新文章 ID"""
    conn = get_db()
    cursor = conn.cursor()

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not excerpt:
        # 自动生成摘要：取前 200 字符的纯文本
        import re
        plain = re.sub(r'<[^>]+>', '', content)
        excerpt = plain[:200].strip()
        if len(plain) > 200:
            excerpt += '...'

    cursor.execute("""
        INSERT INTO blog_posts (title, content, excerpt, author, category, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, content, excerpt, author, category, status, now, now))

    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return post_id


def update_blog_post(post_id, title=None, content=None, excerpt=None, category=None, status=None):
    """更新博客文章"""
    conn = get_db()
    cursor = conn.cursor()

    updates = []
    params = []

    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if content is not None:
        updates.append("content = ?")
        params.append(content)
        # 如果没有手动设置 excerpt，自动生成
        if excerpt is None:
            import re
            plain = re.sub(r'<[^>]+>', '', content)
            excerpt = plain[:200].strip()
            if len(plain) > 200:
                excerpt += '...'
    if excerpt is not None:
        updates.append("excerpt = ?")
        params.append(excerpt)
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    if status is not None:
        updates.append("status = ?")
        params.append(status)

    updates.append("updated_at = ?")
    params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    params.append(post_id)

    cursor.execute(
        f"UPDATE blog_posts SET {', '.join(updates)} WHERE id = ?", params
    )

    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def delete_blog_post(post_id):
    """删除博客文章"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blog_posts WHERE id = ?", (post_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def increment_blog_view(post_id):
    """增加博客文章浏览次数"""
    conn = get_db()
    conn.execute("UPDATE blog_posts SET views = views + 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()


# ============================================================
# 用户系统 CRUD
# ============================================================

def create_user(email, username, password_hash):
    """创建用户，返回新用户 ID。邮箱已存在则返回 None"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (email, username, password_hash)
            VALUES (?, ?, ?)
        """, (email, username, password_hash))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def get_user_by_email(email):
    """根据邮箱获取用户"""
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    """根据 ID 获取用户（不含密码）"""
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute(
        "SELECT id, email, username, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================
# 会话管理
# ============================================================

SESSION_DURATION_DAYS = 7


def create_session(user_id, token):
    """创建登录会话"""
    conn = get_db()
    expires_at = (datetime.now() + timedelta(days=SESSION_DURATION_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at)
    )
    conn.commit()
    conn.close()


def get_session(token):
    """根据 token 获取有效会话，返回用户 ID 或 None"""
    if not token:
        return None
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute(
        "SELECT user_id, expires_at FROM sessions WHERE token = ?", (token,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    # 检查是否过期
    try:
        expires = datetime.strptime(row['expires_at'], '%Y-%m-%d %H:%M:%S')
        if expires < datetime.now():
            delete_session(token)
            return None
    except (ValueError, TypeError):
        return None
    return row['user_id']


def delete_session(token):
    """删除会话（登出）"""
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


# ============================================================
# 收藏管理
# ============================================================

def add_favorite(user_id, article_id):
    """添加收藏，返回是否新增成功"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO favorites (user_id, article_id) VALUES (?, ?)",
            (user_id, article_id)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def remove_favorite(user_id, article_id):
    """取消收藏"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM favorites WHERE user_id = ? AND article_id = ?",
        (user_id, article_id)
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_favorites(user_id, page=1, limit=20):
    """获取用户收藏列表"""
    conn = get_db()
    cursor = conn.cursor()

    total = cursor.execute(
        "SELECT COUNT(*) FROM favorites WHERE user_id = ?", (user_id,)
    ).fetchone()[0]

    offset = (page - 1) * limit
    rows = cursor.execute("""
        SELECT a.* FROM articles a
        INNER JOIN favorites f ON a.id = f.article_id
        WHERE f.user_id = ?
        ORDER BY f.created_at DESC
        LIMIT ? OFFSET ?
    """, (user_id, limit, offset)).fetchall()

    articles = [dict(row) for row in rows]
    conn.close()

    return {
        'articles': articles,
        'total': total,
        'page': page,
        'limit': limit,
        'total_pages': max(1, (total + limit - 1) // limit)
    }


def get_favorited_ids(user_id, article_ids):
    """批量查询哪些文章已被用户收藏，返回已收藏的 article_id 集合"""
    if not article_ids:
        return set()
    conn = get_db()
    cursor = conn.cursor()
    placeholders = ','.join('?' * len(article_ids))
    rows = cursor.execute(
        f"SELECT article_id FROM favorites WHERE user_id = ? AND article_id IN ({placeholders})",
        [user_id] + list(article_ids)
    ).fetchall()
    conn.close()
    return {row['article_id'] for row in rows}
