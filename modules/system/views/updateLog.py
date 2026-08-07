from datetime import datetime
from django.views.decorators.http import require_POST
from modules.system.models import UpdateLog
from modules.system.service.updateLog import validate_add_log_params
from utils.auth import get_user_id
from utils.response import res_handle, res_limit
from utils.tools import post_handle


@require_POST
def add_update_log(request):
    params = post_handle(request)
    msg = validate_add_log_params(params)
    params['releasedBy'] = get_user_id(request)
    if msg:
        return res_handle(501, False, msg)
    UpdateLog.objects.create(**params)
    return res_handle(0, '添加成功', True)


@require_POST
def edit_update_log(request):
    params = post_handle(request)
    msg = validate_add_log_params(params)
    params['updateTime'] = datetime.now()
    params['releasedBy'] = get_user_id(request)
    if msg:
        return res_handle(501, msg, False)
    UpdateLog.objects.filter(id=params['id']).update(**params)

    return res_handle(0, '修改成功', True)


@require_POST
def delete_update_log(request):
    params = post_handle(request)
    sql = UpdateLog.objects.filter(id__in=params['ids'])
    sql.delete()
    return res_handle(0, '删除成功', True)


@require_POST
def get_update_log_list(request):
    params = post_handle(request)
    sql = UpdateLog.objects.all().filter(summary__contains=params['keyword']).values(*['createTime', 'updateTime', 'id',
                                                                                       'isCurrentVersion', 'summary',
                                                                                       'version', 'details',
                                                                                       'plannedReleaseDate',
                                                                                       'actualReleaseDate',
                                                                                       'releasedBy', 'releasedType',
                                                                                       'status'])
    return res_limit(params, sql)
