import base64
import io

from mutagen import File as MutagenFile
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

# 内嵌封面大小上限，防止异常数据
MAX_COVER_BYTES = 10 * 1024 * 1024

# ID3 / FLAC 封面类型：3 表示 front cover
FRONT_COVER_TYPE = 3


def _get_text(tags, *keys):
    """从不同格式的标签对象中取第一个非空文本值"""
    for key in keys:
        try:
            value = tags.get(key)
        except (AttributeError, KeyError, TypeError):
            continue
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            if not value:
                continue
            value = value[0]
        text = str(value).strip()
        if text:
            return text
    return ''


def _pick_picture(pictures):
    if not pictures:
        return None
    return next(
        (item for item in pictures if getattr(item, 'type', None) == FRONT_COVER_TYPE),
        pictures[0],
    )


def _cover_from_id3(tags):
    if not isinstance(tags, ID3):
        return None
    frames = tags.getall('APIC')
    frame = _pick_picture(frames)
    if not frame or not frame.data:
        return None
    return bytes(frame.data), frame.mime or 'image/jpeg'


def _cover_from_flac(audio):
    picture = _pick_picture(getattr(audio, 'pictures', None))
    if not picture or not picture.data:
        return None
    return bytes(picture.data), picture.mime or 'image/jpeg'


def _cover_from_mp4(tags):
    covers = tags.get('covr') or []
    if not covers:
        return None
    cover = covers[0]
    mime = 'image/png' if cover.imageformat == MP4Cover.FORMAT_PNG else 'image/jpeg'
    return bytes(cover), mime


def _cover_from_vorbis(tags):
    blocks = tags.get('metadata_block_picture') or []
    if not blocks:
        return None
    try:
        picture = Picture(base64.b64decode(blocks[0]))
    except Exception:
        return None
    if not picture.data:
        return None
    return bytes(picture.data), picture.mime or 'image/jpeg'


def extract_music_metadata(data):
    """
    解析音频文件的内嵌信息。

    返回 {name, singer, lyric, cover, cover_mime}，无法解析的项为空。
    歌词保留原始文本（若内嵌 LRC，则继续带时间戳）。
    """
    audio = MutagenFile(io.BytesIO(data))
    if audio is None:
        raise ValueError('无法识别的音频格式')

    tags = getattr(audio, 'tags', None) or {}
    name = singer = lyric = ''
    cover = None

    if isinstance(audio, MP4):
        name = _get_text(tags, '\xa9nam')
        singer = _get_text(tags, '\xa9ART', 'aART')
        lyric = _get_text(tags, '\xa9lyr')
        cover = _cover_from_mp4(tags)
    elif isinstance(audio, FLAC):
        name = _get_text(tags, 'TITLE')
        singer = _get_text(tags, 'ARTIST')
        lyric = _get_text(tags, 'LYRICS', 'UNSYNCEDLYRICS')
        cover = _cover_from_flac(audio)
    elif isinstance(audio, (OggVorbis, OggOpus)):
        name = _get_text(tags, 'TITLE')
        singer = _get_text(tags, 'ARTIST')
        lyric = _get_text(tags, 'LYRICS', 'UNSYNCEDLYRICS')
        cover = _cover_from_vorbis(tags)
    else:
        # MP3 / WAVE / AIFF 等通常使用 ID3 标签
        id3_tags = tags if isinstance(tags, ID3) else None
        if id3_tags is not None:
            name = _get_text(id3_tags, 'TIT2')
            singer = _get_text(id3_tags, 'TPE1')
            lyric_frames = id3_tags.getall('USLT')
            if lyric_frames:
                lyric = str(lyric_frames[0].text or '').strip()
            cover = _cover_from_id3(id3_tags)

    cover_data, cover_mime = '', ''
    if cover:
        raw, mime = cover
        if raw and len(raw) <= MAX_COVER_BYTES:
            cover_data, cover_mime = raw, mime or 'image/jpeg'

    return {
        'name': name,
        'singer': singer,
        'lyric': lyric,
        'cover': cover_data,
        'cover_mime': cover_mime,
    }
