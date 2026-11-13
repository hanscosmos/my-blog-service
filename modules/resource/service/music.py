from urllib.parse import urlparse
from uuid import UUID, uuid4

import requests
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.db.models import F, Max

from modules.resource.models import Music
from modules.resource.service.music_meta import extract_music_metadata
from utils.upload import upload_file_to_server

# 列表返回字段，与前端 MusicItemType 保持一致
MUSIC_FIELDS = (
    'id',
    'name',
    'singer',
    'cover',
    'url',
    'duration',
    'language',
    'genre',
    'lyric',
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

# 歌词最大长度，需与前端保持一致
MAX_LYRIC_LENGTH = 20000

# 解析旧音频时允许下载的最大体积
MAX_AUDIO_BYTES = 80 * 1024 * 1024

# 从内嵌封面还原出的图片仍按音乐封面目录存储，并沿用长缓存策略
MUSIC_COVER_TYPE = 'music-cover'
MUSIC_COVER_CACHE_CONTROL = 'public, max-age=31536000'
COVER_EXTENSION_MAP = {
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp',
    'image/gif': 'gif',
    'image/bmp': 'bmp',
}


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
        'language': str(params.get('language') or '').strip(),
        'genre': str(params.get('genre') or '').strip(),
        'lyric': str(params.get('lyric') or '').strip(),
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
    elif len(data['language']) > 32:
        msg = '语种不合法'
    elif len(data['genre']) > 32:
        msg = '风格不合法'
    elif len(data['lyric']) > MAX_LYRIC_LENGTH:
        msg = f'歌词长度不得超过{MAX_LYRIC_LENGTH}'
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
    language = str(params.get('language') or '').strip()
    genre = str(params.get('genre') or '').strip()
    if name:
        sql = sql.filter(name__contains=name)
    if singer:
        sql = sql.filter(singer__contains=singer)
    if language:
        sql = sql.filter(language=language)
    if genre:
        sql = sql.filter(genre=genre)
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


def download_music_audio(url):
    """下载已上传的音频文件，用于解析内嵌信息"""
    parsed = urlparse(str(url or ''))
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise ValueError('音频地址不合法')
    try:
        with requests.get(url, stream=True, timeout=(5, 60)) as response:
            if response.status_code != 200:
                raise ValueError('音频下载失败')
            content_length = int(response.headers.get('Content-Length') or 0)
            if content_length > MAX_AUDIO_BYTES:
                raise ValueError('音频文件过大，无法解析')
            buffer = bytearray()
            for chunk in response.iter_content(chunk_size=256 * 1024):
                if not chunk:
                    continue
                buffer.extend(chunk)
                if len(buffer) > MAX_AUDIO_BYTES:
                    raise ValueError('音频文件过大，无法解析')
    except requests.RequestException:
        raise ValueError('音频下载失败，请检查文件是否可以访问')
    if not buffer:
        raise ValueError('音频下载失败')
    return bytes(buffer)


def _upload_music_cover(data, mime):
    """把解析出的封面按音乐封面目录上传到 COS"""
    mime = (mime or '').lower()
    extension = COVER_EXTENSION_MAP.get(mime, 'jpg')
    file_name = f'{uuid4().hex}.{extension}'
    upload = SimpleUploadedFile(file_name, data, content_type=mime or 'image/jpeg')
    return upload_file_to_server(
        upload, file_name, MUSIC_COVER_TYPE, MUSIC_COVER_CACHE_CONTROL
    )


def extract_music_embedded_info(music_id):
    """
    根据已上传的音频地址重新解析内嵌信息。

    只补充空字段（名称/歌手/歌词/封面），已有内容不会被覆盖。
    """
    if not _is_uuid(music_id):
        raise ValueError('音乐不存在')
    music = Music.objects.filter(id=music_id).first()
    if not music:
        raise ValueError('音乐不存在')

    audio_data = download_music_audio(music.url)
    try:
        info = extract_music_metadata(audio_data)
    except ValueError:
        raise
    except Exception:
        raise ValueError('音频解析失败')

    updates = {}
    updated = []
    if not music.name and info['name']:
        updates['name'] = info['name'][:64]
        updated.append('name')
    if not music.singer and info['singer']:
        updates['singer'] = info['singer'][:64]
        updated.append('singer')
    lyric = (info['lyric'] or '').replace('﻿', '').strip()
    if not music.lyric and lyric:
        updates['lyric'] = lyric[:MAX_LYRIC_LENGTH]
        updated.append('lyric')
    if not music.cover and info['cover']:
        try:
            cover_url = _upload_music_cover(info['cover'], info['cover_mime'])
        except Exception:
            cover_url = ''
        if cover_url:
            updates['cover'] = cover_url
            updated.append('cover')
    if updates:
        Music.objects.filter(id=music.id).update(**updates)

    return {
        'id': str(music.id),
        'updated': updated,
        'name': updates.get('name', music.name),
        'singer': updates.get('singer', music.singer),
        'lyric': updates.get('lyric', music.lyric),
        'cover': updates.get('cover', music.cover or ''),
    }
