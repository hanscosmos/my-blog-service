from django.http import JsonResponse
from utils.tools import json_handle, limit_queryset


def res_handle(code, msg, data=None):
    if data is None:
        data = None
    res_list = {'code': code, 'msg': msg, 'data': data}
    return JsonResponse(json_handle(res_list))


# 用来做表单校验的函数
def res_valid(data, sql):
    if sql.exists():
        return res_handle(500, '关键参数重复')
    if data.is_valid():
        data.save()
        return res_handle(0, '操作成功')
    else:
        return res_handle(501, '后台校验未通过，详情查看控制台', data.errors)


def res_search(data):
    return res_handle(0, '查询成功', data)


def res_limit(params, sql):
    query_data = limit_queryset(params, sql)
    if not query_data['result']:
        return res_search({'result': [], 'total': query_data['total']})
    else:
        return res_search({'result': list(query_data['result']), 'total': query_data['total']})


# 用来做删除处理的函数
def res_delete(sql):
    sql.delete()
    return res_handle(0, '删除成功')
