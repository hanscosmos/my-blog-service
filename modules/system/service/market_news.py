import html
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import requests
from django.core.cache import cache

CN_TZ = ZoneInfo('Asia/Shanghai')
REQUEST_TIMEOUT = 5

ARTICLES_CACHE_KEY = 'market:news:articles'
ARTICLES_STALE_KEY = 'market:news:articles:stale'
ARTICLES_CACHE_TTL = 300
ARTICLES_STALE_TTL = 1800

FLASH_CACHE_KEY = 'market:news:flash'
FLASH_STALE_KEY = 'market:news:flash:stale'
FLASH_CACHE_TTL = 60
FLASH_STALE_TTL = 600

NEWS_ITEM_LIMIT = 15
FLASH_ITEM_LIMIT = 20

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
}

SINA_FINANCE_URL = 'https://feed.mix.sina.com.cn/api/roll/get'
SINA_FINANCE_PARAMS = {'pageid': 153, 'lid': 2516, 'num': 30, 'page': 1}

CHINANEWS_FINANCE_URL = 'https://www.chinanews.com.cn/rss/finance.xml'
CHINANEWS_WORLD_URL = 'https://www.chinanews.com.cn/rss/world.xml'
CHINANEWS_SOCIETY_URL = 'https://www.chinanews.com.cn/rss/society.xml'
CHINANEWS_SCROLL_URL = 'https://www.chinanews.com.cn/rss/scroll-news.xml'

EASTMONEY_FLASH_URL = 'https://np-weblist.eastmoney.com/comm/web/getFastNewsList'
EASTMONEY_FLASH_PARAMS = {
    'client': 'web',
    'biz': 'web_724',
    'fastColumn': '102',
    'sortEnd': '',
    'pageSize': 30,
    'req_trace': '1',
}

WSCN_LIVES_URL = 'https://api-one.wallstcn.com/apiv1/content/lives'
WSCN_WORLD_CHANNEL = 'forex-channel'
WSCN_FLASH_CHANNEL = 'us-stock-channel'

CATEGORY_ORDER = ('finance', 'world', 'society')
CATEGORY_NAMES = {'finance': '金融', 'world': '国际', 'society': '社会'}

_TAG_RE = re.compile(r'<[^>]+>')
_SPACE_RE = re.compile(r'[\s　]+')


def _clean_text(raw, limit=120):
    if not raw:
        return ''
    text = html.unescape(str(raw))
    text = _TAG_RE.sub('', text)
    text = _SPACE_RE.sub(' ', text).strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + '…'
    return text


def _format_dt(value):
    return value.astimezone(CN_TZ).strftime('%Y-%m-%d %H:%M')


def _format_unix(raw):
    try:
        return _format_dt(datetime.fromtimestamp(int(raw), CN_TZ))
    except (TypeError, ValueError, OSError):
        return ''


def _format_str(raw):
    try:
        return datetime.strptime(raw, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
    except (TypeError, ValueError):
        return (raw or '')[:16]


def _fetch_json(url, params):
    resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _fetch_sina_finance():
    data = _fetch_json(SINA_FINANCE_URL, SINA_FINANCE_PARAMS)
    raw_items = ((data.get('result') or {}).get('data') or [])
    items = []
    for raw in raw_items:
        url = raw.get('url') or raw.get('wapurl')
        title = _clean_text(raw.get('title'), 80)
        if not url or not title:
            continue
        items.append({
            'id': raw.get('docid') or url,
            'category': 'finance',
            'title': title,
            'summary': _clean_text(raw.get('summary') or raw.get('intro'), 120),
            'source': raw.get('media_name') or '新浪财经',
            'publishTime': _format_unix(raw.get('ctime')),
            'url': url,
        })
    return items


def _fetch_chinanews_feed(url):
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    items = []
    for node in root.findall('.//item'):
        link = (node.findtext('link') or '').strip()
        title = _clean_text(node.findtext('title'), 80)
        if not link or not title:
            continue
        publish_time = ''
        pub_date = node.findtext('pubDate')
        if pub_date:
            try:
                parsed = parsedate_to_datetime(pub_date)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=CN_TZ)
                publish_time = _format_dt(parsed)
            except (TypeError, ValueError):
                publish_time = ''
        items.append({
            'id': link,
            'category': '',
            'title': title,
            'summary': _clean_text(node.findtext('description'), 120),
            'source': '中国新闻网',
            'publishTime': publish_time,
            'url': link,
        })
    return items


def _fetch_wscn_lives(channel):
    data = _fetch_json(WSCN_LIVES_URL, {'channel': channel, 'limit': 30})
    raw_items = ((data.get('data') or {}).get('items') or [])
    items = []
    for raw in raw_items:
        title = _clean_text(raw.get('title'), 80)
        content = _clean_text(raw.get('content_text'), 140)
        if not title and not content:
            continue
        raw_id = str(raw.get('id') or '')
        items.append({
            'id': raw_id,
            'title': title or content[:40],
            'content': content,
            'publishTime': _format_unix(raw.get('display_time')),
            'url': raw.get('uri') or (f'https://wallstreetcn.com/livenews/{raw_id}' if raw_id else ''),
        })
    return items


def _fetch_eastmoney_flash():
    data = _fetch_json(EASTMONEY_FLASH_URL, EASTMONEY_FLASH_PARAMS)
    raw_items = ((data.get('data') or {}).get('fastNewsList') or [])
    items = []
    for raw in raw_items:
        title = _clean_text(raw.get('title'), 80)
        content = _clean_text(raw.get('summary'), 140)
        # 东方财富快讯正文通常以【标题】开头，去掉重复部分
        content = re.sub(r'^【[^】]{0,80}】', '', content).strip()
        if not title and not content:
            continue
        code = str(raw.get('code') or '')
        items.append({
            'id': code or title,
            'title': title or content[:40],
            'content': content,
            'publishTime': _format_str(raw.get('showTime')),
            'url': f'https://finance.eastmoney.com/a/{code}.html' if code else '',
        })
    return items


def _categorize(items, category):
    return [{**item, 'category': category} for item in items]


def _merge_items(items, limit):
    seen = set()
    result = []
    for item in sorted(items, key=lambda value: value.get('publishTime') or '', reverse=True):
        key = item.get('url') or item.get('title')
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def _safe_fetch(fetcher, *args):
    try:
        return fetcher(*args)
    except Exception:
        return []


def _build_articles():
    with ThreadPoolExecutor(max_workers=6) as pool:
        sina_future = pool.submit(_safe_fetch, _fetch_sina_finance)
        cn_finance_future = pool.submit(_safe_fetch, _fetch_chinanews_feed, CHINANEWS_FINANCE_URL)
        cn_world_future = pool.submit(_safe_fetch, _fetch_chinanews_feed, CHINANEWS_WORLD_URL)
        cn_society_future = pool.submit(_safe_fetch, _fetch_chinanews_feed, CHINANEWS_SOCIETY_URL)
        cn_scroll_future = pool.submit(_safe_fetch, _fetch_chinanews_feed, CHINANEWS_SCROLL_URL)
        wscn_future = pool.submit(_safe_fetch, _fetch_wscn_lives, WSCN_WORLD_CHANNEL)

    scroll_items = cn_scroll_future.result()
    wscn_articles = [
        {
            'id': f'wscn-{item["id"]}',
            'category': 'world',
            'title': item['title'],
            'summary': item['content'],
            'source': '华尔街见闻',
            'publishTime': item['publishTime'],
            'url': item['url'],
        }
        for item in wscn_future.result()
    ]

    category_items = {
        'finance': _categorize(sina_future.result() + cn_finance_future.result(), 'finance'),
        'world': (
            _categorize(cn_world_future.result(), 'world')
            + _categorize([item for item in scroll_items if '/gj/' in item['url']], 'world')
            + wscn_articles
        ),
        'society': _categorize(
            cn_society_future.result()
            + [item for item in scroll_items if '/sh/' in item['url']],
            'society',
        ),
    }

    categories = [
        {
            'key': key,
            'name': CATEGORY_NAMES[key],
            'items': _merge_items(category_items[key], NEWS_ITEM_LIMIT),
        }
        for key in CATEGORY_ORDER
    ]
    if not any(category['items'] for category in categories):
        raise RuntimeError('新闻源均不可用')
    return categories


def _build_flashes():
    with ThreadPoolExecutor(max_workers=2) as pool:
        eastmoney_future = pool.submit(_safe_fetch, _fetch_eastmoney_flash)
        wscn_future = pool.submit(_safe_fetch, _fetch_wscn_lives, WSCN_FLASH_CHANNEL)

    items = eastmoney_future.result() + wscn_future.result()
    if not items:
        raise RuntimeError('快讯源均不可用')
    return _merge_items(items, FLASH_ITEM_LIMIT)


def _now_text():
    return datetime.now(CN_TZ).strftime('%Y-%m-%d %H:%M:%S')


def _load_cached(cache_key, stale_key, ttl, stale_ttl, builder, force):
    if not force:
        cached = cache.get(cache_key)
        if isinstance(cached, dict) and 'data' in cached:
            return cached['data'], cached.get('updateTime', ''), False
    try:
        data = builder()
        update_time = _now_text()
        payload = {'updateTime': update_time, 'data': data}
        cache.set(cache_key, payload, ttl)
        cache.set(stale_key, payload, stale_ttl)
        return data, update_time, False
    except Exception:
        stale = cache.get(stale_key)
        if isinstance(stale, dict) and 'data' in stale:
            return stale['data'], stale.get('updateTime', ''), True
        return None, '', False


def get_market_news_data(force=False):
    articles, articles_time, articles_stale = _load_cached(
        ARTICLES_CACHE_KEY,
        ARTICLES_STALE_KEY,
        ARTICLES_CACHE_TTL,
        ARTICLES_STALE_TTL,
        _build_articles,
        force,
    )
    flashes, flashes_time, flashes_stale = _load_cached(
        FLASH_CACHE_KEY,
        FLASH_STALE_KEY,
        FLASH_CACHE_TTL,
        FLASH_STALE_TTL,
        _build_flashes,
        force,
    )

    articles_failed = articles is None
    flashes_failed = flashes is None

    if articles_failed:
        articles = [
            {'key': key, 'name': CATEGORY_NAMES[key], 'items': []}
            for key in CATEGORY_ORDER
        ]
    if flashes_failed:
        flashes = []

    if not any(category['items'] for category in articles) and not flashes:
        raise RuntimeError('资讯数据获取失败')

    update_time = max(
        [value for value in (articles_time, flashes_time) if value],
        default=_now_text(),
    )
    return {
        'updateTime': update_time,
        'stale': articles_stale or flashes_stale or articles_failed or flashes_failed,
        'categories': articles,
        'flashes': flashes,
    }
