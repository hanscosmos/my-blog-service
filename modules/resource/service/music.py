from uuid import UUID

from django.db import transaction
from django.db.models import F, Max

from modules.resource.models import Music

# 列表返回字段，与前端 MusicItemType 保持一致
MUSIC_FIELDS = (
    'id',
    'name',
    'singer',
    'cover',
    'url',
    'duration',
    'playCount',
    'listenSeconds',
    'sort',
    'createTime',
)

# 排序模式 -> 排序字段；统计类默认降序，手动排序按 sort 升序
MUSIC_ORDER_MAP = {
    'manual': ('sort', 'createTime'),
    'playCount': ('-playCount', 'sort'),
    'listenSeconds': ('-listenSeconds', 'sort'),
}

# 单次上报的收听秒数上限，防止异常数据
MAX_REPORT_SECONDS = 300


def _is_uuid(value):
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def clean_music_params(params):
    """提取并规范化允许入库的字段（统计字段不允许由前端写入）"""
    try:
        duration = int(params.get('duration') or 0)
    except (TypeError, ValueError):
        duration = -1
    return {
        'name': str(params.get('name') or '').strip(),
        'singer': str(params.get('singer') or '').strip(),
        'cover': str(params.get('cover') or '').strip(),
        'url': str(params.get('url') or '').strip(),
        'duration': duration,
    }


def validate_music_params(data, music_id=None):
    msg = ''
    if not data['name']:
        msg = '歌曲名不得为空'
    elif len(data['name']) > 64:
        msg = '歌曲名长度不得超过64'
    elif len(data['singer']) > 64:
        msg = '歌手名长度不得超过64'
    elif len(data['cover']) > 200:
        msg = '封面地址过长'
    elif not data['url']:
        msg = '请上传音频文件'
    elif len(data['url']) > 200:
        msg = '音频地址过长'
    elif data['duration'] < 0 or data['duration'] > 86400:
        msg = '音频时长不合法'
    else:
        url_sql = Music.objects.filter(url=data['url'])
        if music_id:
            url_sql = url_sql.exclude(id=music_id)
        if url_sql.exists():
            msg = '该音频文件已存在'
    return msg


def get_music_order_fields(sort_by):
    return MUSIC_ORDER_MAP.get(sort_by) or MUSIC_ORDER_MAP['manual']


def get_music_list(params):
    sql = Music.objects.all()
    name = str(params.get('name') or '').strip()
    singer = str(params.get('singer') or '').strip()
    if name:
        sql = sql.filter(name__contains=name)
    if singer:
        sql = sql.filter(singer__contains=singer)
    return sql.order_by(*get_music_order_fields(params.get('sortBy'))).values(*MUSIC_FIELDS)


def get_all_music():
    return list(Music.objects.order_by('sort', 'createTime').values(*MUSIC_FIELDS))


def create_music(data):
    max_sort = Music.objects.aggregate(max_sort=Max('sort'))['max_sort'] or 0
    Music.objects.create(**data, sort=max_sort + 1)


def update_music(music_id, data):
    if not _is_uuid(music_id):
        raise ValueError('音乐不存在')
    updated = Music.objects.filter(id=music_id).update(**data)
    if not updated:
        raise ValueError('音乐不存在')


def delete_music(ids):
    if not isinstance(ids, list) or not ids or not all(_is_uuid(item) for item in ids):
        raise ValueError('请选择要删除的音乐')
    Music.objects.filter(id__in=ids).delete()


@transaction.atomic
def update_music_sort(ids):
    """按传入的 id 顺序重写 sort 字段"""
    if not isinstance(ids, list) or not ids or not all(_is_uuid(item) for item in ids):
        raise ValueError('排序列表不合法')
    music_list = list(Music.objects.filter(id__in=ids))
    if len(music_list) != len(ids):
        raise ValueError('存在无效的音乐记录')
    music_map = {str(item.id).lower(): item for item in music_list}
    for index, music_id in enumerate(ids):
        music_map[str(music_id).lower()].sort = index
    Music.objects.bulk_update(music_list, ['sort'])


def increase_play_count(music_id):
    if not _is_uuid(music_id):
        raise ValueError('音乐不存在')
    updated = Music.objects.filter(id=music_id).update(playCount=F('playCount') + 1)
    if not updated:
        raise ValueError('音乐不存在')


def increase_listen_seconds(music_id, seconds):
    if not _is_uuid(music_id):
        raise ValueError('音乐不存在')
    try:
        seconds = int(seconds or 0)
    except (TypeError, ValueError):
        raise ValueError('收听时长不合法')
    seconds = max(0, min(seconds, MAX_REPORT_SECONDS))
    if not seconds:
        return 0
    updated = Music.objects.filter(id=music_id).update(
        listenSeconds=F('listenSeconds') + seconds
    )
    if not updated:
        raise ValueError('音乐不存在')
    return seconds
