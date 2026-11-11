import hashlib
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import UUID
from zoneinfo import ZoneInfo

import requests
from django.core.cache import cache

from modules.system.models import FundHolding

CN_TZ = ZoneInfo('Asia/Shanghai')

FUND_SEARCH_URL = 'https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx'
FUND_QUOTE_URL = 'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNFInfo'
FUND_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Referer': 'https://fund.eastmoney.com/',
}
REQUEST_TIMEOUT = 5

FUND_QUOTE_CACHE_TTL = 60
FUND_QUOTE_STALE_TTL = 600
FUND_SEARCH_CACHE_TTL = 300
FUND_META_CACHE_TTL = 86400

FUND_CATEGORY_NAMES = {
    'bond': '债券型',
    'equity': '股票/指数',
    'mixed': '混合型',
    'overseas': '海外/QDII',
    'money': '货币型',
    'commodity': '商品型',
    'other': '其他',
}
VALID_CATEGORIES = tuple(FUND_CATEGORY_NAMES.keys())
VALID_STYLES = ('passive', 'active', 'unknown')


def _round(value, places):
    if value is None:
        return None
    return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def _json_number(value, places):
    rounded = _round(value, places)
    return None if rounded is None else float(rounded)


def _to_decimal(value):
    if value is None:
        return None
    text = str(value).strip().replace(',', '')
    if not text or text in ('--', 'null', 'None'):
        return None
    if text.endswith('%'):
        text = text[:-1]
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _is_uuid(value):
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _classify_fund(fund_type, fund_name=''):
    """按基金类型推断资产类别与管理方式，用户保存时可覆盖"""
    text = f'{fund_type or ""}{fund_name or ""}'
    upper_text = text.upper()

    if '债券' in text:
        category = 'bond'
    elif '货币' in text:
        category = 'money'
    elif 'QDII' in upper_text or '海外' in text:
        category = 'overseas'
    elif '商品' in text or '黄金' in text or '白银' in text:
        category = 'commodity'
    elif '混合' in text:
        category = 'mixed'
    elif '股票' in text or '指数' in text or 'ETF' in upper_text or '联接' in text:
        category = 'equity'
    else:
        category = 'other'

    if '指数' in text or 'ETF' in upper_text or '联接' in text:
        style = 'passive'
    elif '混合' in text or '股票' in text or '债券' in text:
        style = 'active'
    else:
        style = 'unknown'

    return category, style


def search_funds(keyword, limit=10):
    """按代码/名称搜索场外基金，返回带类型与最新净值的结果"""
    keyword = (keyword or '').strip()
    if not keyword:
        return []

    cache_key = f'market:fund:search:{keyword.lower()}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        resp = requests.get(
            FUND_SEARCH_URL,
            params={'m': 1, 'key': keyword},
            headers=FUND_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return []

    items = []
    seen = set()
    for raw in payload.get('Datas') or []:
        category_desc = raw.get('CATEGORYDESC')
        if category_desc and category_desc != '基金':
            continue
        base = raw.get('FundBaseInfo') or {}
        code = str(raw.get('CODE') or base.get('FCODE') or '').strip()
        name = str(raw.get('NAME') or base.get('SHORTNAME') or '').strip()
        if not code or not name or code in seen:
            continue
        fund_type = str(base.get('FTYPE') or '').strip()
        category, style = _classify_fund(fund_type, name)
        items.append({
            'code': code,
            'name': name,
            'type': fund_type,
            'category': category,
            'style': style,
            'nav': _json_number(_to_decimal(base.get('DWJZ')), 4),
            'navDate': base.get('FSRQ') or '',
            'company': base.get('JJGS') or '',
            'manager': base.get('JJJL') or '',
        })
        seen.add(code)
        if len(items) >= limit:
            break

    cache.set(cache_key, items, FUND_SEARCH_CACHE_TTL)
    return items


def get_fund_meta(code):
    """获取单支基金的名称/类型等元数据，找不到时返回 None"""
    cache_key = f'market:fund:meta:{code}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached or None

    meta = next((item for item in search_funds(code, limit=20) if item['code'] == code), None)
    cache.set(cache_key, meta or {}, FUND_META_CACHE_TTL)
    return meta


def _fetch_fund_quotes(codes):
    resp = requests.get(
        FUND_QUOTE_URL,
        params={
            'Fcodes': ','.join(codes),
            'pageIndex': 1,
            'pageSize': len(codes),
            'plat': 'Android',
            'appType': 'ttjj',
            'product': 'EFund',
            'Version': 1,
            'deviceid': 'my-blog-admin',
        },
        headers=FUND_HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get('ErrCode') not in (0, '0') or not payload.get('Datas'):
        raise ValueError(payload.get('ErrMsg') or '基金行情数据为空')
    return {
        item.get('FCODE'): item
        for item in payload.get('Datas') or []
        if item.get('FCODE')
    }


def _build_fund_quote(raw):
    if not raw:
        return None

    nav = _to_decimal(raw.get('NAV'))
    nav_date = str(raw.get('PDATE') or '').strip()
    nav_change = _to_decimal(raw.get('NAVCHGRT'))
    estimate_nav = _to_decimal(raw.get('GSZ'))
    estimate_change = _to_decimal(raw.get('GSZZL'))
    estimate_time = str(raw.get('GZTIME') or '').strip()
    today = datetime.now(CN_TZ).strftime('%Y-%m-%d')

    # 当日净值已公布时以净值为准；否则使用当日盘中估值
    nav_is_today = nav_date == today
    has_estimate = (
        not nav_is_today
        and estimate_nav is not None
        and estimate_nav > 0
        and estimate_time[:10] == today
    )

    if has_estimate:
        current_nav = estimate_nav
        prev_nav = nav
        change_percent = estimate_change
        if change_percent is None and prev_nav:
            change_percent = (current_nav - prev_nav) / prev_nav * 100
        data_mode = 'estimate'
        quote_time = estimate_time
    else:
        current_nav = nav
        if nav is not None and nav_change is not None and nav_change > -100:
            prev_nav = nav / (Decimal('1') + nav_change / Decimal('100'))
            change_percent = nav_change
        else:
            prev_nav = None
            change_percent = None
        data_mode = 'nav' if nav is not None else 'none'
        quote_time = nav_date

    return {
        'name': raw.get('SHORTNAME') or '',
        'nav': _json_number(nav, 4),
        'navDate': nav_date,
        'navChangePercent': _json_number(nav_change, 4),
        'estimateNav': _json_number(estimate_nav, 4),
        'estimateChangePercent': _json_number(estimate_change, 4),
        'estimateTime': estimate_time,
        'currentNav': _json_number(current_nav, 4),
        'prevNav': _json_number(prev_nav, 4),
        'changePercent': _json_number(change_percent, 4),
        'quoteTime': quote_time,
        'dataMode': data_mode,
    }


def get_fund_quotes(codes, force=False):
    codes = sorted({str(code).strip() for code in codes if str(code).strip()})
    now_text = datetime.now(CN_TZ).strftime('%Y-%m-%d %H:%M:%S')
    if not codes:
        return {'updateTime': now_text, 'stale': False, 'quotes': {}}

    digest = hashlib.md5(','.join(codes).encode('utf-8')).hexdigest()
    cache_key = f'market:fund:quotes:{digest}'
    stale_key = f'{cache_key}:stale'

    if not force:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        raw_map = _fetch_fund_quotes(codes)
        result = {
            'updateTime': now_text,
            'stale': False,
            'quotes': {
                code: quote
                for code, quote in (
                    (code, _build_fund_quote(raw_map.get(code))) for code in codes
                )
                if quote is not None
            },
        }
        cache.set(cache_key, result, FUND_QUOTE_CACHE_TTL)
        cache.set(stale_key, result, FUND_QUOTE_STALE_TTL)
        return result
    except Exception:
        stale = cache.get(stale_key)
        if stale:
            fallback = dict(stale)
            fallback['stale'] = True
            return fallback
        raise


def _previous_trading_day(today):
    """上一个交易日（仅跳过周末，海外节假日按其净值日期自然顺延）"""
    day = datetime.strptime(today, '%Y-%m-%d').date()
    while True:
        day -= timedelta(days=1)
        if day.weekday() < 5:
            return day.strftime('%Y-%m-%d')


def _calc_today_pnl(shares, quote, category, today):
    """当日收益口径：
    海外/QDII 取昨日净值的变化（覆盖海外隔夜行情），净值尚未更新到昨日时不计入；
    其余基金只认当天净值或当天盘中估值，当日数据未出时不计入。
    """
    data_mode = quote.get('dataMode') or 'none'
    nav_date = str(quote.get('navDate') or '')

    if category == 'overseas':
        if nav_date != _previous_trading_day(today):
            return None
        nav = _to_decimal(quote.get('nav'))
        nav_change = _to_decimal(quote.get('navChangePercent'))
        # 兼容旧缓存中没有 navChangePercent 的行情
        if nav_change is None and data_mode == 'nav':
            nav_change = _to_decimal(quote.get('changePercent'))
        if nav is None or nav_change is None or nav_change <= -100:
            return None
        prev_nav = nav / (Decimal('1') + nav_change / Decimal('100'))
        return shares * (nav - prev_nav)

    if data_mode == 'estimate' or (data_mode == 'nav' and nav_date == today):
        current_nav = _to_decimal(quote.get('currentNav'))
        prev_nav = _to_decimal(quote.get('prevNav'))
        if current_nav is None or prev_nav is None:
            return None
        return shares * (current_nav - prev_nav)

    return None


def get_fund_portfolio_data(user_id, force=False):
    holdings = list(
        FundHolding.objects.filter(user=user_id).order_by('sort', 'createTime')
    )
    # 已清仓基金不参与当前市值和行情计算
    quote_codes = [
        holding.fundCode
        for holding in holdings
        if Decimal(str(holding.shares)) > 0
    ]
    quote_data = get_fund_quotes(quote_codes, force)
    quotes = quote_data.get('quotes') or {}

    total_cost = Decimal('0')
    total_value = Decimal('0')
    total_today_pnl = Decimal('0')
    total_today_prev_value = Decimal('0')
    total_pnl = Decimal('0')
    total_realized_pnl = Decimal('0')
    incomplete = False
    category_map = {}
    today = datetime.now(CN_TZ).strftime('%Y-%m-%d')

    items = []
    for holding in holdings:
        quote = quotes.get(holding.fundCode) or {}
        shares = Decimal(str(holding.shares))
        cost_nav = Decimal(str(holding.costNav))
        realized_pnl = Decimal(str(holding.realizedPnl or 0))
        cost_amount = shares * cost_nav

        if shares == 0:
            status = 'cleared'
        elif realized_pnl != 0:
            status = 'partial'
        else:
            status = 'holding'

        if status == 'cleared':
            market_value = Decimal('0')
            today_pnl = None
            holding_pnl = Decimal('0')
            total_return_rate = None
            day_return_rate = None
        else:
            current_nav = _to_decimal(quote.get('currentNav'))
            prev_nav = _to_decimal(quote.get('prevNav'))

            market_value = shares * current_nav if current_nav is not None else None
            today_pnl = _calc_today_pnl(shares, quote, holding.category, today)
            holding_pnl = market_value - cost_amount if market_value is not None else None
            total_return_rate = (
                holding_pnl / cost_amount * 100
                if holding_pnl is not None and cost_amount > 0
                else None
            )
            previous_value = market_value - today_pnl if market_value is not None and today_pnl is not None else None
            day_return_rate = (
                today_pnl / previous_value * 100
                if today_pnl is not None and previous_value is not None and previous_value > 0
                else None
            )

        item = {
            'id': str(holding.id),
            'fundCode': holding.fundCode,
            'fundName': quote.get('name') or holding.fundName,
            'fundType': holding.fundType or '',
            'category': holding.category,
            'style': holding.style,
            'status': status,
            'shares': _json_number(shares, 4),
            'costNav': _json_number(cost_nav, 4),
            'realizedPnl': _json_number(realized_pnl, 2),
            'remark': holding.remark or '',
            'sort': holding.sort,
            'nav': quote.get('nav'),
            'navDate': quote.get('navDate') or '',
            'estimateNav': quote.get('estimateNav'),
            'estimateChangePercent': quote.get('estimateChangePercent'),
            'estimateTime': quote.get('estimateTime') or '',
            'currentNav': quote.get('currentNav'),
            'prevNav': quote.get('prevNav'),
            'changePercent': quote.get('changePercent'),
            'quoteTime': quote.get('quoteTime') or '',
            'dataMode': quote.get('dataMode') or 'none',
            'costAmount': _json_number(cost_amount, 2),
            'marketValue': _json_number(market_value, 2),
            'todayPnl': _json_number(today_pnl, 2),
            'totalPnl': _json_number(holding_pnl, 2),
            'totalReturnRate': _json_number(total_return_rate, 2),
            'dayReturnRate': _json_number(day_return_rate, 2),
            'ratio': None,
        }

        total_cost += cost_amount
        total_realized_pnl += realized_pnl

        if status != 'cleared':
            if market_value is not None and holding_pnl is not None:
                total_value += market_value
                total_pnl += holding_pnl
            else:
                incomplete = True
            if today_pnl is not None:
                total_today_pnl += today_pnl
                if market_value is not None:
                    total_today_prev_value += market_value - today_pnl

            category_stat = category_map.setdefault(holding.category, {
                'category': holding.category,
                'count': 0,
                'marketValue': Decimal('0'),
                'todayPnl': Decimal('0'),
                'totalPnl': Decimal('0'),
            })
            category_stat['count'] += 1
            if market_value is not None and holding_pnl is not None:
                category_stat['marketValue'] += market_value
                category_stat['totalPnl'] += holding_pnl
            if today_pnl is not None:
                category_stat['todayPnl'] += today_pnl

        items.append((item, market_value))

    for item, market_value in items:
        item['ratio'] = (
            _json_number(market_value / total_value * 100, 2)
            if item['status'] != 'cleared' and market_value is not None and total_value > 0
            else None
        )

    categories = [
        {
            'category': key,
            'name': FUND_CATEGORY_NAMES.get(key, '其他'),
            'count': value['count'],
            'marketValue': _json_number(value['marketValue'], 2),
            'todayPnl': _json_number(value['todayPnl'], 2),
            'totalPnl': _json_number(value['totalPnl'], 2),
            'ratio': (
                _json_number(value['marketValue'] / total_value * 100, 2)
                if total_value > 0
                else None
            ),
        }
        for key, value in sorted(
            category_map.items(),
            key=lambda item: item[1]['marketValue'],
            reverse=True,
        )
    ]

    summary = {
        'totalCost': _json_number(total_cost, 2),
        'totalMarketValue': _json_number(total_value, 2),
        'totalTodayPnl': _json_number(total_today_pnl, 2),
        'totalPnl': _json_number(total_pnl, 2),
        'totalReturnRate': (
            _json_number(total_pnl / total_cost * 100, 2)
            if total_cost > 0
            else None
        ),
        'totalRealizedPnl': _json_number(total_realized_pnl, 2),
        'totalPnlIncludingRealized': _json_number(total_pnl + total_realized_pnl, 2),
        'todayReturnRate': (
            _json_number(total_today_pnl / total_today_prev_value * 100, 2)
            if total_today_prev_value > 0
            else None
        ),
        'incomplete': incomplete,
    }

    return {
        'updateTime': quote_data.get('updateTime') or datetime.now(CN_TZ).strftime('%Y-%m-%d %H:%M:%S'),
        'stale': bool(quote_data.get('stale')),
        'summary': summary,
        'categories': categories,
        'items': [item for item, _ in items],
    }


def validate_fund_holding_params(fund_code, shares, cost_nav, realized_pnl, category, style):
    if not re.fullmatch(r'\d{6}', fund_code or ''):
        return '基金代码应为 6 位数字'
    if shares is None or shares < 0:
        return '持有份额不能小于 0'
    if realized_pnl is None:
        return '已实现收益格式不正确'
    if cost_nav is None or cost_nav < 0:
        return '持仓成本价不能小于 0'
    if shares > 0 and cost_nav <= 0:
        return '持有份额大于 0 时请填写持仓成本价'
    if category and category not in VALID_CATEGORIES:
        return '资产类别不正确'
    if style and style not in VALID_STYLES:
        return '管理方式不正确'
    return ''


def save_fund_holding(user_id, params):
    holding = None
    holding_id = params.get('id')
    if holding_id:
        if not _is_uuid(holding_id):
            raise ValueError('持仓不存在')
        holding = FundHolding.objects.filter(id=holding_id, user=user_id).first()
        if not holding:
            raise ValueError('持仓不存在')

    fund_code = str(params.get('fundCode') or (holding.fundCode if holding else '')).strip()
    shares = _to_decimal(params.get('shares'))
    cost_nav = _to_decimal(params.get('costNav'))
    realized_pnl = _to_decimal(params.get('realizedPnl'))
    shares = _round(shares, 4) if shares is not None else None
    cost_nav = _round(cost_nav, 4) if cost_nav is not None else Decimal('0')
    realized_pnl = _round(realized_pnl, 2) if realized_pnl is not None else Decimal('0')
    category = str(params.get('category') or '').strip()
    style = str(params.get('style') or '').strip()
    remark = str(params.get('remark') or '').strip()[:255]

    msg = validate_fund_holding_params(
        fund_code,
        shares,
        cost_nav,
        realized_pnl,
        category,
        style,
    )
    if msg:
        raise ValueError(msg)

    try:
        sort_value = int(params.get('sort'))
    except (TypeError, ValueError):
        sort_value = holding.sort if holding else 0

    meta = None
    code_changed = holding is None or holding.fundCode != fund_code
    if code_changed:
        if FundHolding.objects.filter(user=user_id, fundCode=fund_code).exists():
            raise ValueError('该基金已在持仓中')
        meta = get_fund_meta(fund_code)
        if not meta:
            raise ValueError('未找到该基金')

    if not category:
        category = meta['category'] if meta else holding.category
    if not style or style == 'unknown':
        style = meta['style'] if meta else (holding.style if holding else 'unknown')

    if holding:
        holding.fundCode = fund_code
        if meta:
            holding.fundName = meta['name']
            holding.fundType = meta['type']
        holding.category = category
        holding.style = style
        holding.shares = shares
        holding.costNav = cost_nav
        holding.realizedPnl = realized_pnl
        holding.remark = remark
        holding.sort = sort_value
        holding.save()
        return holding

    return FundHolding.objects.create(
        user=user_id,
        fundCode=fund_code,
        fundName=meta['name'],
        fundType=meta['type'],
        category=category,
        style=style,
        shares=shares,
        costNav=cost_nav,
        realizedPnl=realized_pnl,
        remark=remark,
        sort=sort_value,
    )


def delete_fund_holdings(user_id, ids):
    if not isinstance(ids, (list, tuple)) or not ids:
        raise ValueError('请选择要删除的持仓')
    valid_ids = [item for item in ids if _is_uuid(item)]
    if not valid_ids:
        raise ValueError('持仓不存在')
    return FundHolding.objects.filter(id__in=valid_ids, user=user_id).delete()
