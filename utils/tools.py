import json
import re
from datetime import date, datetime
from uuid import UUID
from django.core.paginator import Paginator
from django.forms.models import model_to_dict


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, UUID):
            return str(obj)
        elif model_to_dict(obj):
            return model_to_dict(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def json_handle(data):
    return json.loads(json.dumps(data, cls=ComplexEncoder))


# 用来将列表转化成树结构的函数
def list_to_tree(arr, parent_id, own_id):
    arr = json_handle(arr)
    obj = {}
    for item in arr:
        obj[item[own_id]] = item
    parent_list = []
    for subItem in arr:
        if subItem[parent_id]:
            parent = obj[subItem[parent_id]]
            if parent:
                if 'children' not in parent:
                    parent['children'] = []
                parent['children'].append(subItem)
        else:
            parent_list.append(subItem)
    return parent_list


def int_handle(data):
    return data if isinstance(data, int) else int(data)


def limit_queryset(params, sql):
    page_number = int_handle(params['pageNumber'])
    page_size = int_handle(params['pageSize'])
    total_count = sql.count()
    if (page_number - total_count / page_size < 1) or page_number == 1:
        page_result = Paginator(sql, page_size)
        result = page_result.page(page_number)
        return {'result': result, 'total': total_count}
    else:
        return {'result': [], 'total': 0}


def post_handle(request):
    if len(request.POST.keys()) > 0:
        return request.POST
    else:
        return json.loads(request.body)


def turn_param_style(params: dict):
    """
    将参数名的驼峰形式转为下划线形式
    @param params:
    @return:
    """
    temp_dict = {}
    for name, value in params.items():
        temp_name = ""
        if re.search("[A-Z]", name):
            capital_letters = re.findall("[A-Z]", name)
            for c in capital_letters:
                lower_c = c.lower()
                r_str = "_" + lower_c
                temp_name = name.replace(c, r_str)
        else:
            temp_name = name

        temp_dict.update({temp_name: value})

    return temp_dict


# 格式化请求的参数，统一转化为符合python标准的下划线命名方式
def params_handle(request):
    if request.method == "GET":
        return turn_param_style(request.GET)
    elif request.method == "POST":
        return turn_param_style(post_handle(request))
    else:
        pass


# 判断一个对象中是否有某个属性并且这个属性为true
def obj_has_attr(obj, attr):
    if not (attr in obj):
        return False
    return bool(obj[attr])

