# -*- coding: utf-8 -*-
"""
通过 TechNews API 插入 Agnes 文章（无需 SSH）
需要先注册/登录获取 token
"""
import urllib.request
import urllib.error
import json
import os

BASE_URL = "https://technews.dedyn.io"

# 机器人账号密码从环境变量读取，不要硬编码提交到仓库
# 用法（PowerShell）：$env:TECHNEWS_BOT_PASSWORD="..." ; python insert_agnes_via_api.py
BOT_PASSWORD = os.environ.get('TECHNEWS_BOT_PASSWORD', '')

# Agnes AI 热门文章
AGNES_ARTICLES = [
    {
        'title': '新加坡Agnes AI三款核心模型API无限期免费：东南亚AI赛道杀出的"价格屠夫"',
        'summary': '2026年6月1日，新加坡AI Lab Agnes AI正式宣布旗下三款核心模型API面向全球开发者无限期免费开放。三款模型分别是：文本模型Agnes-2.0-Flash、图像模型Agnes-Image-2.0-Flash、视频模型Agnes-Video-V2.0。在AI大模型纷纷提价、限量的2026年，永久免费让全球开发者为之侧目。',
        'source_url': 'https://www.cnblogs.com/yijunzhao/p/20286023',
        'author': '小易撩挨踢',
        'published_at': '2026-06-03 14:03:00',
        'thumbnail_url': 'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=400',
        'keywords': 'AI,Agnes,免费API,多模态,新加坡,文本模型,图像模型,视频生成',
    },
    {
        'title': '免费API推荐：Agnes AI，全栈多模态平台来了',
        'summary': '文本、图片、视频API全部开放，且兼容OpenAI接口。对于个人开发者、学生以及开源项目维护者来说，Agnes AI最大的吸引力是：文本、图像、视频生成能力，一个平台全搞定，没有学习成本，修改Base URL和API Key就能直接接入。',
        'source_url': 'https://blog.csdn.net/Honmaple/article/details/161820149',
        'author': 'Honmaple',
        'published_at': '2026-08-09 18:45:27',
        'thumbnail_url': 'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=400',
        'keywords': 'AI,Agnes,免费API,OpenAI兼容,多模态,开发者工具,图像生成,视频生成',
    },
    {
        'title': '不做通用Agent：新加坡全民AI应用Agnes，上线四月揽获20万日活用户',
        'summary': 'Agnes AI由新加坡国立大学系统孵化，团队完全自主研发的7B闭源模型Agnes-R1已达同级模型的SOTA性能。产品自7月4日正式上线Product Hunt以来，仅仅四个月，全球斩获300万注册用户，日活跃用户突破20万。涵盖搜索、研究、图片、视频、PPT、表格等多功能一体化工作流。',
        'source_url': 'https://new.qq.com/rain/a/20251030A01YP600',
        'author': '腾讯网',
        'published_at': '2025-10-30 09:50:28',
        'thumbnail_url': 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=400',
        'keywords': 'AI,Agnes,新加坡,日活用户,NUS,Agent,AI应用,Product Hunt',
    },
    {
        'title': '两个月破300万用户，Agnes AI刷新Instagram与Snapchat增长纪录',
        'summary': 'Agnes AI在9月移动端App推出后，增长势能全面爆发：短短两个月新增注册用户300万，日活跃用户突破20万。Agnes AI由新加坡国立大学博士团队创立，凭借涵盖搜索、研究、图片、视频、PPT、表格等多功能一体化工作流，迅速赢得东南亚、拉美、中东地区知识工作者和年轻用户的青睐。',
        'source_url': 'https://new.qq.com/rain/a/20251117A02SV000',
        'author': '腾讯网',
        'published_at': '2025-11-17 12:04:00',
        'thumbnail_url': 'https://images.unsplash.com/photo-1551434678-e076c223a692?w=400',
        'keywords': 'AI,Agnes,增长纪录,用户增长,新加坡国立大学,移动App,多模态',
    },
    {
        'title': '李飞飞押宝的Agent被这个公司做出来了：Agnes AI',
        'summary': '一款完全在新加坡开发和训练的协作型AI助手，将智能生成、实时协作、上下文记忆以及本地化语言支持融合在一起。上线仅三周，Agnes日活就已逼近估值数亿美金、刚完成一轮融资的Lovart。在Product Hunt等科技社区好评如潮，有网友称：Agnes is a game-changer for business storytelling and productivity。',
        'source_url': 'https://blog.csdn.net/sinat_37574187/article/details/149586913',
        'author': 'Amusi CVer',
        'published_at': '2025-07-24 13:11:00',
        'thumbnail_url': 'https://images.unsplash.com/photo-1488229297570-58520851e68c?w=400',
        'keywords': 'AI,Agnes,Agent,协作AI,李飞飞,新加坡,Product Hunt,工作流',
    },
    {
        'title': 'Agnes AI免费使用教程：文本、图片、视频生成工具介绍',
        'summary': 'Agnes AI是由新加坡Sapiens AI团队开发的多模态AI平台，提供文本、图片、视频三种模型的API接口，目前处于免费开放阶段。文本模型Agnes-2.0-Flash支持256K超长上下文、OpenAI Chat Completions兼容、Agent场景和工具调用；图像模型支持文生图、海报生成、电商图；视频模型支持文生视频、AI短片。',
        'source_url': 'https://blog.csdn.net/2503_92925992/article/details/161819821',
        'author': 'CSDN',
        'published_at': '2026-06-20 17:47:08',
        'thumbnail_url': 'https://images.unsplash.com/photo-1614064641938-3bbee52942c7?w=400',
        'keywords': 'AI,Agnes,免费API,文本生成,图像生成,视频生成,教程,多模态',
    },
    {
        'title': 'Agnes AI接入Trae IDE完整步骤，零难度一次配置永久可用',
        'summary': '分享零难度、一次配置永久可用的Trae + Agnes AI接入方法，无需复杂部署，兼容OpenAI接口，直接解锁Agnes满血编程能力，代码补全、调试、全栈开发速度直接拉满。只需在Trae IDE中配置Base URL为https://api.agnes-ai.cn/v1，填入API Key即可使用。',
        'source_url': 'https://www.cnblogs.com/cbc2562/p/archive/2026/07/15',
        'author': '科普大巴',
        'published_at': '2026-07-15 18:26:13',
        'thumbnail_url': 'https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=400',
        'keywords': 'AI,Agnes,Trae,IDE,代码补全,API接入,编程,开发工具,教程',
    },
    {
        'title': 'Agnes AI接入Codex可行性方案：DeepSeek没钱后的Plan B',
        'summary': 'Agnes AI的Responses API与Codex客户端实际兼容程度需实测验证，核心思路是仿照DeepSeek官方「接入Codex」的教程，把Agnes的OpenAI兼容接口对接到Codex客户端，支持对话补全、代码补全等场景。Base URL使用https://api.agnes-ai.cn/v1，模型用agnes-2.5-flash。',
        'source_url': 'https://platform.agnes-ai.com',
        'author': 'TechNews',
        'published_at': '2026-08-11 22:47:00',
        'thumbnail_url': 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=400',
        'keywords': 'AI,Agnes,Codex,DeepSeek,API,代码补全,OpenAI兼容,开发工具',
    },
]

def api_post(path, data, token=None):
    """POST 请求"""
    url = f"{BASE_URL}{path}"
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {'success': False, 'error': f'HTTP {e.code}: {e.read().decode("utf-8")}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def register_or_login():
    """注册或登录获取 token"""
    if not BOT_PASSWORD:
        print('请先设置环境变量 TECHNEWS_BOT_PASSWORD（机器人账号密码）')
        return None

    # 先尝试注册
    reg_data = {
        'email': 'agnes_bot@technews.local',
        'username': 'agnes_bot',
        'password': BOT_PASSWORD
    }
    result = api_post('/api/auth/register', reg_data)
    if result.get('success'):
        print(f'注册成功: {result["data"]["user"]["email"]}')
        return result['data']['token']
    
    # 注册失败（可能已存在），尝试登录
    print(f'注册失败: {result.get("error")}，尝试登录...')
    login_data = {
        'email': 'agnes_bot@technews.local',
        'password': BOT_PASSWORD
    }
    result = api_post('/api/auth/login', login_data)
    if result.get('success'):
        print(f'登录成功: {result["data"]["user"]["email"]}')
        return result['data']['token']
    
    print(f'登录也失败: {result.get("error")}')
    return None

def insert_article_via_api(token, article):
    """通过 API 插入文章（如果 API 支持）"""
    # TechNews 没有直接插入文章的 API，需要通过爬虫触发
    # 这里只是打印信息
    print(f'  准备插入: {article["title"][:50]}...')
    return True

def main():
    print('=== Agnes AI 文章插入工具 ===\n')
    
    # 获取 token
    token = register_or_login()
    if not token:
        print('无法获取 token，退出')
        return
    
    print(f'Token: {token[:20]}...\n')
    
    # 由于 TechNews 没有直接插入文章的 API，我们输出文章信息
    # 用户需要手动复制到 admin 后台或使用其他方式
    print(f'共有 {len(AGNES_ARTICLES)} 篇 Agnes 文章需要插入：\n')
    for i, article in enumerate(AGNES_ARTICLES, 1):
        print(f'{i}. {article["title"]}')
        print(f'   来源: {article["source_url"]}')
        print(f'   作者: {article["author"]}')
        print()
    
    print('\n由于 TechNews 没有开放文章插入 API，建议：')
    print('1. 访问 https://technews.dedyn.io/admin 登录后台')
    print('2. 使用上面提供的 token 登录（如果后台支持 token）')
    print('3. 或者等下次爬虫自动抓取（已添加 Agnes 关键词）')

if __name__ == '__main__':
    main()
