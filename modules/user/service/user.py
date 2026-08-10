import datetime
import re
import jwt

from config.config import sysConfig
from modules.user.models import UserActivityLog
from utils.auth import get_user_id
from utils.tools import json_handle


def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True
    else:
        return False


def validate_add_user_params(username, nickname, email):
    msg: str = ''
    if not username:
        msg = '用户名不得为空'
    if not nickname:
        msg = '昵称不得为空'
    if not email:
        msg = '邮箱不得为空'
    if len(username) < 8 or len(username) > 20:
        msg = '用户名长度为8-20'
    if len(nickname) > 32:
        msg = '昵称长度为1-32'
    if not validate_email(email):
        msg = '请输入正确的邮箱格式'
    return msg


def generate_token(data):
    headers = {
        'typ': 'jwt',
        'alg': 'HS256'
    }
    token_time = sysConfig.ACCESS_TOKEN_WORK_TIME
    secret_key = sysConfig.JWT_SECRET_KEY
    exp = datetime.datetime.now() + datetime.timedelta(hours=token_time)
    payload = {
        'userInfo': json_handle(data),
        'type': 'access',
        'exp': exp
    }
    result = jwt.encode(payload=payload, key=secret_key, algorithm='HS256', headers=headers)
    return result


def generate_refresh_token(data):
    headers = {
        'typ': 'jwt',
        'alg': 'HS256'
    }
    token_time = sysConfig.TOKEN_WORK_TIME
    secret_key = sysConfig.JWT_SECRET_KEY
    exp = datetime.datetime.now() + datetime.timedelta(hours=token_time)
    payload = {
        'userInfo': json_handle(data),
        'type': 'refresh',
        'exp': exp
    }
    result = jwt.encode(payload=payload, key=secret_key, algorithm='HS256', headers=headers)
    return result


def add_user_activity(request, target_type, target_id, action, extra_data):
    user_id = request if target_type == 'login' else get_user_id(request)
    UserActivityLog.objects.create(user=user_id, targetType=target_type, targetId=target_id, action=action,
                                   extraData=extra_data)
