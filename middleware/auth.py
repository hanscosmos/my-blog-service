from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from config.choices import WHITE_PATH_LIST
from config.permission import PERMISSION_PATH_MAP
from modules.authority.service.permission import has_permission
from modules.user.models import Users
from utils.auth import validate_token
from utils.tools import json_handle


# 用来验证用户是否有权限的中间件
class AuthMiddleWare(MiddlewareMixin):
    @staticmethod
    def process_request(request):
        url_path = request.path
        if url_path in WHITE_PATH_LIST:
            return
        if url_path.startswith('/client/'):
            return
        v_result = validate_token(request)
        if v_result.get('code') != 0:
            return JsonResponse(json_handle(v_result))
        user_id = v_result['data']['id']
        user = Users.objects.get(id__exact=user_id)
        if user.isForbidden:
            return JsonResponse({'code': 401, 'msg': '当前用户已被禁用'})
        # 写操作按权限码校验，未登记的路径默认放行（读接口由菜单可见性控制入口）
        perm_code = PERMISSION_PATH_MAP.get(url_path)
        if perm_code and not has_permission(user_id, perm_code):
            return JsonResponse({'code': 403, 'msg': '您的权限不足，无法执行该操作'})
        return
