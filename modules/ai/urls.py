from django.urls import path
from .views.chat import ai_chat
from .views.conversation import (
    list_conversations,
    get_conversation,
    create_conversation,
    delete_conversation,
    update_conversation,
)

urlpatterns = [
    # 聊天（SSE 流式）
    path('chat', ai_chat, name='ai_chat'),

    # 对话 CRUD
    path('conversations', list_conversations, name='ai_list_conversations'),
    path('conversations/create', create_conversation, name='ai_create_conversation'),
    path('conversations/<str:conversation_id>', get_conversation, name='ai_get_conversation'),
    path('conversations/<str:conversation_id>/delete', delete_conversation, name='ai_delete_conversation'),
    path('conversations/<str:conversation_id>/update', update_conversation, name='ai_update_conversation'),
]
