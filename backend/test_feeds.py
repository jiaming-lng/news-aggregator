# -*- coding: utf-8 -*-
import urllib.request

feeds = {
    'ithome':   'https://www.ithome.com/rss/',
    'leiphone': 'https://www.leiphone.com/feed',
    'sspai':    'https://sspai.com/feed',
    '36kr':     'https://36kr.com/feed',
    'pingwest': 'https://www.pingwest.com/feed',
}

for name, url in feeds.items():
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'TechNews/1.0'})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = r.read(300)
        print(f'OK   {name}: {len(data)} bytes')
    except Exception as e:
        print(f'FAIL {name}: {str(e)[:60]}')
