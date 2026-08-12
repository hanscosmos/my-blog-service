from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from modules.ai.models import AiConversation, AiMessage
from utils.auth import get_user_id
from utils.response import res_handle
from utils.tools import post_handle


@csrf_exempt
def list_conversations(request):
    """获取当前用户的对话列表（仅返回摘要信息，不含消息内容）"""
    user_id = get_user_id(request)
    if not user_id:
        return res_handle(401, '请先登录')

    conversations = (
        AiConversation.objects
        .filter(user=user_id)
        .values('id', 'title', 'model', 'createTime', 'updateTime')
        .order_by('-updateTime')
    )
    return res_handle(0, '查询成功', list(conversations))


@csrf_exempt
def get_conversation(request, conversation_id):
    """获取某个对话的完整消息列表"""
    user_id = get_user_id(request)
    if not user_id:
        return res_handle(401, '请先登录')

    # 先验证对话是否属于当前用户
    conv = AiConversation.objects.filter(id=conversation_id, user=user_id).first()
    if not conv:
        return res_handle(404, '对话不存在')

    messages = (
        AiMessage.objects
        .filter(conversation=conversation_id)
        .values('id', 'role', 'content', 'promptTokens', 'completionTokens', 'createTime')
        .order_by('createTime')
    )
    return res_handle(0, '查询成功', {
        'conversation': {
            'id': conv.id,
            'title': conv.title,
            'model': conv.model,
            'createTime': conv.createTime,
            'updateTime': conv.updateTime,
        },
        'messages': list(messages),
    })


@csrf_exempt
@require_POST
def create_conversation(request):
    """新建对话，返回对话 ID"""
    user_id = get_user_id(request)
    if not user_id:
        return res_handle(401, '请先登录')

    params = post_handle(request)
    title = params.get('title', '新对话')
    model = params.get('model', 'deepseek-v4-pro')

    conv = AiConversation.objects.create(
        user=user_id,
        title=title,
        model=model,
    )
    return res_handle(0, '创建成功', {'id': conv.id})


@csrf_exempt
@require_POST
def delete_conversation(request, conversation_id):
    """删除对话以及其所有消息"""
    user_id = get_user_id(request)
    if not user_id:
        return res_handle(401, '请先登录')

    conv = AiConversation.objects.filter(id=conversation_id, user=user_id).first()
    if not conv:
        return res_handle(404, '对话不存在')

    # 级联删除所有关联消息
    AiMessage.objects.filter(conversation=conversation_id).delete()
    conv.delete()

    return res_handle(0, '删除成功')


@csrf_exempt
@require_POST
def update_conversation(request, conversation_id):
    """更新对话标题"""
    user_id = get_user_id(request)
    if not user_id:
        return res_handle(401, '请先登录')

    params = post_handle(request)
    title = params.get('title', '').strip()
    if not title:
        return res_handle(400, '标题不能为空')

    conv = AiConversation.objects.filter(id=conversation_id, user=user_id).first()
    if not conv:
        return res_handle(404, '对话不存在')

    conv.title = title[:64]
    conv.save(update_fields=['title', 'updateTime'])

    return res_handle(0, '更新成功')
