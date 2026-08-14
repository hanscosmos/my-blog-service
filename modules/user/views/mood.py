from django.views.decorators.http import require_POST

from modules.user.models import UserMood
from modules.user.service.user import add_user_activity
from utils.auth import get_user_id
from utils.response import res_handle, res_search
from utils.tools import post_handle, limit_queryset


@require_POST
def get_user_mood_list(request):
    params = post_handle(request)
    user_id = get_user_id(request)
    sql = UserMood.objects.filter(user=user_id).order_by('-createTime')
    queryset_data = limit_queryset(params, sql)
    result = [
        {
            'id': str(mood.id),
            'content': mood.content,
            'mood': mood.mood,
            'images': mood.images or [],
            'createTime': mood.createTime,
        }
        for mood in queryset_data['result']
    ]
    return res_search({'result': result, 'total': queryset_data['total']})


@require_POST
def add_user_mood(request):
    params = post_handle(request)
    user_id = get_user_id(request)
    content = (params.get('content') or '').strip()
    mood = params.get('mood') or None
    images = params.get('images') or []
    if not content and not images:
        return res_handle(500, '文字和图片至少填写一个', False)
    mood_obj = UserMood.objects.create(user=user_id, content=content, mood=mood, images=images)
    add_user_activity(request, 'create_mood', mood_obj.id, '发布心情', {'content': content, 'mood': mood})
    return res_handle(0, '发布成功', True)


@require_POST
def delete_user_mood(request):
    params = post_handle(request)
    user_id = get_user_id(request)
    UserMood.objects.filter(user=user_id, id__in=params['ids']).delete()
    return res_handle(0, '删除成功', True)
