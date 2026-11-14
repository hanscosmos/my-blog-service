import re
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from modules.system.models import CashHolding
from modules.system.service.fund import (
    _is_uuid,
    _json_number,
    _round,
    _to_decimal,
    get_money_fund_quotes,
)

CN_TZ = ZoneInfo('Asia/Shanghai')

DEFAULT_MONEY_FUND_CODE = '000198'
VALID_KINDS = ('money_fund', 'deposit')
VALID_INTEREST_TYPES = ('demand', 'fixed')


def _today():
    return datetime.now(CN_TZ).date()


def _now_text():
    return datetime.now(CN_TZ).strftime('%Y-%m-%d %H:%M:%S')


def _parse_date(value):
    text = str(value or '').strip()
    if not text:
        return None
    text = text[:10]
    try:
        return datetime.strptime(text, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError('日期格式不正确')


def _daily_interest(principal, annual_rate):
    if principal is None or annual_rate is None:
        return None
    return principal * annual_rate / Decimal('100') / Decimal('365')


def _build_money_fund_item(holding, quote):
    balance = Decimal(str(holding.balance)) if holding.balance is not None else Decimal('0')
    principal = Decimal(str(holding.principal)) if holding.principal is not None else balance
    total_pnl = balance - principal
    daily_income = _to_decimal(quote.get('dailyIncome')) if quote else None
    seven_day_rate = _to_decimal(quote.get('sevenDayRate')) if quote else None
    annual_rate = (
        Decimal(str(holding.annualRate))
        if holding.annualRate is not None
        else seven_day_rate
    )
    yesterday_pnl = (
        Decimal(str(holding.yesterdayPnl))
        if holding.yesterdayPnl is not None
        else (balance / Decimal('10000') * daily_income if daily_income is not None else None)
    )

    return {
        'id': str(holding.id),
        'kind': 'money_fund',
        'name': holding.name,
        'fundCode': holding.fundCode or DEFAULT_MONEY_FUND_CODE,
        'balance': _json_number(balance, 2),
        'principal': _json_number(principal, 2),
        'annualRate': _json_number(annual_rate, 4),
        'yesterdayPnl': _json_number(yesterday_pnl, 2),
        'totalPnl': _json_number(total_pnl, 2),
        'totalReturnRate': (
            _json_number(total_pnl / principal * 100, 2) if principal > 0 else None
        ),
        'startDate': '',
        'endDate': '',
        'interestType': None,
        'status': 'active',
        'days': None,
        'maturityInterest': None,
        'remark': holding.remark or '',
        'sort': holding.sort,
        'quoteDate': (quote or {}).get('quoteDate') or '',
        'dailyIncome': _json_number(daily_income, 4),
        'sevenDayRate': _json_number(seven_day_rate, 4),
        'dataMode': 'quote' if daily_income is not None else 'manual',
        'yesterdayPnlManual': holding.yesterdayPnl is not None,
        'annualRateManual': holding.annualRate is not None,
    }


def _build_deposit_item(holding, today):
    principal = Decimal(str(holding.principal)) if holding.principal is not None else Decimal('0')
    annual_rate = Decimal(str(holding.annualRate)) if holding.annualRate is not None else Decimal('0')
    interest_type = holding.interestType or 'demand'
    start_date = holding.startDate
    end_date = holding.endDate
    matured = bool(
        interest_type == 'fixed' and end_date and today > end_date
    )

    if start_date:
        effective_end = min(today, end_date) if end_date and interest_type == 'fixed' else today
        days = max(0, (effective_end - start_date).days + 1)
    else:
        days = 0

    total_pnl = _daily_interest(principal, annual_rate) * days
    balance = principal + total_pnl
    yesterday_pnl = Decimal('0') if matured else _daily_interest(principal, annual_rate)

    maturity_interest = None
    if interest_type == 'fixed' and start_date and end_date:
        term_days = max(0, (end_date - start_date).days + 1)
        maturity_interest = _daily_interest(principal, annual_rate) * term_days

    return {
        'id': str(holding.id),
        'kind': 'deposit',
        'name': holding.name,
        'fundCode': '',
        'balance': _json_number(balance, 2),
        'principal': _json_number(principal, 2),
        'annualRate': _json_number(annual_rate, 4),
        'yesterdayPnl': _json_number(yesterday_pnl, 2),
        'totalPnl': _json_number(total_pnl, 2),
        'totalReturnRate': (
            _json_number(total_pnl / principal * 100, 2) if principal > 0 else None
        ),
        'startDate': start_date.strftime('%Y-%m-%d') if start_date else '',
        'endDate': end_date.strftime('%Y-%m-%d') if end_date else '',
        'interestType': interest_type,
        'status': 'matured' if matured else 'active',
        'days': days,
        'maturityInterest': _json_number(maturity_interest, 2),
        'remark': holding.remark or '',
        'sort': holding.sort,
        'quoteDate': '',
        'dailyIncome': None,
        'sevenDayRate': None,
        'dataMode': 'manual',
        'yesterdayPnlManual': False,
        'annualRateManual': holding.annualRate is not None,
    }


def get_cash_portfolio_data(user_id, force=False):
    holdings = list(
        CashHolding.objects.filter(user=user_id).order_by('sort', 'createTime')
    )
    money_codes = [
        holding.fundCode or DEFAULT_MONEY_FUND_CODE
        for holding in holdings
        if holding.kind == 'money_fund'
    ]
    try:
        quote_data = get_money_fund_quotes(money_codes, force)
    except Exception:
        # 行情失败不影响存款展示，货币基金退化为手动/旧数据口径
        quote_data = {'updateTime': _now_text(), 'stale': True, 'quotes': {}}
    quotes = quote_data.get('quotes') or {}
    today = _today()

    items = []
    total_balance = Decimal('0')
    total_principal = Decimal('0')
    total_yesterday_pnl = Decimal('0')
    total_pnl = Decimal('0')
    rate_numerator = Decimal('0')
    rate_denominator = Decimal('0')
    incomplete = False

    for holding in holdings:
        if holding.kind == 'money_fund':
            code = holding.fundCode or DEFAULT_MONEY_FUND_CODE
            quote = quotes.get(code)
            # 没有可用行情且未手填昨日收益时，当日收益无法计入汇总
            if holding.yesterdayPnl is None and (
                not quote or quote.get('dailyIncome') is None
            ):
                incomplete = True
            item = _build_money_fund_item(holding, quote)
        else:
            item = _build_deposit_item(holding, today)

        balance = _to_decimal(item['balance']) or Decimal('0')
        principal = _to_decimal(item['principal']) or Decimal('0')
        total_balance += balance
        total_principal += principal
        total_pnl += _to_decimal(item['totalPnl']) or Decimal('0')
        if item['yesterdayPnl'] is not None:
            total_yesterday_pnl += _to_decimal(item['yesterdayPnl']) or Decimal('0')
        if item['annualRate'] is not None and balance > 0:
            rate_numerator += balance * _to_decimal(item['annualRate'])
            rate_denominator += balance

        items.append(item)

    summary = {
        'totalBalance': _json_number(total_balance, 2),
        'totalPrincipal': _json_number(total_principal, 2),
        'totalYesterdayPnl': _json_number(total_yesterday_pnl, 2),
        'totalPnl': _json_number(total_pnl, 2),
        'totalReturnRate': (
            _json_number(total_pnl / total_principal * 100, 2)
            if total_principal > 0
            else None
        ),
        'weightedAnnualRate': (
            _json_number(rate_numerator / rate_denominator, 4)
            if rate_denominator > 0
            else None
        ),
        'incomplete': incomplete,
    }

    return {
        'updateTime': quote_data.get('updateTime') or _now_text(),
        'stale': bool(quote_data.get('stale')),
        'summary': summary,
        'items': items,
    }


def save_cash_holding(user_id, params):
    holding = None
    holding_id = params.get('id')
    if holding_id:
        if not _is_uuid(holding_id):
            raise ValueError('资产不存在')
        holding = CashHolding.objects.filter(id=holding_id, user=user_id).first()
        if not holding:
            raise ValueError('资产不存在')

    kind = str(params.get('kind') or (holding.kind if holding else '')).strip()
    if kind not in VALID_KINDS:
        raise ValueError('资产类型不正确')

    name = str(params.get('name') or '').strip()[:128]
    if not name:
        name = '余额宝' if kind == 'money_fund' else '银行存款'
    remark = str(params.get('remark') or '').strip()[:255]

    try:
        sort_value = int(params.get('sort'))
    except (TypeError, ValueError):
        sort_value = holding.sort if holding else 0

    common_fields = {
        'kind': kind,
        'name': name,
        'remark': remark,
        'sort': sort_value,
    }

    if kind == 'money_fund':
        fund_code = str(
            params.get('fundCode')
            or (holding.fundCode if holding else '')
            or DEFAULT_MONEY_FUND_CODE
        ).strip()
        if not re.fullmatch(r'\d{6}', fund_code):
            raise ValueError('货币基金代码应为 6 位数字')

        balance = _to_decimal(params.get('balance'))
        if balance is None or balance < 0:
            raise ValueError('当前余额不能小于 0')
        total_pnl = _to_decimal(params.get('totalPnl')) or Decimal('0')
        principal = balance - total_pnl
        if principal < 0:
            raise ValueError('累计收益不能大于当前余额')

        annual_rate = _to_decimal(params.get('annualRate'))
        if annual_rate is not None and annual_rate < 0:
            raise ValueError('年化收益率不能小于 0')
        yesterday_pnl = _to_decimal(params.get('yesterdayPnl'))
        if yesterday_pnl is not None and yesterday_pnl < 0:
            raise ValueError('昨日收益不能小于 0')

        fields = {
            **common_fields,
            'fundCode': fund_code,
            'balance': _round(balance, 2),
            'principal': _round(principal, 2),
            'annualRate': _round(annual_rate, 4) if annual_rate is not None else None,
            'yesterdayPnl': _round(yesterday_pnl, 2) if yesterday_pnl is not None else None,
            'startDate': None,
            'endDate': None,
            'interestType': None,
        }
    else:
        principal = _to_decimal(params.get('principal'))
        if principal is None or principal <= 0:
            raise ValueError('存款本金应大于 0')

        annual_rate = _to_decimal(params.get('annualRate'))
        if annual_rate is None or annual_rate < 0:
            raise ValueError('请填写年利率')

        interest_type = str(
            params.get('interestType')
            or (holding.interestType if holding else '')
            or 'demand'
        ).strip()
        if interest_type not in VALID_INTEREST_TYPES:
            raise ValueError('计息方式不正确')

        start_date = _parse_date(params.get('startDate')) or (
            holding.startDate if holding else None
        )
        if not start_date:
            raise ValueError('请选择起存日')

        end_date = _parse_date(params.get('endDate')) if interest_type == 'fixed' else None
        if interest_type == 'fixed':
            if not end_date:
                raise ValueError('定期存款请选择到期日')
            if end_date < start_date:
                raise ValueError('到期日不能早于起存日')

        fields = {
            **common_fields,
            'fundCode': None,
            'balance': None,
            'principal': _round(principal, 2),
            'annualRate': _round(annual_rate, 4),
            'yesterdayPnl': None,
            'startDate': start_date,
            'endDate': end_date,
            'interestType': interest_type,
        }

    if holding:
        for key, value in fields.items():
            setattr(holding, key, value)
        holding.save()
        return holding

    return CashHolding.objects.create(user=user_id, **fields)


def delete_cash_holdings(user_id, ids):
    if not isinstance(ids, (list, tuple)) or not ids:
        raise ValueError('请选择要删除的资产')
    valid_ids = [item for item in ids if _is_uuid(item)]
    if not valid_ids:
        raise ValueError('资产不存在')
    return CashHolding.objects.filter(id__in=valid_ids, user=user_id).delete()
