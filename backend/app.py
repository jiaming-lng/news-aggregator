"""
资讯聚合网站 - Flask 后端服务
提供 RESTful API 并托管前端静态文件
支持 SSR 预渲染首页以提升 SEO 和首屏性能
"""

import os
import sys
import json
import gzip
import io
import html as html_module
import secrets
from datetime import datetime
from functools import wraps
from html.parser import HTMLParser

# 确保 backend 目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_from_directory, Response, redirect
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from database import (
    init_db, get_articles, get_hot_articles, get_stats, get_crawl_logs, increment_view,
    get_article_by_id, get_related_articles,
    get_blog_posts, get_blog_post, create_blog_post, update_blog_post, delete_blog_post, increment_blog_view,
    create_user, get_user_by_email, get_user_by_id, create_session, get_session, delete_session,
    add_favorite, remove_favorite, get_favorites, get_favorited_ids,
    check_rate_limit, clear_rate_limit
)
from crawler import seed_initial_data, start_scheduler, start_watchdog, run_crawl_job, check_crawler_health, scheduler_status, LAST_CRAWL_STALE_MINUTES
from backup import start_daily_backup

# 创建 Flask 应用，静态文件指向 CSS/JS 目录（HTML 模板单独管理）
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, 'templates')
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

# 静态资源版本号（修改静态文件时递增，用于缓存失效）
ASSET_VERSION = '13'

# 管理员邮箱白名单（逗号分隔），注册时命中会自动授予管理员角色
ADMIN_EMAILS = {
    e.strip().lower() for e in os.environ.get('ADMIN_EMAILS', '').split(',') if e.strip()
}


def _int_arg(name, default, min_value=1, max_value=100):
    """解析整数查询参数并限制范围，非法输入回退为默认值"""
    try:
        val = int(request.args.get(name, default))
    except (TypeError, ValueError):
        val = default
    return max(min_value, min(val, max_value))


def require_auth(f):
    """API 认证装饰器：未登录返回 401 JSON（装饰器在模块加载时即被引用，
    因此必须定义在第一个使用它的路由之前；_get_current_user 在请求时解析）"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = _get_current_user()
        if not user:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return wrapper


def require_admin(f):
    """API 管理员鉴权装饰器：未登录 401，普通用户 403"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = _get_current_user()
        if not user:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        if not user.get('is_admin'):
            return jsonify({'success': False, 'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return wrapper


# ============================================================
# SSR 渲染辅助函数
# ============================================================

_PLATFORM_COLORS = {
    'youtube': '#FF0000', 'tiktok': '#000000', 'github': '#6e5494',
    'hackernews': '#FF6600', 'bilibili': '#00A1D6', 'blog': '#0ea5e9',
    'reddit': '#FF4500', 'github_trending': '#24292f', 'ithome': '#e60012',
    'leiphone': '#00a383', 'sspai': '#e03e2d', 'solidot': '#ff6600',
    'oschina': '#d2691e',
}
_PLATFORM_ICONS = {
    'youtube': 'YT', 'tiktok': 'TT', 'github': 'GH', 'hackernews': 'HN',
    'bilibili': 'BL', 'blog': 'BG', 'reddit': 'RD', 'github_trending': 'GT',
    'ithome': 'IT', 'leiphone': 'LP', 'sspai': 'SP', 'solidot': 'SD',
    'oschina': 'OS',
}
_PLATFORM_NAMES = {
    'youtube': 'YouTube', 'tiktok': 'TikTok', 'github': 'GitHub',
    'hackernews': 'Hacker News', 'bilibili': 'Bilibili', 'blog': 'Blog',
    'reddit': 'Reddit', 'github_trending': 'GitHub Trending',
    'ithome': 'IT之家', 'leiphone': '雷峰网', 'sspai': '少数派',
    'solidot': 'Solidot', 'oschina': '开源中国',
}
_CATEGORY_NAMES = {'tech': '科技', 'ai': 'AI', 'opensource': '开源'}


def _format_time(date_str):
    """格式化时间为相对时间"""
    if not date_str:
        return ''
    try:
        date = datetime.strptime(str(date_str), '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        try:
            date = datetime.fromisoformat(str(date_str))
        except (ValueError, TypeError):
            return str(date_str)[:10]
    now = datetime.now()
    diff_sec = (now - date).total_seconds()
    diff_min = int(diff_sec / 60)
    diff_hr = int(diff_sec / 3600)
    diff_day = int(diff_sec / 86400)

    if diff_min < 1:
        return '刚刚'
    if diff_min < 60:
        return f'{diff_min} 分钟前'
    if diff_hr < 24:
        return f'{diff_hr} 小时前'
    if diff_day < 7:
        return f'{diff_day} 天前'
    return str(date_str)[:10]


def _format_number(n):
    if n >= 10000:
        return f'{n / 10000:.1f}w'
    if n >= 1000:
        return f'{n / 1000:.1f}k'
    return str(n)


def _render_article_card(article):
    """服务端渲染单条文章卡片 HTML"""
    platform = article.get('source_platform', '')
    platform_color = _PLATFORM_COLORS.get(platform, '#64748b')
    platform_icon = _PLATFORM_ICONS.get(platform, '##')
    platform_name = _PLATFORM_NAMES.get(platform, platform)
    category = article.get('category', '')
    category_name = _CATEGORY_NAMES.get(category, category)
    time_str = _format_time(article.get('published_at'))
    safe_url = html_module.escape(article.get('source_url') or '#')
    title = html_module.escape(article.get('title', ''))
    summary = html_module.escape(article.get('summary') or '暂无摘要')
    author = article.get('author', '')
    view_count = article.get('view_count', 0)
    article_id = article.get('id', '')

    author_html = f'<span class="meta-item">by {html_module.escape(author)}</span>' if author else ''
    view_html = f'<span class="meta-item">{_format_number(view_count)} views</span>' if view_count and view_count > 0 else ''

    detail_url = f'/article/{article_id}'

    return f"""      <div class="article-card" data-id="{article_id}">
        <div class="card-header">
          <span class="platform-badge" style="background: {platform_color}">
            {platform_icon} {platform_name}
          </span>
          <span class="category-tag {category}">{category_name}</span>
          <button class="fav-btn" data-fav-id="{article_id}" title="收藏" aria-label="收藏文章">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"/></svg>
          </button>
        </div>
        <a href="{detail_url}" class="article-title-link" data-id="{article_id}">
          <h3 class="article-title">{title}</h3>
        </a>
        <p class="article-summary">{summary}</p>
        <div class="article-meta">
          {author_html}
          <span class="meta-item">{time_str}</span>
          {view_html}
        </div>
        <div class="article-actions">
          <a href="{detail_url}" class="btn-source">阅读详情</a>
          <a href="{safe_url}" target="_blank" rel="noopener" class="btn-external" data-id="{article_id}">查看原文</a>
        </div>
      </div>"""


def _render_hot_card(article):
    """服务端渲染热门卡片 HTML"""
    platform = article.get('source_platform', '')
    platform_color = _PLATFORM_COLORS.get(platform, '#64748b')
    platform_icon = _PLATFORM_ICONS.get(platform, '##')
    platform_name = _PLATFORM_NAMES.get(platform, platform)
    category = article.get('category', '')
    category_name = _CATEGORY_NAMES.get(category, category)
    time_str = _format_time(article.get('published_at'))
    safe_url = html_module.escape(article.get('source_url') or '#')
    title = html_module.escape(article.get('title', ''))

    return f"""      <a href="{safe_url}" target="_blank" rel="noopener" class="hot-card">
        <span class="hot-badge">HOT</span>
        <span class="hot-platform-badge" style="background: {platform_color}">
          {platform_icon} {platform_name}
        </span>
        <h4 class="hot-title">{title}</h4>
        <div class="hot-meta">
          <span>{category_name}</span>
          <span>·</span>
          <span>{time_str}</span>
        </div>
      </a>"""


def _render_pagination(page, total_pages):
    """服务端渲染分页 HTML"""
    if total_pages <= 1:
        return ''

    parts = []
    disabled_prev = ' disabled' if page <= 1 else ''
    parts.append(f'<button class="page-btn" data-page="{page - 1}"{disabled_prev}>← 上一页</button>')

    start_page = max(1, page - 2)
    end_page = min(total_pages, page + 2)

    if start_page > 1:
        parts.append('<button class="page-btn" data-page="1">1</button>')
        if start_page > 2:
            parts.append('<span class="page-ellipsis">...</span>')

    for i in range(start_page, end_page + 1):
        cls = 'page-btn active' if i == page else 'page-btn'
        parts.append(f'<button class="{cls}" data-page="{i}">{i}</button>')

    if end_page < total_pages:
        if end_page < total_pages - 1:
            parts.append('<span class="page-ellipsis">...</span>')
        parts.append(f'<button class="page-btn" data-page="{total_pages}">{total_pages}</button>')

    disabled_next = ' disabled' if page >= total_pages else ''
    parts.append(f'<button class="page-btn" data-page="{page + 1}"{disabled_next}>下一页 →</button>')

    return '\n'.join(parts)


# ============================================================
# 页面路由（含 SSR 预渲染）
# ============================================================

@app.route('/')
def index():
    """资讯首页 - SSR 预渲染第一页数据，提升 SEO 和首屏速度"""
    html_path = os.path.join(TEMPLATES_DIR, 'index.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 添加资源版本号
    html_content = html_content.replace(
        'href="/css/style.css"',
        f'href="/css/style.css?v={ASSET_VERSION}"'
    )
    html_content = html_content.replace(
        'src="/js/app.js"',
        f'src="/js/app.js?v={ASSET_VERSION}"'
    )
    html_content = html_content.replace(
        'src="/js/theme.js"',
        f'src="/js/theme.js?v={ASSET_VERSION}"'
    )
    html_content = html_content.replace(
        'src="/js/auth.js"',
        f'src="/js/auth.js?v={ASSET_VERSION}"'
    )
    html_content = html_content.replace(
        'src="/js/crawler-status.js"',
        f'src="/js/crawler-status.js?v={ASSET_VERSION}"'
    )

    try:
        # 获取第一页文章和热门文章
        articles_data = get_articles(category='all', search='', sort='latest', page=1, limit=20)
        hot_articles = get_hot_articles(limit=10)

        articles = articles_data['articles']
        total = articles_data['total']
        total_pages = articles_data['total_pages']

        # 渲染文章卡片
        if articles:
            articles_html = '\n'.join(_render_article_card(a) for a in articles)
        else:
            articles_html = '<div class="empty-state"><div class="empty-icon">--</div><div class="empty-text">暂无资讯</div></div>'

        # 渲染热门卡片
        hot_html = '\n'.join(_render_hot_card(a) for a in hot_articles) if hot_articles else ''

        # 渲染分页
        pagination_html = _render_pagination(1, total_pages)

        # 注入 SSR 数据（供 JS 初始化状态）
        ssr_data = {
            'articles': articles,
            'hot_articles': hot_articles,
            'total': total,
            'total_pages': total_pages,
            'page': 1,
            'category': 'all',
            'sort': 'latest',
            'search': ''
        }
        ssr_json = json.dumps(ssr_data, ensure_ascii=False, default=str)

        # 替换模板占位符
        html_content = html_content.replace('<!-- SSR:ARTICLES -->', articles_html)
        html_content = html_content.replace('<!-- SSR:HOT -->', hot_html)
        html_content = html_content.replace('<!-- SSR:PAGINATION -->', pagination_html)
        html_content = html_content.replace('<!-- SSR:DATA -->', f'<script type="application/json" id="ssr-data">{ssr_json}</script>')
    except Exception as e:
        print(f"[SSR] 预渲染失败，降级为 CSR: {e}")
        html_content = html_content.replace('<!-- SSR:DATA -->', '')

    return Response(html_content, content_type='text/html; charset=utf-8')


@app.route('/admin')
def admin():
    """管理后台（仅管理员）"""
    user = _get_current_user()
    if not user or not user.get('is_admin'):
        return redirect('/')
    return send_from_directory(TEMPLATES_DIR, 'admin.html')


@app.route('/article/<int:article_id>')
def article_detail(article_id):
    """文章详情页"""
    return send_from_directory(TEMPLATES_DIR, 'article-detail.html')


@app.route('/favorites')
def favorites():
    """用户收藏页"""
    return send_from_directory(TEMPLATES_DIR, 'favorites.html')


@app.route('/blog')
def blog():
    """博客列表页"""
    return send_from_directory(TEMPLATES_DIR, 'blog.html')


@app.route('/blog/<int:post_id>')
def blog_detail(post_id):
    """博客详情页"""
    return send_from_directory(TEMPLATES_DIR, 'blog-detail.html')


@app.route('/admin/blog')
def admin_blog():
    """博客管理页（仅管理员）"""
    user = _get_current_user()
    if not user or not user.get('is_admin'):
        return redirect('/')
    return send_from_directory(TEMPLATES_DIR, 'admin-blog.html')


# ============================================================
# API 路由
# ============================================================

@app.route('/api/articles', methods=['GET'])
def api_articles():
    """获取文章列表"""
    category = request.args.get('category', 'all')
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'latest')
    page = _int_arg('page', 1)
    limit = _int_arg('limit', 20)

    result = get_articles(category=category, search=search, sort=sort, page=page, limit=limit)
    return jsonify({'success': True, 'data': result})


@app.route('/api/articles/hot', methods=['GET'])
def api_hot_articles():
    """获取热门推荐文章"""
    limit = _int_arg('limit', 10, max_value=50)
    articles = get_hot_articles(limit=limit)
    return jsonify({'success': True, 'data': articles})


@app.route('/api/home', methods=['GET'])
def api_home():
    """合并接口：一次性返回文章列表 + 热门推荐，减少首屏请求数"""
    category = request.args.get('category', 'all')
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'latest')
    page = _int_arg('page', 1)
    limit = _int_arg('limit', 20)

    articles_data = get_articles(category=category, search=search, sort=sort, page=page, limit=limit)
    hot_articles = get_hot_articles(limit=10)

    return jsonify({
        'success': True,
        'data': {
            'articles': articles_data,
            'hot': hot_articles
        }
    })


@app.route('/api/articles/<int:article_id>/view', methods=['POST'])
def api_view_article(article_id):
    """记录文章浏览"""
    increment_view(article_id)
    return jsonify({'success': True})


@app.route('/api/articles/<int:article_id>', methods=['GET'])
def api_article_detail(article_id):
    """获取单篇文章详情 + 相关文章"""
    article = get_article_by_id(article_id)
    if not article:
        return jsonify({'success': False, 'error': '文章不存在'}), 404

    # 增加浏览次数
    increment_view(article_id)

    # 获取相关文章（同分类）
    related = get_related_articles(
        article_id,
        category=article.get('category'),
        limit=5
    )

    return jsonify({
        'success': True,
        'data': {
            'article': article,
            'related': related
        }
    })


@app.route('/api/stats', methods=['GET'])
@require_admin
def api_stats():
    """获取数据统计"""
    stats = get_stats()
    return jsonify({'success': True, 'data': stats})


@app.route('/api/crawl-logs', methods=['GET'])
@require_admin
def api_crawl_logs():
    """获取爬取日志"""
    limit = _int_arg('limit', 20)
    logs = get_crawl_logs(limit=limit)
    return jsonify({'success': True, 'data': logs})


@app.route('/api/crawl/trigger', methods=['POST'])
@require_admin
def api_trigger_crawl():
    """手动触发一次爬取"""
    try:
        fetched, new = run_crawl_job()
        return jsonify({
            'success': True,
            'data': {
                'total_fetched': fetched,
                'total_new': new,
                'message': f'爬取完成！共抓取 {fetched} 条，新增 {new} 条'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/crawler/status')
def api_crawler_status():
    """爬虫健康状态（公开，供页面告警显示）"""
    healthy, minutes, last = check_crawler_health()
    status = scheduler_status()
    return jsonify({
        'success': True,
        'data': {
            'healthy': healthy,
            'minutes_since_last_crawl': minutes,
            'last_crawl_time': last,
            'stale_threshold_minutes': LAST_CRAWL_STALE_MINUTES,
            'scheduler_running': status['scheduler_running'],
            'scheduler_thread_alive': status['scheduler_thread_alive'],
        }
    })


@app.route('/api/platforms', methods=['GET'])
def api_platforms():
    """获取可用的平台和分类信息"""
    return jsonify({
        'success': True,
        'data': {
            'platforms': [
                {'id': 'github', 'name': 'GitHub', 'icon': 'GH', 'color': '#6e5494'},
                {'id': 'hackernews', 'name': 'Hacker News', 'icon': 'HN', 'color': '#FF6600'},
                {'id': 'bilibili', 'name': 'Bilibili', 'icon': 'BL', 'color': '#00A1D6'},
                {'id': 'blog', 'name': 'Blog', 'icon': 'BG', 'color': '#0ea5e9'},
                {'id': 'reddit', 'name': 'Reddit', 'icon': 'RD', 'color': '#FF4500'},
                {'id': 'youtube', 'name': 'YouTube', 'icon': 'YT', 'color': '#FF0000'},
                {'id': 'github_trending', 'name': 'GitHub Trending', 'icon': 'GT', 'color': '#24292f'},
                {'id': 'ithome', 'name': 'IT之家', 'icon': 'IT', 'color': '#e60012'},
                {'id': 'leiphone', 'name': '雷峰网', 'icon': 'LP', 'color': '#00a383'},
                {'id': 'sspai', 'name': '少数派', 'icon': 'SP', 'color': '#e03e2d'},
                {'id': 'solidot', 'name': 'Solidot', 'icon': 'SD', 'color': '#ff6600'},
                {'id': 'oschina', 'name': '开源中国', 'icon': 'OS', 'color': '#d2691e'},
            ],
            'categories': [
                {'id': 'all', 'name': '全部'},
                {'id': 'tech', 'name': '科技'},
                {'id': 'ai', 'name': 'AI'},
                {'id': 'opensource', 'name': '开源'}
            ]
        }
    })


# ============================================================
# 用户认证 API
# ============================================================

def _client_ip():
    """获取客户端 IP；仅当配置了受信代理时才信任 X-Forwarded-For"""
    if os.environ.get('USE_X_FORWARDED_FOR', '0') == '1':
        xff = request.headers.get('X-Forwarded-For', '')
        if xff:
            return xff.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def _get_current_user():
    """从请求头提取 token 并返回用户信息，未登录返回 None"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[7:]
    user_id = get_session(token)
    if not user_id:
        return None
    return get_user_by_id(user_id)


@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """用户注册"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    email = (data.get('email') or '').strip().lower()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    # 注册限流：同一 IP 每小时最多 10 次
    allowed, _, retry_after = check_rate_limit(f'regip:{_client_ip()}', 10, 3600)
    if not allowed:
        return jsonify({'success': False, 'error': f'注册过于频繁，请 {retry_after} 秒后再试'}), 429

    # 输入验证
    if not email or '@' not in email:
        return jsonify({'success': False, 'error': '请输入有效的邮箱地址'}), 400
    if not username or len(username) < 2:
        return jsonify({'success': False, 'error': '用户名至少 2 个字符'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'error': '密码至少 6 个字符'}), 400

    # 检查邮箱是否已注册
    existing = get_user_by_email(email)
    if existing:
        return jsonify({'success': False, 'error': '该邮箱已注册'}), 409

    # 创建用户
    password_hash = generate_password_hash(password)
    user_id = create_user(
        email, username, password_hash,
        is_admin=1 if email in ADMIN_EMAILS else 0
    )
    if not user_id:
        return jsonify({'success': False, 'error': '注册失败，请重试'}), 500

    # 自动登录：创建会话
    token = secrets.token_urlsafe(32)
    create_session(user_id, token)

    user = get_user_by_id(user_id)
    return jsonify({
        'success': True,
        'data': {
            'token': token,
            'user': user
        }
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """用户登录"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'}), 400

    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'success': False, 'error': '邮箱和密码不能为空'}), 400

    # 登录限流：按邮箱（5 次/15 分钟）和 IP（20 次/15 分钟）双重限制
    email_key = f'login:{email}'
    for key, max_attempts, window in [
        (email_key, 5, 15 * 60),
        (f'loginip:{_client_ip()}', 20, 15 * 60),
    ]:
        allowed, _, retry_after = check_rate_limit(key, max_attempts, window)
        if not allowed:
            return jsonify({'success': False, 'error': f'尝试过于频繁，请 {retry_after} 秒后再试'}), 429

    user = get_user_by_email(email)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'success': False, 'error': '邮箱或密码错误'}), 401

    # 登录成功，清除该邮箱的失败计数
    clear_rate_limit(email_key)

    # 创建会话
    token = secrets.token_urlsafe(32)
    create_session(user['id'], token)

    # 返回用户信息（不含密码）
    safe_user = get_user_by_id(user['id'])
    return jsonify({
        'success': True,
        'data': {
            'token': token,
            'user': safe_user
        }
    })


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """用户登出"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        delete_session(token)
    return jsonify({'success': True})


@app.route('/api/auth/me', methods=['GET'])
def api_me():
    """获取当前登录用户信息"""
    user = _get_current_user()
    if not user:
        return jsonify({'success': False, 'error': '未登录'}), 401
    return jsonify({'success': True, 'data': user})


# ============================================================
# 收藏 API
# ============================================================

@app.route('/api/favorites', methods=['GET'])
def api_favorites_list():
    """获取当前用户的收藏列表"""
    user = _get_current_user()
    if not user:
        return jsonify({'success': False, 'error': '请先登录'}), 401

    page = _int_arg('page', 1)
    limit = _int_arg('limit', 20)
    result = get_favorites(user['id'], page=page, limit=limit)
    return jsonify({'success': True, 'data': result})


@app.route('/api/favorites/<int:article_id>', methods=['POST'])
def api_add_favorite(article_id):
    """添加收藏"""
    user = _get_current_user()
    if not user:
        return jsonify({'success': False, 'error': '请先登录'}), 401

    # 检查文章是否存在
    article = get_article_by_id(article_id)
    if not article:
        return jsonify({'success': False, 'error': '文章不存在'}), 404

    added = add_favorite(user['id'], article_id)
    return jsonify({'success': True, 'data': {'favorited': True, 'added': added}})


@app.route('/api/favorites/<int:article_id>', methods=['DELETE'])
def api_remove_favorite(article_id):
    """取消收藏"""
    user = _get_current_user()
    if not user:
        return jsonify({'success': False, 'error': '请先登录'}), 401

    removed = remove_favorite(user['id'], article_id)
    return jsonify({'success': True, 'data': {'favorited': False, 'removed': removed}})


# ============================================================
# 博客文章 API
# ============================================================

# 服务端博客 HTML 消毒：白名单标签 + 白名单属性 + 安全 URL，防止存储型 XSS
_ALLOWED_BLOG_TAGS = {
    'p', 'br', 'strong', 'em', 'b', 'i', 'u', 's', 'h2', 'h3', 'h4',
    'ul', 'ol', 'li', 'a', 'pre', 'code', 'blockquote', 'hr',
    'span', 'div', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
}
_ALLOWED_BLOG_ATTRS = {
    'a': {'href', 'title'},
    'img': {'src', 'alt', 'title'},
    'th': {'colspan', 'rowspan'},
    'td': {'colspan', 'rowspan'},
}
_SAFE_URL_SCHEMES = ('http', 'https', 'mailto')


def _safe_blog_url(value):
    value = (value or '').strip()
    if not value or any(ch.isspace() for ch in value):
        return ''
    if ':' in value:
        scheme = value.split(':', 1)[0].lower()
        return value if scheme in _SAFE_URL_SCHEMES else ''
    return value  # 相对链接（如 /blog/1）


class _BlogSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._stack = []  # (tag, allowed) 元组栈

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag not in _ALLOWED_BLOG_TAGS:
            self._stack.append((tag, False))
            return
        self._stack.append((tag, True))
        self.parts.append(self._render_tag(tag, attrs))

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if tag not in _ALLOWED_BLOG_TAGS:
            return
        self.parts.append(self._render_tag(tag, attrs, self_closing=True))

    def handle_endtag(self, tag):
        tag = tag.lower()
        allowed = False
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                _, allowed = self._stack.pop(i)
                break
        if allowed:
            self.parts.append(f'</{tag}>')

    def handle_data(self, data):
        # 被跳过的标签（script/iframe 等）内部内容不输出
        if any(not allowed for _, allowed in self._stack):
            return
        self.parts.append(html_module.escape(data))

    def _render_tag(self, tag, attrs, self_closing=False):
        allowed = _ALLOWED_BLOG_ATTRS.get(tag, set())
        rendered = ['<', tag]
        has_src = False
        has_href = False
        for name, value in attrs:
            name = name.lower()
            if name not in allowed or value is None:
                continue
            if name == 'href':
                value = _safe_blog_url(value)
                if not value:
                    continue
                has_href = True
            elif name == 'src':
                if not value.startswith(('http://', 'https://')):
                    continue
                has_src = True
            rendered.append(f' {name}="{html_module.escape(value, quote=True)}"')
        if tag == 'img' and not has_src:
            return ''
        if tag == 'a' and has_href:
            rendered.append(' rel="noopener noreferrer" target="_blank"')
        rendered.append('/>' if self_closing else '>')
        return ''.join(rendered)


def _sanitize_blog_html(raw):
    """服务端博客内容消毒入口"""
    if not raw:
        return ''
    parser = _BlogSanitizer()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        return ''
    return ''.join(parser.parts)


@app.route('/api/blog/posts', methods=['GET'])
def api_blog_posts():
    """获取博客文章列表"""
    status = request.args.get('status', 'published')
    category = request.args.get('category', 'all')
    page = _int_arg('page', 1)
    limit = _int_arg('limit', 10)

    result = get_blog_posts(status=status, category=category, page=page, limit=limit)
    return jsonify({'success': True, 'data': result})


@app.route('/api/blog/posts/<int:post_id>', methods=['GET'])
def api_blog_post_detail(post_id):
    """获取单篇博客文章"""
    post = get_blog_post(post_id)
    if not post:
        return jsonify({'success': False, 'error': '文章不存在'}), 404

    # 增加浏览次数
    increment_blog_view(post_id)

    return jsonify({'success': True, 'data': post})


@app.route('/api/blog/posts', methods=['POST'])
@require_admin
def api_create_blog_post():
    """创建博客文章"""
    data = request.get_json()
    if not data or not data.get('title') or not data.get('content'):
        return jsonify({'success': False, 'error': '标题和内容不能为空'}), 400

    content = _sanitize_blog_html(data['content'])
    if not content.strip():
        return jsonify({'success': False, 'error': '内容不能为空'}), 400

    post_id = create_blog_post(
        title=(data.get('title') or '').strip()[:200],
        content=content,
        excerpt=(data.get('excerpt') or '')[:500],
        author=(data.get('author') or 'TechNews')[:50],
        category=data.get('category', 'tech'),
        status=data.get('status', 'published'),
    )

    return jsonify({'success': True, 'data': {'id': post_id}}), 201


@app.route('/api/blog/posts/<int:post_id>', methods=['PUT'])
@require_admin
def api_update_blog_post(post_id):
    """更新博客文章"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '无更新数据'}), 400

    if 'title' in data and not (data.get('title') or '').strip():
        return jsonify({'success': False, 'error': '标题不能为空'}), 400

    content = data.get('content')
    if content is not None:
        content = _sanitize_blog_html(content)
        if not content.strip():
            return jsonify({'success': False, 'error': '内容不能为空'}), 400

    ok = update_blog_post(
        post_id,
        title=(data.get('title') or '').strip() if 'title' in data else None,
        content=content,
        excerpt=data.get('excerpt')[:500] if data.get('excerpt') is not None else None,
        category=data.get('category'),
        status=data.get('status'),
    )

    if not ok:
        return jsonify({'success': False, 'error': '文章不存在'}), 404

    return jsonify({'success': True})


@app.route('/api/blog/posts/<int:post_id>', methods=['DELETE'])
@require_admin
def api_delete_blog_post(post_id):
    """删除博客文章"""
    ok = delete_blog_post(post_id)
    if not ok:
        return jsonify({'success': False, 'error': '文章不存在'}), 404

    return jsonify({'success': True})


# ============================================================
# SEO 辅助文件
# ============================================================

# 站点基础 URL（用于 SEO 文件生成）
import os as _os
BASE_URL = _os.environ.get('BASE_URL', 'http://106.53.58.166:5000').rstrip('/')


@app.route('/robots.txt')
def robots():
    """搜索引擎爬虫规则"""
    body = f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\nSitemap: {BASE_URL}/sitemap.xml\n"
    return Response(body, content_type='text/plain; charset=utf-8')


@app.route('/sitemap.xml')
def sitemap():
    """站点地图"""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    # 首页
    lines.append('  <url>')
    lines.append(f'    <loc>{BASE_URL}/</loc>')
    lines.append('    <changefreq>30min</changefreq>')
    lines.append('    <priority>1.0</priority>')
    lines.append('  </url>')

    # 各分类页面
    for cat in ['tech', 'ai', 'opensource']:
        lines.append('  <url>')
        lines.append(f'    <loc>{BASE_URL}/?category={cat}</loc>')
        lines.append('    <changefreq>30min</changefreq>')
        lines.append('    <priority>0.8</priority>')
        lines.append('  </url>')

    # 博客页面
    lines.append('  <url>')
    lines.append(f'    <loc>{BASE_URL}/blog</loc>')
    lines.append('    <changefreq>daily</changefreq>')
    lines.append('    <priority>0.7</priority>')
    lines.append('  </url>')

    lines.append('</urlset>')
    return Response('\n'.join(lines), content_type='application/xml; charset=utf-8')


# ============================================================
# 缓存策略
# ============================================================

@app.after_request
def add_cache_headers(response):
    """为静态资源设置长缓存，HTML 设置不缓存"""
    path = request.path

    # 静态文件（带版本号查询参数）设置一年缓存
    if path.startswith('/css/') or path.startswith('/js/'):
        # 直接设置 header，避免 Flask 静态文件服务的 no-cache 干扰
        response.headers['Cache-Control'] = 'public, max-age=31536000'
    # HTML 页面不缓存（确保 SSR 内容始终最新）
    elif response.content_type and 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    # API 响应短缓存
    elif path.startswith('/api/'):
        response.headers['Cache-Control'] = 'public, max-age=60'

    return response


# ============================================================
# Gzip 压缩
# ============================================================

@app.after_request
def gzip_response(response):
    """对文本类响应（HTML/CSS/JS/JSON）启用 gzip 压缩，减小传输体积"""
    accept_encoding = request.headers.get('Accept-Encoding', '')
    if 'gzip' not in accept_encoding.lower():
        return response

    content_type = response.content_type or ''
    compressible_types = ('text/html', 'text/css', 'text/javascript',
                          'application/javascript', 'application/json',
                          'text/plain', 'application/xml')
    if not any(ct in content_type for ct in compressible_types):
        return response

    # direct_passthrough 模式（Flask 静态文件服务）跳过压缩
    # 静态文件已有一年缓存，首次下载后不再请求
    if response.direct_passthrough:
        return response

    data = response.get_data()

    # 太小的响应不压缩（压缩反而增大体积）
    if len(data) < 500:
        return response

    gzip_buffer = io.BytesIO()
    with gzip.GzipFile(mode='wb', fileobj=gzip_buffer, compresslevel=6) as f:
        f.write(data)

    response.set_data(gzip_buffer.getvalue())
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(response.get_data())
    response.headers['Vary'] = 'Accept-Encoding'

    return response


# ============================================================
# 应用启动
# ============================================================

def initialize():
    """应用初始化：建库、填充种子数据、启动定时爬取"""
    print("=" * 50)
    print("  TechNews 资讯聚合网站")
    print("=" * 50)

    init_db()
    print("[Init] 数据库初始化完成")

    seed_initial_data()
    print("[Init] 种子数据填充完成")

    start_scheduler(interval_minutes=30)
    print("[Init] 定时爬取已启动（间隔 30 分钟）")

    start_watchdog(check_interval_minutes=5)
    print("[Init] 爬虫看门狗已启动（自动检测并自愈）")

    start_daily_backup()
    print("[Init] 每日数据库备份已启动")

    print("=" * 50)


if __name__ == '__main__':
    # 初始化在启动前完成，避免首个请求阻塞
    initialize()
    print(f"\n  访问地址: {BASE_URL}")
    print(f"  管理后台: {BASE_URL}/admin\n")
    # 生产环境关闭 debug，本地开发可通过环境变量开启
    is_debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=is_debug, use_reloader=False)
