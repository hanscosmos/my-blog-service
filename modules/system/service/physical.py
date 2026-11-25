from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from modules.system.models import Dictionary, PhysicalAsset
from modules.system.service.fund import (
    _is_uuid,
    _json_number,
    _round,
    _time_text,
    _to_decimal,
)

CN_TZ = ZoneInfo('Asia/Shanghai')
PHYSICAL_DICT_CODE = 'PHYSICAL_ASSET_CATEGORY'
MAX_PHYSICAL_IMAGES = 9
MAX_IMAGE_URL_LENGTH = 800

# 预设类别固定，自定义类别放在字典 PHYSICAL_ASSET_CATEGORY 中维护
PRESET_CATEGORIES = [
    {'key': 'house', 'name': '房产'},
    {'key': 'vehicle', 'name': '车辆'},
    {'key': 'precious_metal', 'name': '贵金属'},
    {'key': 'collectible', 'name': '收藏品'},
    {'key': 'other', 'name': '其他'},
]
PRESET_CATEGORY_MAP = {item['key']: item['name'] for item in PRESET_CATEGORIES}


def _today():
    return datetime.now(CN_TZ).date()


def _parse_date(value):
    text = str(value or '').strip()
    if not text:
        return None
    text = text[:10]
    try:
        return datetime.strptime(text, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError('日期格式不正确')


def _dict_category_rows():
    try:
        return list(
            Dictionary.objects.filter(code=PHYSICAL_DICT_CODE)
            .order_by('sort', 'createTime')
            .values('key', 'value', 'sort', 'status')
        )
    except Exception:
        return []


def _category_options(rows):
    """预设类别 + 字典中启用的自定义类别"""
    options = [dict(item, preset=True) for item in PRESET_CATEGORIES]
    seen = set(PRESET_CATEGORY_MAP)
    for row in rows:
        if not row.get('status'):
            continue
        key = str(row.get('key') or '').strip()
        name = str(row.get('value') or '').strip()
        if not key or not name or key in seen:
            continue
        options.append({'key': key, 'name': name, 'preset': False})
        seen.add(key)
    return options


def _category_name_map(rows):
    """类别名称解析：包含已停用/已删除的自定义类别，保证历史数据显示可读"""
    name_map = dict(PRESET_CATEGORY_MAP)
    for row in rows:
        key = str(row.get('key') or '').strip()
        name = str(row.get('value') or '').strip()
        if key and name and key not in name_map:
            name_map[key] = name
    return name_map


def _asset_decimal(value):
    decimal_value = _to_decimal(value)
    return decimal_value if decimal_value is not None else Decimal('0')


def _normalize_images(value):
    if not isinstance(value, (list, tuple)):
        return []
    images = []
    for item in value:
        url = str(item or '').strip()
        if not url or url in images:
            continue
        images.append(url)
        if len(images) >= MAX_PHYSICAL_IMAGES:
            break
    return images


def _clean_image_url(value):
    url = str(value or '').strip()
    if not url:
        return ''
    if len(url) > MAX_IMAGE_URL_LENGTH:
        raise ValueError('图片地址过长')
    if not url.startswith(('http://', 'https://')):
        raise ValueError('图片地址格式不正确')
    return url


def _clean_images(value):
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError('图片列表格式不正确')
    if len(value) > MAX_PHYSICAL_IMAGES:
        raise ValueError(f'最多上传 {MAX_PHYSICAL_IMAGES} 张图片')
    images = []
    for item in value:
        url = _clean_image_url(item)
        if url and url not in images:
            images.append(url)
    return images


def _serialize_item(asset, category, category_name):
    current_value = _asset_decimal(asset.currentValue)
    cost_value = _asset_decimal(asset.costValue)
    pnl = current_value - cost_value
    return {
        'id': str(asset.id),
        'category': category,
        'categoryName': category_name,
        'name': asset.name,
        'currentValue': _json_number(current_value, 2),
        'costValue': _json_number(cost_value, 2),
        'pnl': _json_number(pnl, 2),
        'returnRate': (
            _json_number(pnl / cost_value * 100, 2) if cost_value > 0 else None
        ),
        'cover': asset.cover or '',
        'images': _normalize_images(asset.images),
        'purchaseDate': (
            asset.purchaseDate.strftime('%Y-%m-%d') if asset.purchaseDate else ''
        ),
        'valuationDate': (
            asset.valuationDate.strftime('%Y-%m-%d') if asset.valuationDate else ''
        ),
        'remark': asset.remark or '',
        'sort': asset.sort,
        'updateTime': _time_text(asset.updateTime),
    }


def get_physical_portfolio_data(user_id):
    assets = list(
        PhysicalAsset.objects.filter(user=user_id).order_by('sort', 'createTime')
    )
    rows = _dict_category_rows()
    name_map = _category_name_map(rows)
    options = _category_options(rows)

    items = []
    stat_map = {}
    total_value = Decimal('0')
    total_cost = Decimal('0')

    for asset in assets:
        category = asset.category or 'other'
        category_name = name_map.get(category, PRESET_CATEGORY_MAP['other'])
        item = _serialize_item(asset, category, category_name)
        items.append(item)

        current_value = _asset_decimal(asset.currentValue)
        cost_value = _asset_decimal(asset.costValue)
        total_value += current_value
        total_cost += cost_value

        stat = stat_map.get(category)
        if not stat:
            stat = {
                'key': category,
                'name': category_name,
                'count': 0,
                'value': Decimal('0'),
                'cost': Decimal('0'),
            }
            stat_map[category] = stat
        stat['count'] += 1
        stat['value'] += current_value
        stat['cost'] += cost_value

    total_pnl = total_value - total_cost
    order_index = {item['key']: index for index, item in enumerate(options)}
    categories = sorted(
        stat_map.values(),
        key=lambda item: (order_index.get(item['key'], 999), -item['value']),
    )
    category_list = []
    for stat in categories:
        pnl = stat['value'] - stat['cost']
        category_list.append({
            'key': stat['key'],
            'name': stat['name'],
            'count': stat['count'],
            'value': _json_number(stat['value'], 2),
            'cost': _json_number(stat['cost'], 2),
            'pnl': _json_number(pnl, 2),
            'returnRate': (
                _json_number(pnl / stat['cost'] * 100, 2)
                if stat['cost'] > 0
                else None
            ),
            'ratio': (
                _json_number(stat['value'] / total_value * 100, 2)
                if total_value > 0
                else None
            ),
        })

    latest_update = max((asset.updateTime for asset in assets), default=None)
    return {
        'updateTime': _time_text(latest_update),
        'summary': {
            'count': len(assets),
            'totalValue': _json_number(total_value, 2),
            'totalCost': _json_number(total_cost, 2),
            'totalPnl': _json_number(total_pnl, 2),
            'totalReturnRate': (
                _json_number(total_pnl / total_cost * 100, 2)
                if total_cost > 0
                else None
            ),
        },
        'categories': category_list,
        'categoryOptions': options,
        'items': items,
    }


def save_physical_asset(user_id, params):
    asset = None
    asset_id = params.get('id')
    if asset_id:
        if not _is_uuid(asset_id):
            raise ValueError('资产不存在')
        asset = PhysicalAsset.objects.filter(id=asset_id, user=user_id).first()
        if not asset:
            raise ValueError('资产不存在')

    options = _category_options(_dict_category_rows())
    allowed_keys = {item['key'] for item in options}
    category = str(
        params.get('category') or (asset.category if asset else '')
    ).strip()
    if not category:
        raise ValueError('请选择资产类别')
    if len(category) > 32:
        raise ValueError('资产类别标识过长')
    # 编辑时允许保留已被删除/停用的历史类别，其它情况必须是有效类别
    if category not in allowed_keys and not (asset and category == asset.category):
        raise ValueError('资产类别不存在或已停用')

    name = str(params.get('name') or '').strip()[:128]
    if not name:
        raise ValueError('请填写资产名称')

    current_value = _to_decimal(params.get('currentValue'))
    if current_value is None or current_value < 0:
        raise ValueError('当前估值不能小于 0')

    cost_value = _to_decimal(params.get('costValue'))
    if cost_value is None or cost_value < 0:
        raise ValueError('购入成本不能小于 0')

    if 'cover' in params:
        cover = _clean_image_url(params.get('cover')) or None
    else:
        cover = asset.cover if asset else None

    if 'images' in params:
        images = _clean_images(params.get('images'))
    else:
        images = _normalize_images(asset.images) if asset else []

    if 'purchaseDate' in params:
        purchase_date = _parse_date(params.get('purchaseDate'))
    else:
        purchase_date = asset.purchaseDate if asset else None

    if 'valuationDate' in params:
        valuation_date = _parse_date(params.get('valuationDate'))
    else:
        valuation_date = asset.valuationDate if asset else _today()

    remark = str(params.get('remark') or '').strip()[:255]

    try:
        sort_value = int(params.get('sort'))
    except (TypeError, ValueError):
        sort_value = asset.sort if asset else 0

    fields = {
        'category': category,
        'name': name,
        'currentValue': _round(current_value, 2),
        'costValue': _round(cost_value, 2),
        'cover': cover,
        'images': images,
        'purchaseDate': purchase_date,
        'valuationDate': valuation_date,
        'remark': remark,
        'sort': sort_value,
    }

    if asset:
        for key, value in fields.items():
            setattr(asset, key, value)
        asset.save()
        return asset

    return PhysicalAsset.objects.create(user=user_id, **fields)


def delete_physical_assets(user_id, ids):
    if not isinstance(ids, (list, tuple)) or not ids:
        raise ValueError('请选择要删除的资产')
    valid_ids = [item for item in ids if _is_uuid(item)]
    if not valid_ids:
        raise ValueError('资产不存在')
    return PhysicalAsset.objects.filter(id__in=valid_ids, user=user_id).delete()
