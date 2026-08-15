import json
import logging

import requests
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from config.config import sysConfig
from modules.ai.models import AiConversation, AiMessage
from modules.ai.tools import run_tool_loop
from utils.auth import get_user_id
from utils.tools import post_handle

logger = logging.getLogger(__name__)


@csrf_exempt
def ai_chat(request):
    """
    AI 聊天接口 —— SSE 流式代理

    转发前端消息到 OpenAI 兼容 API，流式返回 SSE 响应。
    同时将用户消息和助手回复存入数据库，并记录 token 用量。

    请求格式：
        {
            "messages": [{"role": "user", "content": "..."}],
            "conversationId": "<uuid>",   // 可选，对话 ID
            "stream": true
        }
    """
    try:
        params = post_handle(request)
    except Exception:
        return _error_response('请求体解析失败')

    messages = params.get('messages', [])
    if not messages:
        return _error_response('消息列表不能为空')

    model = params.get('model', sysConfig.AI_MODEL)
    conversation_id = params.get('conversationId', '')

    # 检查 API 配置
    if not sysConfig.AI_API_KEY:
        logger.error('AI_API_KEY 未配置')
        return _error_response('AI 服务未配置，请在 .env 中设置 AI_API_KEY')

    # 保存用户消息到数据库（如果传了 conversationId）
    user_id = get_user_id(request)
    if user_id and conversation_id:
        _ensure_conversation_exists(conversation_id, user_id, model)
        # 取最后一条 user 消息入库
        user_messages = [m for m in messages if m.get('role') == 'user']
        if user_messages:
            last_user_msg = user_messages[-1]
            AiMessage.objects.create(
                conversation=conversation_id,
                role='user',
                content=last_user_msg.get('content', ''),
            )
            # 更新对话的 updateTime 和标题
            conv = AiConversation.objects.filter(id=conversation_id).first()
            if conv:
                # 首条用户消息自动设为标题
                msg_count = AiMessage.objects.filter(conversation=conversation_id, role='user').count()
                if msg_count == 1 or conv.title == '新对话':
                    title = last_user_msg.get('content', '')
                    conv.title = title[:30] + ('...' if len(title) > 30 else '')
                conv.save(update_fields=['title', 'updateTime'])

    # 用于在流式过程中收集数据
    collected_content = []      # 收集助手回复内容
    collected_usage = None      # 收集 token 用量

    def event_stream():
        """
        SSE 事件流生成器
        先通过工具调用循环获取最终回复，再以 SSE 形式返回给前端
        """
        nonlocal collected_usage

        try:
            final_content, usage = run_tool_loop(messages, model, user_id)
            if usage:
                collected_usage = {
                    'prompt_tokens': usage.get('prompt_tokens'),
                    'completion_tokens': usage.get('completion_tokens'),
                }
            if final_content:
                collected_content.append(final_content)
            yield f'data: {json.dumps({"content": final_content}, ensure_ascii=False)}\n\n'
            yield 'data: [DONE]\n\n'
        except requests.exceptions.Timeout:
            logger.error('上游 API 请求超时')
            yield f'data: {json.dumps({"error": "AI 服务响应超时，请稍后重试"})}\n\n'
            yield 'data: [DONE]\n\n'
        except requests.exceptions.ConnectionError:
            logger.error('上游 API 连接失败')
            yield f'data: {json.dumps({"error": "无法连接到 AI 服务，请检查网络和 API 配置"})}\n\n'
            yield 'data: [DONE]\n\n'
        except Exception as e:
            logger.error(f'AI 服务异常: {str(e)}')
            yield f'data: {json.dumps({"error": f"AI 服务异常: {str(e)}"})}\n\n'
            yield 'data: [DONE]\n\n'

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    response['Access-Control-Allow-Origin'] = '*'

    # 无法直接在 StreamingHttpResponse 完成后做 DB 操作
    # 改为通过重写 close 方法实现：流结束后保存助手消息
    original_close = response.close

    def close_with_save():
        # 保存助手回复消息到数据库
        if user_id and conversation_id and collected_content:
            full_content = ''.join(collected_content)
            AiMessage.objects.create(
                conversation=conversation_id,
                role='assistant',
                content=full_content,
                promptTokens=collected_usage.get('prompt_tokens') if collected_usage else None,
                completionTokens=collected_usage.get('completion_tokens') if collected_usage else None,
            )
            # 更新对话 updateTime
            conv = AiConversation.objects.filter(id=conversation_id).first()
            if conv:
                conv.save(update_fields=['updateTime'])
        original_close()

    response.close = close_with_save

    return response


def _ensure_conversation_exists(conversation_id, user_id, model):
    """确保对话存在，不存在则创建"""
    if not AiConversation.objects.filter(id=conversation_id).exists():
        AiConversation.objects.create(
            id=conversation_id,
            user=user_id,
            title='新对话',
            model=model,
        )


def _error_response(msg: str):
    """返回普通 JSON 错误响应（非流式）"""
    from django.http import JsonResponse
    from utils.tools import json_handle
    return JsonResponse(json_handle({'code': 500, 'msg': msg, 'data': None}))
