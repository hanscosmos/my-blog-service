import os
import datetime
from django.views.decorators.http import require_POST
from modules.blogger.models import BloggerProfile
from utils.auth import get_user_id
from utils.response import res_handle
from utils.tools import post_handle


@require_POST
def get_blogger_profile(request):
    user_id = get_user_id(request)
    profile = BloggerProfile.objects.filter(userId=user_id).first()
    if not profile:
        profile = BloggerProfile.objects.create(userId=user_id)
    data = {
        'id': profile.id,
        'userId': profile.userId,
        'introduction': profile.introduction or '',
        'phone': profile.phone or '',
        'wechat': profile.wechat or '',
        'qq': profile.qq or '',
        'github': profile.github or '',
        'weibo': profile.weibo or '',
        'site': profile.site or '',
        'resumeFileUrl': profile.resumeFileUrl or '',
        'resumeFileName': profile.resumeFileName or '',
        'assets': profile.assets or {'items': []},
        'createdAt': profile.createdAt,
        'updatedAt': profile.updatedAt,
    }
    return res_handle(0, '查询成功', data)


@require_POST
def update_blogger_profile(request):
    user_id = get_user_id(request)
    params = post_handle(request)
    profile = BloggerProfile.objects.filter(userId=user_id).first()
    if not profile:
        profile = BloggerProfile.objects.create(userId=user_id)

    allowed_fields = [
        'introduction', 'phone', 'wechat', 'qq',
        'github', 'weibo', 'site',
        'resumeFileUrl', 'resumeFileName', 'assets',
    ]
    for field in allowed_fields:
        if field in params:
            setattr(profile, field, params[field])

    profile.updatedAt = datetime.datetime.now()
    profile.save()
    return res_handle(0, '保存成功', True)

