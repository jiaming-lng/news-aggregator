# -*- coding: utf-8 -*-
"""
数据源增强模块
新增: GitHub Trending 爬虫 + AI 科技媒体 RSS 源
"""

import urllib.request
import urllib.error
import re
import xml.etree.ElementTree as ET
from datetime import datetime

# ============================================================
# GitHub Trending 爬虫（无 API，直接爬页面）
# ============================================================

GITHUB_TRENDING_URL = "https://github.com/trending"


def crawl_github_trending():
    """爬取 GitHub Trending 页面（https://github.com/trending）"""
    print("[Crawler] GitHub Trending: 开始爬取...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    req = urllib.request.Request(GITHUB_TRENDING_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            # 限制读取大小，避免 IncompleteRead
            html = resp.read(500000).decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[Crawler] GitHub Trending: 请求失败 - {e}")
        return 0, 0

    repo_pattern = re.compile(
        r'<article[^>]*class="Box-row"[^>]*>(.*?)</article>',
        re.DOTALL
    )

    repos = repo_pattern.findall(html)
    new_count = 0

    for repo_html in repos:
        try:
            name_match = re.search(
                r'<a[^>]*href="(/[^"]+)"[^>]*>\s*<span[^>]*d-none d-sm-inline[^>]*>([^<]+)</span>',
                repo_html
            )
            if not name_match:
                name_match = re.search(r'<a[^>]*href="(/[^"]+/[^"]+)"', repo_html)
            if not name_match:
                continue

            full_name = name_match.group(1).strip().lstrip('/')
            if '/' not in full_name:
                continue

            desc_match = re.search(
                r'<p[^>]*class="color-fg-secondary[^"]*"[^>]*>(.*?)</p>',
                repo_html, re.DOTALL
            )
            description = ''
            if desc_match:
                description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
                description = ' '.join(description.split())

            lang_match = re.search(
                r'<span[^>]*itemprop="programmingLanguage"[^>]*>([^<]+)</span>',
                repo_html
            )
            language = lang_match.group(1).strip() if lang_match else ''

            avatar_match = re.search(r'<img[^>]*class="avatar mb-1"[^>]*src="([^"]+)"', repo_html)
            avatar_url = avatar_match.group(1) if avatar_match else ''

            title = f"{full_name} - {description}" if description else full_name

            from crawler import insert_article, _categorize

            result = insert_article(
                title=title,
                summary=description or 'GitHub 热门项目',
                source_platform='github_trending',
                category=_categorize(title, description, [language] if language else []),
                source_url=f'https://github.com/{full_name}',
                author=full_name.split('/')[0],
                published_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                thumbnail_url=avatar_url,
                keywords=f'github,trending,{language}'.lower() if language else 'github,trending',
            )

            if result is not None:
                new_count += 1

        except Exception:
            continue

    print(f"[Crawler] GitHub Trending: 抓取 {len(repos)} 条，新增 {new_count} 条")
    return len(repos), new_count


# ============================================================
# AI 科技媒体 RSS 源（量子位同类型内容）
# ============================================================

AI_NEWS_RSS = {
    'ithome':   'https://www.ithome.com/rss/',    # IT之家
    'leiphone': 'https://www.leiphone.com/feed',  # 雷峰网
    'sspai':    'https://sspai.com/feed',         # 少数派
    'solidot':  'https://www.solidot.org/index.rss',  # Solidot
    'oschina':  'https://www.oschina.net/news/rss',   # 开源中国
}

AI_KEYWORDS = [
    'ai', '人工智能', '大模型', 'llm', 'gpt', 'chatgpt', 'openai',
    '深度学习', '机器学习', '神经网络', '多模态', '生成式', '智能体',
    'agent', 'claude', 'gemini', 'anthropic', '文生图', '视频生成',
    'diffusion', 'stable diffusion', 'sora', 'agnes', 'copilot', 'cursor',
    '编程', '开源', 'github', 'agent', 'rAG', 'embedding',
]


def crawl_ai_news():
    """通过多个 AI 科技 RSS 源过滤 AI 相关内容"""
    print("[Crawler] AI 科技媒体 RSS: 开始爬取...")

    new_count = 0
    fetched_count = 0

    for name, url in AI_NEWS_RSS.items():
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'TechNews-Aggregator/1.0',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            })
            with urllib.request.urlopen(req, timeout=8) as resp:
                xml_text = resp.read().decode('utf-8', errors='ignore')

            # 两种解析策略：先 ET，失败则正则提取
            items = []
            root = None
            try:
                root = ET.fromstring(xml_text)
                items = root.findall('.//item') or root.findall('.//entry')
            except ET.ParseError:
                pass

            # 正则兜底：ET 解析失败或找不到条目时，直接提取 <item> / <entry> 块
            if not items:
                for tag in ['item', 'entry']:
                    blocks = re.findall(
                        rf'<{tag}[^>]*>(.*?)</{tag}>',
                        xml_text, re.DOTALL | re.IGNORECASE
                    )
                    for block in blocks:
                        items.append(block)  # 传字符串而非 Element，后面的代码要兼容

            if not items:
                continue

            from crawler import insert_article, _categorize, _parse_timestamp

            for item in items[:15]:
                # 统一提取字段（Element 对象或字符串块）
                # 注意：不能用 hasattr(block, 'find') 判断，字符串也有 .find() 方法
                def get_text(block, tag):
                    if isinstance(block, str):
                        # 字符串块：用正则提取
                        m = re.search(
                            rf'<{tag}[^>]*>(.*?)</{tag}>',
                            block, re.DOTALL | re.IGNORECASE
                        )
                        if m:
                            t = re.sub(r'<[^>]+>', '', m.group(1))
                            return ' '.join(t.split())
                        return ''
                    # Element 对象
                    el = block.find(tag)
                    if el is not None:
                        return (el.text or '').strip()
                    return ''

                title = get_text(item, 'title')
                if not title:
                    continue

                desc_text = get_text(item, 'description') or get_text(item, 'summary') or get_text(item, 'content:encoded') or ''
                desc_text = desc_text[:300]
                link = get_text(item, 'link')
                if not link:
                    continue
                pub_date = get_text(item, 'pubDate') or get_text(item, 'published') or get_text(item, 'updated')
                author = get_text(item, 'author') or get_text(item, 'dc:creator') or name

                text_check = (title + ' ' + desc_text).lower()
                if not any(kw.lower() in text_check for kw in AI_KEYWORDS):
                    continue

                result = insert_article(
                    title=title[:200],
                    summary=desc_text or 'AI科技资讯',
                    source_platform=name,
                    category=_categorize(title, desc_text),
                    source_url=link,
                    author=author,
                    published_at=_parse_timestamp(pub_date) if pub_date else datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    keywords='ai,科技,人工智能,大模型',
                )

                if result is not None:
                    new_count += 1

            fetched_count += 1

        except Exception as e:
            print(f"[Crawler] {name}: 失败 - {e}")
            continue

    print(f"[Crawler] AI 科技媒体: 扫描 {fetched_count} 个源，新增 {new_count} 条")
    return fetched_count, new_count


if __name__ == '__main__':
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    if len(sys.argv) > 1:
        if sys.argv[1] == 'trending':
            crawl_github_trending()
        elif sys.argv[1] == 'ai_news':
            crawl_ai_news()
    else:
        print("用法: python crawler_enhancements.py [trending|ai_news]")
        print("  trending  - GitHub Trending 热门项目")
        print("  ai_news   - AI 科技媒体 RSS (智东西/雷峰网/IT之家等)")
