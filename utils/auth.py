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
                # refresh token 不能用于 API 鉴权
                if payload.get('type') == 'refresh':
                    return {'code': 401, 'msg': '请使用 Access Token 访问接口', 'data': None}
                return {'code': 0, 'msg': '验证通过', 'data': payload['userInfo']}
            else:
                return {'code': 401, 'msg': '您未登录，没有权限访问该接口', 'data': None}
        except jwt.ExpiredSignatureError:
            return {'code': 401, 'msg': 'Token过期, 请重新登录', 'data': None}
        except jwt.InvalidTokenError:
            return {'code': 401, 'msg': '您未登录，没有权限访问该接口', 'data': None}


def validate_refresh_token(token):
    """验证 refresh token，返回 userInfo 或错误 dict"""
    try:
        payload = jwt.decode(token, sysConfig.JWT_SECRET_KEY, algorithms=['HS256'])
        if 'userInfo' not in payload:
            return {'code': 401, 'msg': '刷新令牌无效', 'data': None}
        if payload.get('type') != 'refresh':
            return {'code': 401, 'msg': '请使用 Refresh Token 刷新', 'data': None}
        return {'code': 0, 'msg': '验证通过', 'data': payload['userInfo']}
    except jwt.ExpiredSignatureError:
        return {'code': 401, 'msg': '刷新令牌已过期，请重新登录', 'data': None}
    except jwt.InvalidTokenError:
        return {'code': 401, 'msg': '刷新令牌无效', 'data': None}


def get_user_id(request):
    if not ('Authorization' in request.headers):
        return None
    else:
        token = request.headers['Authorization']
        try:
            payload = jwt.decode(token, sysConfig.JWT_SECRET_KEY, algorithms=['HS256'])
            if 'userInfo' in payload and payload.get('type') != 'refresh':
                return payload['userInfo']['id']
            else:
                return None
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
