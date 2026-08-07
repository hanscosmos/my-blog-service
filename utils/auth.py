import jwt
from config.config import sysConfig


def validate_token(request):
    if not ('Authorization' in request.headers):
        return {'code': 401, 'msg': '您没有权限访问该接口', 'data': None}
    else:
        token = request.headers['Authorization']
        try:
            payload = jwt.decode(token, sysConfig.JWT_SECRET_KEY, algorithms=['HS256'])
            if 'userInfo' in payload:
                return {'code': 0, 'msg': '验证通过', 'data': payload['userInfo']}
            else:
                return {'code': 401, 'msg': '您未登录，没有权限访问该接口', 'data': None}
        except jwt.ExpiredSignatureError:
            return {'code': 401, 'msg': 'Token过期, 请重新登录', 'data': None}
        except jwt.InvalidTokenError:
            return {'code': 401, 'msg': '您未登录，没有权限访问该接口', 'data': None}


def get_user_id(request):
    if not ('Authorization' in request.headers):
        return None
    else:
        token = request.headers['Authorization']
        try:
            payload = jwt.decode(token, sysConfig.JWT_SECRET_KEY, algorithms=['HS256'])
            if 'userInfo' in payload:
                return payload['userInfo']['id']
            else:
                return None
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
