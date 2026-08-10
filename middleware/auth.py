from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from config.choices import WHITE_PATH_LIST
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
        # if not Api.objects.filter(path__exact=url_path).exists():
        #     return JsonResponse({'code': 500, 'msg': '接口不存在'})
        # api = Api.objects.get(path__exact=url_path)
        # if not api.isAuth:
        #     return
        v_result = validate_token(request)
        if v_result.get('code') != 0:
            return JsonResponse(json_handle(v_result))
        # 这里根据用户角色id查询相关表判断用户是否具有该接口的权限
        user_id = v_result['data']['id']
        user = Users.objects.get(id__exact=user_id)
        if user.isForbidden:
            return JsonResponse({'code': 401, 'msg': '当前用户已被禁用'})
        return
        # role = Role.objects.get(id__exact=user.role.id)
        # if user.role.sign == 'master':
        #     return
        # is_auth = ApiAuthority.objects.filter(role__id=role.id, api__id=api.id).exists()
        # if not is_auth:
        #     return JsonResponse({'code': 403, 'msg': '您的权限不足，无法访问此接口'})
        # else:
        #     return
