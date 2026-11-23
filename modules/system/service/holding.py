from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from modules.system.models import CashHolding, FundHolding, HoldingSnapshot
from modules.system.service.cash import get_cash_portfolio_data
from modules.system.service.fund import (
    FUND_CATEGORY_NAMES,
    _json_number,
    _to_decimal,
    get_fund_portfolio_data,
)

CN_TZ = ZoneInfo('Asia/Shanghai')
SATURDAY = 5
CASH_GROUP_NAMES = {
    'money_fund': '余额宝/货币基金',
    'deposit': '银行存款',
}


def _today():
    return datetime.now(CN_TZ).date()


def _fund_items(fund_data):
    items = []
    for item in fund_data.get('items') or []:
        # 已清仓基金不进入趋势统计
        if item.get('status') == 'cleared':
            continue
        category = item.get('category') or 'other'
        value = _to_decimal(item.get('marketValue')) or Decimal('0')
        principal = _to_decimal(item.get('costAmount')) or Decimal('0')
        holding_pnl = _to_decimal(item.get('totalPnl')) or Decimal('0')
        realized_pnl = _to_decimal(item.get('realizedPnl')) or Decimal('0')
        items.append({
            'key': f"fund:{item.get('fundCode') or ''}",
            'type': 'fund',
            'name': item.get('fundName') or '',
            'code': item.get('fundCode') or '',
            'group': category,
            'groupName': FUND_CATEGORY_NAMES.get(category, '其他'),
            'value': _json_number(value, 2),
            'principal': _json_number(principal, 2),
            'pnl': _json_number(holding_pnl + realized_pnl, 2),
            'realizedPnl': _json_number(realized_pnl, 2),
            'status': item.get('status'),
        })
    return items


def _cash_items(cash_data):
    items = []
    for item in cash_data.get('items') or []:
        kind = item.get('kind') or 'money_fund'
        value = _to_decimal(item.get('balance')) or Decimal('0')
        principal = _to_decimal(item.get('principal')) or Decimal('0')
        pnl = _to_decimal(item.get('totalPnl')) or Decimal('0')
        items.append({
            'key': f"cash:{item.get('id') or ''}",
            'type': kind,
            'name': item.get('name') or '',
            'code': item.get('fundCode') or '',
            'group': f'cash_{kind}',
            'groupName': CASH_GROUP_NAMES.get(kind, '现金/存款'),
            'value': _json_number(value, 2),
            'principal': _json_number(principal, 2),
            'pnl': _json_number(pnl, 2),
            'realizedPnl': None,
            'status': item.get('status'),
        })
    return items


def record_holding_snapshot(user_id):
    """记录当天持仓快照；同一天重复调用会覆盖为最新值。"""
    fund_data = get_fund_portfolio_data(user_id)
    cash_data = get_cash_portfolio_data(user_id)
    fund_summary = fund_data.get('summary') or {}
    cash_summary = cash_data.get('summary') or {}

    fund_value = _to_decimal(fund_summary.get('totalMarketValue')) or Decimal('0')
    cash_value = _to_decimal(cash_summary.get('totalBalance')) or Decimal('0')
    fund_principal = _to_decimal(fund_summary.get('totalCost')) or Decimal('0')
    cash_principal = _to_decimal(cash_summary.get('totalPrincipal')) or Decimal('0')
    fund_pnl = _to_decimal(fund_summary.get('totalPnlIncludingRealized')) or Decimal('0')
    cash_pnl = _to_decimal(cash_summary.get('totalPnl')) or Decimal('0')

    snapshot, _ = HoldingSnapshot.objects.update_or_create(
        user=user_id,
        snapshotDate=_today(),
        defaults={
            'totalValue': _json_number(fund_value + cash_value, 2),
            'totalPrincipal': _json_number(fund_principal + cash_principal, 2),
            'totalPnl': _json_number(fund_pnl + cash_pnl, 2),
            'fundValue': _json_number(fund_value, 2),
            'cashValue': _json_number(cash_value, 2),
            'complete': not (
                fund_summary.get('incomplete') or cash_summary.get('incomplete')
            ),
            'items': _fund_items(fund_data) + _cash_items(cash_data),
        },
    )
    return snapshot


def _serialize_snapshot(snapshot):
    return {
        'date': snapshot.snapshotDate.strftime('%Y-%m-%d'),
        'totalValue': float(snapshot.totalValue or 0),
        'totalPrincipal': float(snapshot.totalPrincipal or 0),
        'totalPnl': float(snapshot.totalPnl or 0),
        'fundValue': float(snapshot.fundValue or 0),
        'cashValue': float(snapshot.cashValue or 0),
        'complete': snapshot.complete,
        # 兼容历史快照：读取时同样过滤已清仓基金
        'items': [
            item
            for item in (snapshot.items or [])
            if item.get('status') != 'cleared'
        ],
    }


def get_holding_history(user_id):
    snapshots = HoldingSnapshot.objects.filter(user=user_id).order_by('snapshotDate')
    return [_serialize_snapshot(item) for item in snapshots]


def get_holding_remind_status(user_id):
    now = datetime.now(CN_TZ)
    today = now.date()
    is_saturday = now.weekday() == SATURDAY
    has_holdings = (
        FundHolding.objects.filter(user=user_id).exists()
        or CashHolding.objects.filter(user=user_id).exists()
    )
    today_snapshot = HoldingSnapshot.objects.filter(
        user=user_id, snapshotDate=today
    ).exists()
    last_snapshot = (
        HoldingSnapshot.objects.filter(user=user_id)
        .order_by('-snapshotDate')
        .first()
    )
    return {
        'isSaturday': is_saturday,
        'needRemind': bool(is_saturday and has_holdings and not today_snapshot),
        'lastSnapshotDate': (
            last_snapshot.snapshotDate.strftime('%Y-%m-%d')
            if last_snapshot
            else ''
        ),
    }
