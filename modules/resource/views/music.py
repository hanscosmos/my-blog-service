from django.views.decorators.http import require_POST

from modules.authority.service.permission import is_super_user
from modules.resource.service.music import (
    clean_music_params,
    create_music,
    delete_music,
    extract_music_embedded_info,
    get_all_music,
    get_music_list,
    increase_listen_seconds,
    increase_play_count,
    update_music,
    update_music_sort,
    validate_music_params,
)
from utils.auth import get_user_id
from utils.response import res_handle, res_limit
from utils.tools import post_handle


def _get_super_user_id(request):
    user_id = get_user_id(request)
    if not user_id:
        return None, res_handle(401, '请先登录', None)
    if not is_super_user(user_id):
        return None, res_handle(403, '该功能仅超级管理员可用', None)
    return user_id, None


def _get_params(request):
    try:
        return post_handle(request)
    except Exception:
        return {}


@require_POST
def get_music_page_list(request):
    _, error = _get_super_user_id(request)
    if error:
        return error
    params = _get_params(request)
    sql = get_music_list(params)
    return res_limit(params, sql)


@require_POST
def get_music_playlist(request):
    _, error = _get_super_user_id(request)
    if error:
        return error
    return res_handle(0, '查询成功', get_all_music())


@require_POST
def add_music_view(request):
    _, error = _get_super_user_id(request)
    if error:
        return error
    data = clean_music_params(_get_params(request))
    msg = validate_music_params(data)
    if msg:
        return res_handle(501, msg, False)
    create_music(data)
    return res_handle(0, '添加成功', True)


@require_POST
def edit_music_view(request):
    _, error = _get_super_user_id(request)
    if error:
        return error
    params = _get_params(request)
    music_id = params.get('id')
    if not music_id:
        return res_handle(501, '缺少音乐标识', False)
    data = clean_music_params(params)
    msg = validate_music_params(data, music_id)
    if msg:
        return res_handle(501, msg, False)
    try:
        update_music(music_id, data)
    except ValueError as exc:
        return res_handle(501, str(exc), False)
    return res_handle(0, '修改成功', True)


@require_POST
def delete_music_view(request):
    _, error = _get_super_user_id(request)
    if error:
        return error
    try:
        delete_music(_get_params(request).get('ids'))
    except ValueError as exc:
        return res_handle(501, str(exc), False)
    return res_handle(0, '删除成功', True)


@require_POST
def sort_music_view(request):
    _, error = _get_super_user_id(request)
    if error:
        return error
    try:
        update_music_sort(_get_params(request).get('ids'))
    except ValueError as exc:
        return res_handle(501, str(exc), False)
    return res_handle(0, '排序保存成功', True)


@require_POST
def play_music_view(request):
    _, error = _get_super_user_id(request)
    if error:
        return error
    try:
        increase_play_count(_get_params(request).get('id'))
    except ValueError as exc:
        return res_handle(501, str(exc), False)
    return res_handle(0, '记录成功', True)


@require_POST
def music_listen_stat_view(request):
    _, error = _get_super_user_id(request)
    if error:
        return error
    params = _get_params(request)
    try:
        increase_listen_seconds(params.get('id'), params.get('seconds'))
    except ValueError as exc:
        return res_handle(501, str(exc), False)
    return res_handle(0, '记录成功', True)


@require_POST
def extract_music_view(request):
    _, error = _get_super_user_id(request)
    if error:
        return error
    try:
        data = extract_music_embedded_info(_get_params(request).get('id'))
    except ValueError as exc:
        return res_handle(501, str(exc), False)
    msg = '解析完成' if data['updated'] else '未发现可补充的内嵌信息'
    return res_handle(0, msg, data)
