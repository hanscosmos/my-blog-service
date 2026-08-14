import hashlib
import random
import datetime

from django.contrib.auth.hashers import make_password, check_password
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.views.decorators.http import require_POST

from django.conf import settings


from modules.article.models import Article, ArticleCategory
from modules.article.serializers.article import ArticleSerializers
from modules.authority.models import Role
from modules.user.models import Users, UserProfile, UserAuthority, UserActivityLog, UserTask
from modules.user.serializers.user import UserSerializers
from modules.user.service.user import validate_add_user_params, generate_token, generate_refresh_token, add_user_activity
from utils.auth import get_user_id, validate_refresh_token
from utils.response import res_handle, res_search
from utils.tools import post_handle, obj_has_attr, limit_queryset


def get_user_list(request):
    params = post_handle(request)
    sql = Users.objects.all().filter(nickName__contains=params['keyword'])
    if obj_has_attr(params, 'role'):
        user_ids = list(UserAuthority.objects.all().filter(role=params['role']))
        sql = sql.filter(id__in=user_ids)
    queryset_data = limit_queryset(params, sql)
    data = UserSerializers(instance=queryset_data['result'], many=True)
    return res_search({'result': data.data, 'total': queryset_data['total']})


def add_user_by_admin(request):
    params = post_handle(request)
    username, nickname, email, role_ids = params['username'], params['nickName'], params['email'], params['roleIds']
    msg: str = validate_add_user_params(username, nickname, email)
    if msg != '':
        return res_handle(500, msg)

    is_username_exist: bool = Users.objects.filter(username=username).exists()
    is_email_exist: bool = UserProfile.objects.filter(email=email).exists()
    authority_list: list = []
    if is_username_exist or is_email_exist:
        return res_handle(500, '用户名或者邮箱重复')
    password = make_password(hashlib.md5(settings.INIT_USER_PASSWORD.encode('utf-8')).hexdigest())
    add_user_sql = Users.objects.create(username=username,
                                        nickName=nickname,
                                        password=password)
    for role_id in role_ids:
        user_count = UserAuthority.objects.filter(role=role_id).count()
        role_obj = Role.objects.get(id=role_id)
        if role_obj.limit and user_count >= role_obj.limit:
            return res_handle(500, '%s角色用户数量已达上限' % role_obj.name)
        authority_list.append(UserAuthority(user=add_user_sql.id, role=role_id))
    add_user_profile = UserProfile.objects.create(id=add_user_sql.id, email=email)
    UserAuthority.objects.bulk_create(authority_list)
    add_user_sql.save()
    add_user_profile.save()
    return res_handle(0, '新增用户成功', True)


def set_user_role(request):
    params = post_handle(request)
    user_id, role_ids = params['userId'], params['roleIds']
    authority_list: list = []
    UserAuthority.objects.filter(user=user_id).delete()
    for role_id in role_ids:
        user_count = UserAuthority.objects.filter(role=role_id).count()
        role_obj = Role.objects.get(id=role_id)
        if role_obj.limit and user_count >= role_obj.limit:
            return res_handle(500, '%s角色用户数量已达上限' % role_obj.name)
        authority_list.append(UserAuthority(user=user_id, role=role_id))
    UserAuthority.objects.bulk_create(authority_list)
    return res_handle(0, '角色分配成功', True)


@csrf_exempt
def user_login_admin_system(request):
    params = post_handle(request)
    username, password, key, code = params['username'], params['password'], params['key'], params['code']
    user_exist: bool = Users.objects.filter(username=username).exists()
    is_code_match: bool = (cache.get(key) == code)
    if not is_code_match:
        return res_handle(500, '验证码错误或过期')
    if not user_exist:
        return res_handle(500, '用户不存在')
    user_obj = Users.objects.get(username=username)
    if not check_password(password, user_obj.password):
        return res_handle(500, '用户名或密码错误')
    user = Users.objects.get(id=user_obj.id)
    if user.isForbidden:
        return res_handle(500, '该用户已被禁用！')
    user_profile = UserProfile.objects.get(id=user.id)
    user_profile.loginTime = datetime.datetime.now()
    csrf_token = get_token(request)
    token_data = {
        'id': user.id,
        'nickName': user.nickName,
        'avatar': user.avatar,
        'bgCover': user_profile.bgCover,
        'sex': user_profile.sex,
        'createTime': user.createTime,
        'loginTime': user_profile.loginTime,
    }
    result = generate_token({'id': user.id})
    refresh_token = generate_refresh_token({'id': user.id})
    user_data = {
        'userInfo': token_data,
        'token': result,
        'refreshToken': refresh_token,
        'csrfToken': csrf_token,
    }
    return res_handle(0, '登录成功', user_data)


def get_self_info(request):
    user_id = get_user_id(request)
    user = Users.objects.get(id=user_id)
    user_profile = UserProfile.objects.get(id=user_id)
    user_info = {
        'id': str(user.id),
        'nickName': user.nickName,
        'avatar': user.avatar,
        'bgCover': user_profile.bgCover,
        'sex': user_profile.sex,
        'createTime': user.createTime,
        'talks': user_profile.talks,
        'email': user_profile.email,
        'level': user_profile.levelScore,
    }
    return res_handle(0, '查询成功', user_info)


def update_self_info(request):
    params = post_handle(request)
    user_id = get_user_id(request)
    user = Users.objects.get(id=user_id)
    user_profile = UserProfile.objects.get(id=user_id)
    user.nickName = params['nickName']
    user.avatar = params['avatar']
    user_profile.bgCover = params['bgCover']
    user_profile.sex = params['sex']
    user_profile.talks = params['talks']
    user_profile.email = params['email']
    user.save()
    user_profile.save()
    return res_handle(0, '获取成功', True)


@csrf_exempt
def get_valid_code(request):
    params = post_handle(request)
    key = params['key']
    valid_code = str(random.randint(100000, 999999))
    cache.set(key, valid_code, 120)
    return res_handle(0, '获取成功', valid_code)


@csrf_exempt
def user_refresh_token(request):
    """用 refresh token 换取新的 access token"""
    params = post_handle(request)
    refresh_token = params.get('refreshToken', '')
    if not refresh_token:
        return res_handle(401, '刷新令牌不能为空')
    v_result = validate_refresh_token(refresh_token)
    if v_result.get('code') != 0:
        return res_handle(v_result['code'], v_result['msg'])
    user_id = v_result['data']['id']
    new_access_token = generate_token({'id': user_id})
    return res_handle(0, '刷新成功', {'token': new_access_token})


ARTICLE_ACTIVITY_TYPES = ('publish_article', 'create_draft', 'update_article', 'delete_article')


def get_self_activity_log(request):
    params = post_handle(request)
    user_id = get_user_id(request)
    sql = UserActivityLog.objects.filter(user=user_id).order_by('-createTime')
    queryset_data = limit_queryset(params, sql)
    result = []
    for log in queryset_data['result']:
        result.append({
            'id': str(log.id),
            'targetId': str(log.targetId) if log.targetId else None,
            'targetType': log.targetType,
            'action': log.action,
            'createTime': log.createTime,
            'extraData': log.extraData or {},
            'article': _resolve_activity_article(log),
        })
    return res_search({'result': result, 'total': queryset_data['total']})


def _resolve_activity_article(log):
    """解析文章类动态关联的文章详情；文章已被删除则返回 None"""
    if log.targetType not in ARTICLE_ACTIVITY_TYPES or not log.targetId:
        return None
    article_obj = Article.objects.filter(id=log.targetId, isDelete=False).first()
    if not article_obj:
        return None
    category_name = None
    if article_obj.category:
        category_name = ArticleCategory.objects.filter(id=article_obj.category).values_list('name', flat=True).first()
    return {
        'id': str(article_obj.id),
        'title': article_obj.title,
        'cover': article_obj.cover,
        'abstract': article_obj.abstract,
        'status': article_obj.status,
        'category': category_name,
        'createTime': article_obj.createTime,
        'updateTime': article_obj.updateTime,
    }


def get_user_stats(request):
    """获取当前用户的统计数据（文章数、动态数、事项数）"""
    user_id = get_user_id(request)
    article_count = Article.objects.filter(author=user_id, isDelete=False).count()
    activity_count = UserActivityLog.objects.filter(user=user_id).count()
    task_count = UserTask.objects.filter(user=user_id).count()
    stats = {
        'articleCount': article_count,
        'activityCount': activity_count,
        'taskCount': task_count,
    }
    return res_handle(0, '查询成功', stats)


@require_POST
def get_user_article_list(request):
    params = post_handle(request)
    user_id = get_user_id(request)
    sql = Article.objects.all().filter(author=user_id)
    if obj_has_attr(params, 'title'):
        sql = sql.filter(title__contains=params['title'])
    if obj_has_attr(params, 'status'):
        sql = sql.filter(status=params['status'])
    if obj_has_attr(params, 'category') and params['category'] not in (0, '0', ''):
        cate_ids = [params['category']]
        child_ids = list(ArticleCategory.objects.filter(father=params['category']).values_list('id', flat=True))
        cate_ids.extend(child_ids)
        sql = sql.filter(category__in=cate_ids)
    if obj_has_attr(params, 'startTime') and obj_has_attr(params, 'endTime'):
        sql = sql.filter(createTime__range=(params['startTime'], params['endTime']))
    # 按发布时间排序，默认倒序
    sort_order = params.get('sortOrder') or 'descending'
    order_prefix = '-' if sort_order == 'descending' else ''
    sql = sql.order_by(f'{order_prefix}createTime')
    queryset_data = limit_queryset(params, sql)
    data = ArticleSerializers(instance=queryset_data['result'], many=True)
    return res_search({'result': data.data, 'total': queryset_data['total']})


@require_POST
def delete_user_activity(request):
    params = post_handle(request)
    user_id = get_user_id(request)
    UserActivityLog.objects.filter(user=user_id, targetType=params['targetType']).delete()
    return res_handle(0, '删除成功')
