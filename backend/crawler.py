"""
TechNews 资讯聚合 - 真实数据爬虫引擎
数据源：
  1. GitHub Search API  - 近期热门仓库（无需 API Key）
  2. Hacker News Algolia API - 热门科技故事（无需 API Key）
  3. YouTube RSS Feeds  - 科技频道最新视频（需外网访问）
  4. Bilibili Search API - 科技/AI/开源视频（国内直连，无需 API Key）
  5. Tech Blog RSS Feeds - 科技博客文章（阮一峰/酷壳/GitHub Blog 等）
使用 Python 标准库 urllib，不引入额外依赖。
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import hashlib
import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from database import insert_article, insert_crawl_log, update_crawl_log, get_db, cleanup_old_articles


# ============================================================
# 配置
# ============================================================

# GitHub Search API - 搜索近 7 天创建、star > 50 的仓库
GITHUB_API = "https://api.github.com/search/repositories"

# Hacker News Algolia API - 搜索近 3 天、points > 30 的故事
HN_API = "https://hn.algolia.com/api/v1/search"

# YouTube RSS - 科技频道（channel_id 可在频道页面源码中搜索 channel_id 获取）
YOUTUBE_CHANNELS = {
    "Fireship":         "UCsBjURrPoezykLs9EqgamOA",
    "MKBHD":            "UCBJycsmduvYEL83R_U4JriQ",
    "Linus Tech Tips":  "UCXuqSBlHAE6Xw-yeJA0Tunw",
    "Two Minute Papers": "UCbfYPyITQ-7l7upoAAI3A19A",
    "Veritasium":       "UCHnyfMqiRRG1u-2MsSQLbXA",
    "Asianometry":      "UC6n6j38BcQzlM5LsgxV4tHg",
}

# Bilibili 搜索 API - 搜索科技/AI/开源相关视频（国内直连）
BILIBILI_SEARCH_API = "https://api.bilibili.com/x/web-interface/search/type"
BILIBILI_KEYWORDS = ['AI', '开源', '编程', 'Agnes AI', '多模态AI', 'AI Agent']
BILIBILI_RESULTS_PER_KEYWORD = 5  # 每个关键词取多少条

# Tech Blog RSS Feeds - 科技博客 RSS/Atom 订阅源
BLOG_FEEDS = {
    "ruanyifeng":  "https://www.ruanyifeng.com/blog/atom.xml",      # 阮一峰的网络日志
    "coolshell":   "https://coolshell.cn/feed",                      # 酷壳 CoolShell
    "github":      "https://github.blog/feed/",                      # GitHub Blog
    "cloudflare":  "https://blog.cloudflare.com/rss/",               # Cloudflare Blog
    "stackoverflow": "https://stackoverflow.blog/feed/",             # Stack Overflow Blog
    "v2ex":        "https://www.v2ex.com/index.xml",                 # V2EX
    "solidot":     "https://www.solidot.org/index.rss",              # Solidot 奇客
    "oschina":     "https://www.oschina.net/news/rss",               # 开源中国
    "linuxcn":     "https://linux.cn/rss.xml",                       # Linux 中国
    "cnbeta":      "https://rss.cnbeta.com/rss",                     # cnBeta
    "csdn":        "https://blog.csdn.net/rss/rss.html",                 # CSDN 博客（Agnes 相关文章主要来源）
    "taibakeji":   "https://www.36kr.com/feed",                          # 钛媒体（科技深度报道，含 AI）
}
BLOG_POSTS_PER_FEED = 3  # 每个 feed 取最新几篇

# Reddit JSON API - 热门科技子版块（无需 API Key，直接 .json 接口）
REDDIT_SUBREDDITS = ['programming', 'MachineLearning', 'technology']
REDDIT_POSTS_PER_SUB = 5   # 每个子版块取多少条
REDDIT_MIN_SCORE = 50      # 最低分数门槛

# 内容质量门槛
GITHUB_MIN_STARS = 50
HN_MIN_POINTS = 30
BILIBILI_HOT_PLAYS = 10000  # 播放量超过此值标记为热门
ARTICLE_MAX_AGE_DAYS = 30  # 超过此天数的文章会被清理

# 请求超时（秒）
HTTP_TIMEOUT = 10
YOUTUBE_TIMEOUT = 5  # YouTube RSS 单独设置更短超时

# AI 关键词（用于自动分类）
AI_KEYWORDS = [
    'ai', 'artificial intelligence', 'gpt', 'llm', 'machine learning',
    'deep learning', 'neural network', 'transformer', 'openai', 'claude',
    'gemini', 'anthropic', 'deepmind', 'diffusion', 'rag', 'agent',
    'chatbot', 'nlp', 'computer vision', 'reinforcement learning',
    'pytorch', 'tensorflow', 'hugging face', 'langchain', 'embedding',
    'fine-tune', 'fine tune', 'inference', 'training', 'model',
    # Agnes AI 相关
    'agnes ai', 'agnes-ai', 'agnes ai', 'agness', 'agnes api',
    'agnes video', 'agnes image', 'agnes-flash',
    # 中文关键词
    '人工智能', '机器学习', '深度学习', '大模型', '大语言模型',
    '神经网络', '自然语言处理', '计算机视觉', '强化学习',
    '智能体', '微调', '推理', '训练', '生成式',
    '多模态', '文生视频', '视频生成', '文生图', '图像生成',
]

# 开源关键词
OPENSOURCE_KEYWORDS = [
    'open source', 'github', 'repo', 'library', 'framework', 'sdk',
    'rust', 'python', 'javascript', 'typescript', 'golang', 'kubernetes',
    'docker', 'linux', 'apache', 'mit license', 'gnu', 'npm', 'pypi',
    'compiler', 'runtime', 'webassembly', 'wasm', 'deno', 'bun',
    'postgresql', 'redis', 'kafka', 'graphql', 'vite', 'webpack',
    # 中文关键词
    '开源', '开源项目', '开源工具', '框架', '编译器', '运行时',
]


# ============================================================
# 工具函数
# ============================================================

def _http_get(url, extra_headers=None, timeout=None):
    """发起 HTTP GET 请求，返回响应文本或 None"""
    headers = {'User-Agent': 'TechNews-Aggregator/1.0'}
    if extra_headers:
        headers.update(extra_headers)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout or HTTP_TIMEOUT) as resp:
            return resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        print(f"  [HTTP] {url[:80]} -> HTTP {e.code}")
        return None
    except Exception as e:
        print(f"  [HTTP] {url[:80]} -> {e}")
        return None


def _parse_timestamp(raw):
    """将多种时间格式统一为 'YYYY-MM-DD HH:MM:SS'"""
    if not raw:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    raw = str(raw).strip()

    # ISO 8601: 2026-08-04T10:30:00Z 或 2026-08-04T10:30:00.000Z
    try:
        dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        # 转为本地时间
        dt = dt.replace(tzinfo=None)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        pass

    # Unix 时间戳（字符串或数字）
    try:
        ts = int(float(raw))
        dt = datetime.fromtimestamp(ts)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        pass

    # RFC 822: Wed, 04 Aug 2026 10:30:00 GMT（YouTube RSS）
    try:
        dt = parsedate_to_datetime(raw)
        dt = dt.replace(tzinfo=None)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        pass

    # 已经是 YYYY-MM-DD HH:MM:SS 格式
    if len(raw) >= 10:
        return raw[:19] if len(raw) >= 19 else raw[:10] + ' 00:00:00'

    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _categorize(title, summary="", extra_tags=None):
    """根据关键词自动分类: ai / opensource / tech"""
    text = f"{title} {summary}".lower()
    if extra_tags:
        text += " " + " ".join(str(t) for t in extra_tags).lower()

    # 先检测 AI（更具体）
    for kw in AI_KEYWORDS:
        if kw in text:
            return 'ai'

    # 再检测开源
    for kw in OPENSOURCE_KEYWORDS:
        if kw in text:
            return 'opensource'

    # 默认科技
    return 'tech'


def _mark_hot(article_id, view_count, threshold):
    """如果热度超过阈值，标记为热门并更新 view_count"""
    if view_count > threshold:
        conn = get_db()
        conn.execute(
            "UPDATE articles SET is_hot = 1, view_count = ? WHERE id = ?",
            (view_count, article_id)
        )
        conn.commit()
        conn.close()


# ============================================================
# GitHub 爬虫
# ============================================================

def crawl_github():
    """从 GitHub Search API 获取近期热门仓库"""
    print("[Crawler] GitHub: 开始爬取...")

    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    params = urllib.parse.urlencode({
        'q': f'created:>{seven_days_ago} stars:>{GITHUB_MIN_STARS}',
        'sort': 'stars',
        'order': 'desc',
        'per_page': 15,
    })
    url = f"{GITHUB_API}?{params}"

    raw = _http_get(url, extra_headers={'Accept': 'application/vnd.github.v3+json'})
    if not raw:
        print("[Crawler] GitHub: 请求失败")
        return 0, 0

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("[Crawler] GitHub: JSON 解析失败")
        return 0, 0

    repos = data.get('items', [])
    new_count = 0

    for repo in repos:
        full_name = repo.get('full_name', '')
        description = repo.get('description', '') or '暂无描述'
        title = f"{full_name} - {description[:80]}" if len(description) > 80 else f"{full_name} - {description}"

        source_url = repo.get('html_url', '')
        author = repo.get('owner', {}).get('login', '')
        published_at = _parse_timestamp(repo.get('created_at'))
        stars = repo.get('stargazers_count', 0)
        thumbnail_url = repo.get('owner', {}).get('avatar_url', '')
        topics = repo.get('topics', [])
        language = repo.get('language', '')
        keywords = ','.join(topics[:5]) if topics else (language or '')

        category = _categorize(title, description, topics)

        result = insert_article(
            title=title,
            summary=description,
            source_platform='github',
            category=category,
            source_url=source_url,
            author=author,
            published_at=published_at,
            thumbnail_url=thumbnail_url,
            keywords=keywords,
        )
        if result is not None:
            new_count += 1
            _mark_hot(result, stars, 500)

    print(f"[Crawler] GitHub: 抓取 {len(repos)} 条，新增 {new_count} 条")
    return len(repos), new_count


# ============================================================
# Hacker News 爬虫
# ============================================================

def crawl_hackernews():
    """从 Hacker News Algolia API 获取热门故事"""
    print("[Crawler] Hacker News: 开始爬取...")

    three_days_ago = int((datetime.now() - timedelta(days=3)).timestamp())
    params = urllib.parse.urlencode({
        'tags': 'story',
        'numericFilters': f'points>{HN_MIN_POINTS},created_at_i>{three_days_ago}',
        'hitsPerPage': 15,
    })
    url = f"{HN_API}?{params}"

    raw = _http_get(url)
    if not raw:
        print("[Crawler] HN: 请求失败")
        return 0, 0

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("[Crawler] HN: JSON 解析失败")
        return 0, 0

    hits = data.get('hits', [])
    new_count = 0

    for hit in hits:
        title = hit.get('title', '').strip()
        if not title:
            continue

        points = hit.get('points', 0)
        num_comments = hit.get('num_comments', 0)
        summary = f"Hacker News 热门 | {points} points | {num_comments} comments"

        # 优先使用原文 URL，没有则用 HN 讨论页
        source_url = hit.get('url') or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
        author = hit.get('author', '')
        published_at = _parse_timestamp(hit.get('created_at_i'))
        keywords = 'hackernews,' + (hit.get('_tags', ['story'])[0] if hit.get('_tags') else 'story')

        category = _categorize(title, summary)

        result = insert_article(
            title=title,
            summary=summary,
            source_platform='hackernews',
            category=category,
            source_url=source_url,
            author=author,
            published_at=published_at,
            keywords=keywords,
        )
        if result is not None:
            new_count += 1
            _mark_hot(result, points, 200)

    print(f"[Crawler] HN: 抓取 {len(hits)} 条，新增 {new_count} 条")
    return len(hits), new_count


# ============================================================
# YouTube RSS 爬虫
# ============================================================

def crawl_youtube():
    """从 YouTube RSS feeds 获取科技频道最新视频"""
    print("[Crawler] YouTube: 开始爬取...")

    total_fetched = 0
    total_new = 0

    # Atom 命名空间
    ns = {
        'atom': 'http://www.w3.org/2005/Atom',
        'media': 'http://search.yahoo.com/mrss/',
        'yt': 'http://www.youtube.com/xml/schemas/2015',
    }

    for channel_name, channel_id in YOUTUBE_CHANNELS.items():
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

        raw = _http_get(feed_url, timeout=YOUTUBE_TIMEOUT)
        if not raw:
            print(f"  [YouTube] {channel_name}: 获取失败，跳过")
            continue

        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            print(f"  [YouTube] {channel_name}: XML 解析失败，跳过")
            continue

        entries = root.findall('atom:entry', ns)
        # 每个频道最多取 3 条最新视频
        for entry in entries[:3]:
            title_elem = entry.find('atom:title', ns)
            if title_elem is None or not title_elem.text:
                continue
            title = title_elem.text.strip()

            link_elem = entry.find('atom:link', ns)
            source_url = link_elem.get('href', '') if link_elem is not None else ''

            pub_elem = entry.find('atom:published', ns)
            published_at = _parse_timestamp(pub_elem.text if pub_elem is not None else None)

            author_elem = entry.find('atom:author/atom:name', ns)
            author = author_elem.text if author_elem is not None else channel_name

            # 视频描述作为摘要
            desc_elem = entry.find('media:group/media:description', ns)
            desc_text = desc_elem.text if desc_elem is not None and desc_elem.text else '暂无描述'
            summary = desc_text[:200]

            # 缩略图
            thumb_elem = entry.find('media:group/media:thumbnail', ns)
            thumbnail_url = thumb_elem.get('url', '') if thumb_elem is not None else ''

            # 视频统计（YouTube RSS 不提供 view_count，用频道名做关键词）
            category = _categorize(title, summary, [channel_name])

            result = insert_article(
                title=title,
                summary=summary,
                source_platform='youtube',
                category=category,
                source_url=source_url,
                author=author,
                published_at=published_at,
                thumbnail_url=thumbnail_url,
                keywords=channel_name,
            )
            if result is not None:
                total_new += 1

            total_fetched += 1

        print(f"  [YouTube] {channel_name}: 获取 {min(len(entries), 3)} 条视频")

    print(f"[Crawler] YouTube 总计: 抓取 {total_fetched} 条，新增 {total_new} 条")
    return total_fetched, total_new


# ============================================================
# Bilibili 爬虫
# ============================================================

# WBI 签名用混淆表（Bilibili 固定值，从前端源码提取）
_WBI_MIXIN_TABLE = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
]

# Bilibili 浏览器 UA（避免被反爬拦截）
_BILIBILI_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com',
}

# 科技相关 tname（用于 Popular API 过滤）
_TECH_TNAMES = {
    '数码', '科学科普', '科工机械', '野生技能协会', '社科·法律·心理',
    '新能源车', '校园学习', '计算机技术', '科技', '软件应用',
    '电脑装机', '编程', '人工智能',
}


def _strip_html_tags(text):
    """去除 Bilibili 搜索结果标题中的 <em class="keyword"> 高亮标签"""
    if not text:
        return ''
    return re.sub(r'<[^>]+>', '', text).strip()


def _get_bilibili_buvid3():
    """从 Bilibili SPI 接口获取 buvid3 cookie"""
    raw = _http_get(
        'https://api.bilibili.com/x/frontend/finger/spi',
        extra_headers=_BILIBILI_HEADERS
    )
    if not raw:
        return ''
    try:
        data = json.loads(raw)
        if data.get('code') == 0:
            return data.get('data', {}).get('b_3', '')
    except (json.JSONDecodeError, KeyError):
        pass
    return ''


def _get_wbi_keys():
    """从 Bilibili nav 接口获取 WBI 签名所需的 img_key 和 sub_key"""
    raw = _http_get(
        'https://api.bilibili.com/x/web-interface/nav',
        extra_headers=_BILIBILI_HEADERS
    )
    if not raw:
        return None, None
    try:
        data = json.loads(raw)
        wbi_img = data.get('data', {}).get('wbi_img', {})
        img_url = wbi_img.get('img_url', '')
        sub_url = wbi_img.get('sub_url', '')
        # 从 URL 中提取 key：https://i0.hdslb.com/bfs/wbi/xxx.png -> xxx
        img_key = img_url.rsplit('/', 1)[-1].split('.')[0] if img_url else ''
        sub_key = sub_url.rsplit('/', 1)[-1].split('.')[0] if sub_url else ''
        return img_key, sub_key
    except (json.JSONDecodeError, KeyError):
        return None, None


def _wbi_sign(params, img_key, sub_key):
    """对请求参数进行 WBI 签名，返回带 w_rid 的完整参数"""
    # 用混淆表生成 mixin_key
    orig = img_key + sub_key
    mixin_key = ''.join(orig[i] for i in _WBI_MIXIN_TABLE if i < len(orig))[:32]

    # 添加时间戳
    params['wts'] = int(time.time())

    # 按参数名排序后拼接
    sorted_items = sorted(params.items())
    # 过滤特殊字符（Bilibili 要求去除 !'()* 的 URL 编码）
    query = '&'.join(
        f'{k}={urllib.parse.quote(str(v), safe="")}'
        for k, v in sorted_items
    )
    # 计算 w_rid
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params['w_rid'] = w_rid
    return params


def _crawl_bilibili_search(buvid3, img_key, sub_key):
    """使用 WBI 签名的搜索 API 获取视频"""
    total_fetched = 0
    total_new = 0

    for keyword in BILIBILI_KEYWORDS:
        params = {
            'search_type': 'video',
            'keyword': keyword,
            'order': 'pubdate',
            'ps': BILIBILI_RESULTS_PER_KEYWORD,
            'pn': 1,
        }

        # WBI 签名
        if img_key and sub_key:
            params = _wbi_sign(params, img_key, sub_key)

        query = urllib.parse.urlencode(params)
        url = f"{BILIBILI_SEARCH_API}?{query}"

        headers = dict(_BILIBILI_HEADERS)
        if buvid3:
            headers['Cookie'] = f'buvid3={buvid3}'

        raw = _http_get(url, extra_headers=headers)
        if not raw:
            print(f"  [Bilibili] 搜索 '{keyword}': 请求失败，跳过")
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            print(f"  [Bilibili] 搜索 '{keyword}': 响应非 JSON，跳过")
            continue

        if data.get('code') != 0:
            print(f"  [Bilibili] 搜索 '{keyword}': API code={data.get('code')}, msg={data.get('message', '')}")
            continue

        results = data.get('data', {}).get('result', [])
        if not results:
            print(f"  [Bilibili] 搜索 '{keyword}': 无结果")
            continue

        keyword_new = 0
        for video in results:
            new_count = _insert_bilibili_video(video, keyword)
            if new_count:
                keyword_new += 1
            total_fetched += 1

        total_new += keyword_new
        print(f"  [Bilibili] 搜索 '{keyword}': 获取 {len(results)} 条，新增 {keyword_new} 条")

    return total_fetched, total_new


def _crawl_bilibili_popular():
    """从 Bilibili 热门 API 获取视频并按科技分类过滤（搜索 API 不可用时的降级方案）"""
    print("[Crawler] Bilibili: 搜索 API 不可用，降级为热门 API + 科技过滤")

    total_fetched = 0
    total_new = 0
    seen_bvids = set()

    for page in range(1, 4):  # 抓 3 页，每页 50 条
        url = f"https://api.bilibili.com/x/web-interface/popular?ps=50&pn={page}"
        raw = _http_get(url, extra_headers=_BILIBILI_HEADERS)
        if not raw:
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if data.get('code') != 0:
            continue

        items = data.get('data', {}).get('list', [])
        for video in items:
            tname = video.get('tname', '')
            bvid = video.get('bvid', '')

            # 去重
            if bvid in seen_bvids:
                continue

            # 过滤：tname 属于科技类 OR 标题包含科技关键词
            title = video.get('title', '')
            desc = video.get('desc', '')
            is_tech = tname in _TECH_TNAMES
            if not is_tech:
                # 检查标题/描述是否包含科技关键词
                text_lower = f"{title} {desc}".lower()
                for kw in AI_KEYWORDS + OPENSOURCE_KEYWORDS:
                    if kw in text_lower:
                        is_tech = True
                        break

            if not is_tech:
                continue

            seen_bvids.add(bvid)

            # 将 Popular API 格式转换为统一处理
            owner = video.get('owner', {})
            stat = video.get('stat', {})
            normalized = {
                'bvid': bvid,
                'arcurl': f"https://www.bilibili.com/video/{bvid}" if bvid else '',
                'title': title,
                'description': desc or '',
                'author': owner.get('name', ''),
                'pic': video.get('pic', ''),
                'play': stat.get('view', 0),
                'pubdate': video.get('pubdate', 0),
                'tag': '',
                'duration': '',  # Popular API 不直接返回 duration 字符串
            }

            new_count = _insert_bilibili_video(normalized, tname)
            if new_count:
                total_new += 1
            total_fetched += 1

        if total_fetched >= 15:  # 够了就停
            break

    return total_fetched, total_new


def _insert_bilibili_video(video, keyword_or_tname):
    """将 Bilibili 视频数据插入数据库，返回新文章 ID 或 None"""
    title = _strip_html_tags(video.get('title', ''))
    if not title:
        return None

    bvid = video.get('bvid', '')
    source_url = video.get('arcurl') or (f"https://www.bilibili.com/video/{bvid}" if bvid else '')
    if not source_url:
        return None

    description = video.get('description', '') or ''
    author = video.get('author', '')
    pubdate = video.get('pubdate', 0)
    published_at = _parse_timestamp(pubdate)
    play_count = video.get('play', 0)

    # 缩略图 URL 补全
    pic = video.get('pic', '')
    if pic and pic.startswith('//'):
        pic = 'https:' + pic
    elif pic and not pic.startswith('http'):
        pic = 'https://' + pic

    tags = video.get('tag', '')
    duration = video.get('duration', '')
    keywords_str = f"bilibili,{tags}" if tags else "bilibili"

    # 构建摘要
    summary_parts = []
    if play_count > 0:
        summary_parts.append(f"播放 {play_count}")
    if duration:
        summary_parts.append(f"时长 {duration}")
    if description:
        summary_parts.append(description[:150])
    summary = ' | '.join(summary_parts) if summary_parts else '暂无描述'

    category = _categorize(title, description, [keyword_or_tname, tags])

    result = insert_article(
        title=title,
        summary=summary,
        source_platform='bilibili',
        category=category,
        source_url=source_url,
        author=author,
        published_at=published_at,
        thumbnail_url=pic,
        keywords=keywords_str,
    )
    if result is not None:
        _mark_hot(result, play_count, BILIBILI_HOT_PLAYS)
        return result
    return None


def crawl_bilibili():
    """从 Bilibili 获取科技相关视频（搜索 API 优先，热门 API 降级）"""
    print("[Crawler] Bilibili: 开始爬取...")

    # 尝试获取 buvid3 和 WBI 签名密钥
    buvid3 = _get_bilibili_buvid3()
    img_key, sub_key = _get_wbi_keys()

    if buvid3 and img_key and sub_key:
        print(f"  [Bilibili] 已获取 buvid3 + WBI 密钥，使用搜索 API")
        fetched, new = _crawl_bilibili_search(buvid3, img_key, sub_key)
        if fetched > 0:
            print(f"[Crawler] Bilibili 总计: 抓取 {fetched} 条，新增 {new} 条")
            return fetched, new
        print("  [Bilibili] 搜索 API 无结果，降级为热门 API")

    # 降级：使用热门 API + 科技过滤
    fetched, new = _crawl_bilibili_popular()
    print(f"[Crawler] Bilibili 总计: 抓取 {fetched} 条，新增 {new} 条")
    return fetched, new


# ============================================================
# Tech Blog RSS 爬虫
# ============================================================

# RSS/Atom 通用命名空间
_RSS_NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'media': 'http://search.yahoo.com/mrss/',
}


def _extract_feed_items(root):
    """从 RSS/Atom XML 根节点中统一提取文章条目列表"""
    # Atom feed: <entry> elements (直接子节点 of <feed>)
    entries = root.findall('atom:entry', _RSS_NS)
    if entries:
        return entries, 'atom'

    # RSS 2.0: <item> elements under <channel>
    items = root.findall('channel/item')
    if items:
        return items, 'rss'

    # RSS 2.0: <item> as direct children (某些非标准 feed)
    items = root.findall('item')
    if items:
        return items, 'rss'

    # 尝试不带命名空间查找 Atom entry
    entries = root.findall('{http://www.w3.org/2005/Atom}entry')
    if entries:
        return entries, 'atom'

    return [], 'rss'


def _extract_item_text(item, feed_type, tag_name, ns=None):
    """从 RSS item 或 Atom entry 中提取指定标签的文本"""
    if feed_type == 'atom':
        # Atom: 使用命名空间查找
        full_tag = f'atom:{tag_name}' if ns is None else f'{ns}:{tag_name}'
        elem = item.find(full_tag, _RSS_NS)
        if elem is None:
            # 尝试不带命名空间
            elem = item.find(tag_name)
    else:
        # RSS 2.0: 直接查找
        elem = item.find(tag_name)
        if elem is None and ns:
            elem = item.find(f'{ns}:{tag_name}', _RSS_NS)

    if elem is not None:
        # 处理 type="html" 的 content（CDATA 或转义）
        text = elem.text
        if text:
            return text.strip()
    return ''


def _extract_item_link(item, feed_type):
    """提取文章链接"""
    if feed_type == 'atom':
        # Atom: <link href="..."/> （取 alternate 或第一个 link）
        for link in item.findall('atom:link', _RSS_NS):
            rel = link.get('rel', '')
            href = link.get('href', '')
            if href and (rel == 'alternate' or rel == ''):
                return href
        # 尝试不带命名空间
        for link in item.findall('{http://www.w3.org/2005/Atom}link'):
            rel = link.get('rel', '')
            href = link.get('href', '')
            if href and (rel == 'alternate' or rel == ''):
                return href
    else:
        # RSS: <link>text</link>
        link_text = _extract_item_text(item, feed_type, 'link')
        if link_text:
            return link_text
    return ''


def _extract_item_date(item, feed_type):
    """提取发布时间"""
    if feed_type == 'atom':
        # Atom: <published> 或 <updated>
        date_str = _extract_item_text(item, feed_type, 'published')
        if not date_str:
            date_str = _extract_item_text(item, feed_type, 'updated')
    else:
        # RSS: <pubDate>
        date_str = _extract_item_text(item, feed_type, 'pubDate')
        if not date_str:
            # 尝试 dc:date
            date_str = _extract_item_text(item, feed_type, 'date', ns='dc')

    return _parse_timestamp(date_str) if date_str else datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _strip_html_simple(text):
    """简单去除 HTML 标签（博客摘要可能包含 HTML）"""
    if not text:
        return ''
    return re.sub(r'<[^>]+>', '', text).strip()


def crawl_blogs():
    """从科技博客 RSS/Atom feeds 获取最新文章"""
    print("[Crawler] Blogs: 开始爬取...")

    total_fetched = 0
    total_new = 0

    for blog_name, feed_url in BLOG_FEEDS.items():
        raw = _http_get(feed_url, timeout=HTTP_TIMEOUT)
        if not raw:
            print(f"  [Blog] {blog_name}: 获取失败，跳过")
            continue

        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            print(f"  [Blog] {blog_name}: XML 解析失败，跳过")
            continue

        items, feed_type = _extract_feed_items(root)
        if not items:
            print(f"  [Blog] {blog_name}: 未找到文章条目")
            continue

        feed_new = 0
        for item in items[:BLOG_POSTS_PER_FEED]:
            title = _strip_html_simple(_extract_item_text(item, feed_type, 'title'))
            if not title:
                continue

            source_url = _extract_item_link(item, feed_type)
            if not source_url:
                continue

            # 提取摘要：Atom 用 <summary> 或 <content>，RSS 用 <description>
            summary = _extract_item_text(item, feed_type, 'summary')
            if not summary:
                summary = _extract_item_text(item, feed_type, 'content', ns='content')
            if not summary:
                summary = _extract_item_text(item, feed_type, 'description')
            summary = _strip_html_simple(summary)[:300] if summary else '暂无摘要'

            published_at = _extract_item_date(item, feed_type)

            # 作者：Atom 用 <author><name>，RSS 用 <author> 或 dc:creator
            author = ''
            if feed_type == 'atom':
                author_elem = item.find('atom:author/atom:name', _RSS_NS)
                if author_elem is not None and author_elem.text:
                    author = author_elem.text.strip()
                else:
                    author_elem = item.find('{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name')
                    if author_elem is not None and author_elem.text:
                        author = author_elem.text.strip()
            else:
                author = _extract_item_text(item, feed_type, 'author')
                if not author:
                    author = _extract_item_text(item, feed_type, 'creator', ns='dc')

            if not author:
                author = blog_name

            category = _categorize(title, summary, [blog_name])

            result = insert_article(
                title=title,
                summary=summary,
                source_platform='blog',
                category=category,
                source_url=source_url,
                author=author,
                published_at=published_at,
                keywords=f"blog,{blog_name}",
            )
            if result is not None:
                feed_new += 1
            total_fetched += 1

        print(f"  [Blog] {blog_name}: 获取 {min(len(items), BLOG_POSTS_PER_FEED)} 篇，新增 {feed_new} 篇")
        total_new += feed_new

    print(f"[Crawler] Blogs 总计: 抓取 {total_fetched} 篇，新增 {total_new} 篇")
    return total_fetched, total_new


# ============================================================
# Reddit 爬虫
# ============================================================

def crawl_reddit():
    """从 Reddit JSON API 获取热门科技帖子"""
    print("[Crawler] Reddit: 开始爬取...")

    total_fetched = 0
    total_new = 0

    for subreddit in REDDIT_SUBREDDITS:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={REDDIT_POSTS_PER_SUB}"

        # Reddit 要求 User-Agent 包含应用名称
        raw = _http_get(url, extra_headers={
            'User-Agent': 'TechNews-Aggregator/1.0 (educational project)',
            'Accept': 'application/json',
        })
        if not raw:
            print(f"  [Reddit] r/{subreddit}: 请求失败，跳过")
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            print(f"  [Reddit] r/{subreddit}: JSON 解析失败，跳过")
            continue

        # Reddit API 结构: data.data.children[]
        children = data.get('data', {}).get('children', [])
        if not children:
            print(f"  [Reddit] r/{subreddit}: 无帖子")
            continue

        sub_new = 0
        for child in children:
            post = child.get('data', {})
            if not post:
                continue

            # 跳过置顶帖（stickied）
            if post.get('stickied'):
                continue

            score = post.get('score', 0)
            if score < REDDIT_MIN_SCORE:
                continue

            title = post.get('title', '').strip()
            if not title:
                continue

            # 构建原文链接：有 url 就用，没有就用 reddit 讨论页
            permalink = post.get('permalink', '')
            reddit_url = f"https://www.reddit.com{permalink}" if permalink else ''
            source_url = post.get('url') or reddit_url
            if not source_url or source_url.startswith('https://www.reddit.com/r/'):
                source_url = reddit_url

            # 摘要
            selftext = post.get('selftext', '')
            if selftext:
                summary = _strip_html_simple(selftext)[:200]
            else:
                num_comments = post.get('num_comments', 0)
                summary = f"Reddit r/{subreddit} | {score} upvotes | {num_comments} comments"

            author = post.get('author', '')
            published_at = _parse_timestamp(post.get('created_utc'))
            subreddit_name = post.get('subreddit', subreddit)
            keywords = f"reddit,{subreddit_name}"

            category = _categorize(title, summary, [subreddit_name])

            result = insert_article(
                title=title,
                summary=summary,
                source_platform='reddit',
                category=category,
                source_url=source_url,
                author=author,
                published_at=published_at,
                keywords=keywords,
            )
            if result is not None:
                sub_new += 1
                _mark_hot(result, score, 500)

            total_fetched += 1

        print(f"  [Reddit] r/{subreddit}: 获取 {len(children)} 条，新增 {sub_new} 条")
        total_new += sub_new

    print(f"[Crawler] Reddit 总计: 抓取 {total_fetched} 条，新增 {total_new} 条")
    return total_fetched, total_new


# ============================================================
# 过期内容清理（实现在 database.py，这里只是调用入口）
# ============================================================

def cleanup_articles(days=ARTICLE_MAX_AGE_DAYS):
    """清理超过指定天数的过期文章"""
    deleted = cleanup_old_articles(days)
    if deleted > 0:
        print(f"[Cleanup] 已清理 {deleted} 条过期文章（超过 {days} 天）")
    return deleted


# ============================================================
# 统一调度
# ============================================================

def run_crawl_job():
    """执行一次完整的爬取任务（所有数据源）"""
    sources = [
        ('github', crawl_github),
        ('hackernews', crawl_hackernews),
        ('bilibili', crawl_bilibili),
        ('blog', crawl_blogs),
        ('reddit', crawl_reddit),
        ('youtube', crawl_youtube),
    ]

    total_fetched = 0
    total_new = 0

    for platform_name, crawl_func in sources:
        log_id = insert_crawl_log(platform_name, status='running')
        try:
            fetched, new = crawl_func()
            total_fetched += fetched
            total_new += new
            update_crawl_log(log_id, 'success', articles_fetched=fetched, articles_new=new)
        except Exception as e:
            update_crawl_log(log_id, 'failed', error_message=str(e))
            print(f"[Crawler] {platform_name} 爬取出错: {e}")

    # 每轮爬取后清理过期内容
    cleanup_articles(ARTICLE_MAX_AGE_DAYS)

    print(f"[Crawler] 本轮总计: 抓取 {total_fetched} 条，新增 {total_new} 条")
    return total_fetched, total_new


# ============================================================
# 种子数据
# ============================================================

def seed_initial_data():
    """首次启动时从真实数据源获取初始数据"""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    conn.close()

    if count > 0:
        print(f"[Seeder] 数据库已有 {count} 条数据，跳过种子填充")
        return

    print("[Seeder] 首次启动，正在从真实数据源获取初始数据...")
    run_crawl_job()

    # 检查是否获取到了数据
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    conn.close()

    if count == 0:
        print("[Seeder] 所有数据源均未获取到数据，写入提示信息")
        insert_article(
            title="正在连接数据源...",
            summary="TechNews 正在连接 GitHub / Hacker News / YouTube 数据源。请稍后在管理后台手动触发爬取，或等待定时任务自动执行。",
            source_platform='github',
            category='tech',
            source_url='#',
            author='TechNews',
            published_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            keywords='system',
        )


# ============================================================
# 定时调度器
# ============================================================

# 调度器全局状态（支持看门狗自愈重启）
_scheduler_thread = None
_scheduler_running = False
_scheduler_lock = threading.Lock()

# 爬虫停摆阈值：超过该分钟数无爬取记录视为异常
LAST_CRAWL_STALE_MINUTES = 120


def get_last_crawl_time():
    """获取最近一次爬取开始时间（来自 crawl_logs）"""
    try:
        conn = get_db()
        try:
            row = conn.execute("SELECT MAX(started_at) FROM crawl_logs").fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    except Exception:
        return None


def check_crawler_health():
    """检查爬虫健康状态
    返回: (is_healthy, minutes_since_last_crawl, last_crawl_time)
    """
    last = get_last_crawl_time()
    if not last:
        return False, None, None
    try:
        last_dt = datetime.strptime(str(last)[:19], '%Y-%m-%d %H:%M:%S')
        minutes = (datetime.now() - last_dt).total_seconds() / 60
        return minutes <= LAST_CRAWL_STALE_MINUTES, int(minutes), str(last)[:19]
    except (ValueError, TypeError):
        return False, None, str(last)[:19]


def start_scheduler(interval_minutes=30):
    """启动后台定时爬取调度器（幂等：已在运行则跳过，可安全重复调用）"""
    global _scheduler_thread, _scheduler_running
    with _scheduler_lock:
        if _scheduler_thread and _scheduler_thread.is_alive() and _scheduler_running:
            print("[Scheduler] 调度线程已在运行，跳过重复启动")
            return
        _scheduler_running = True
        _scheduler_thread = threading.Thread(target=_scheduler_loop, args=(interval_minutes,), daemon=True)
        _scheduler_thread.start()
        print("[Scheduler] 后台调度线程已启动")


def _scheduler_loop(interval_minutes):
    """调度主循环（支持优雅退出标志）"""
    global _scheduler_running
    print(f"[Scheduler] 定时爬取已启动，间隔: {interval_minutes} 分钟")
    try:
        while _scheduler_running:
            time.sleep(interval_minutes * 60)
            if not _scheduler_running:
                break
            try:
                run_crawl_job()
            except Exception as e:
                print(f"[Scheduler] 爬取任务异常: {e}")
    finally:
        _scheduler_running = False
        print("[Scheduler] 调度线程已退出")


def start_watchdog(check_interval_minutes=5, restart=True):
    """启动爬虫看门狗：定期检查爬虫健康，调度线程死亡则自动重启

    参数:
        check_interval_minutes: 检查间隔（默认 5 分钟）
        restart: 调度线程死亡时是否自动重启（默认 True）
    """
    def watchdog_loop():
        print(f"[Watchdog] 看门狗已启动，每 {check_interval_minutes} 分钟检查一次（停摆阈值 {LAST_CRAWL_STALE_MINUTES} 分钟）")
        while True:
            time.sleep(check_interval_minutes * 60)
            try:
                healthy, minutes, last = check_crawler_health()
                if not healthy:
                    print(f"[Watchdog] 警告: 距上次爬取已 {minutes} 分钟（超过阈值 {LAST_CRAWL_STALE_MINUTES} 分钟），爬虫可能停摆")

                # 调度线程存活检测（先释放锁再重启，避免重入死锁）
                with _scheduler_lock:
                    thread_alive = _scheduler_thread is not None and _scheduler_thread.is_alive()
                if not thread_alive:
                    if restart:
                        print("[Watchdog] 检测到调度线程已死亡，正在自动重启...")
                        start_scheduler()
                    else:
                        print("[Watchdog] 检测到调度线程已死亡（自动重启已禁用）")
            except Exception as e:
                print(f"[Watchdog] 检查异常: {e}")

    threading.Thread(target=watchdog_loop, daemon=True).start()
    print("[Watchdog] 看门狗线程已启动")


def scheduler_status():
    """返回调度器状态（供状态 API 使用）"""
    return {
        'scheduler_running': _scheduler_running,
        'scheduler_thread_alive': _scheduler_thread is not None and _scheduler_thread.is_alive(),
    }


if __name__ == '__main__':
    # 独立运行测试
    from database import init_db
    print("=" * 50)
    print("  TechNews 爬虫引擎 - 独立测试模式")
    print("=" * 50)
    init_db()
    print("[Init] 数据库初始化完成")
    run_crawl_job()
    print("\n测试完成。")
