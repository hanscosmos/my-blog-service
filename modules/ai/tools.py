import json
import logging

import requests
from django.db.models import Q

from config.config import sysConfig
from modules.article.models import Article, ArticleDetail, ArticleTag, ArticleTagRelation

logger = logging.getLogger(__name__)

# 工具调用循环最多轮数，防止死循环
MAX_TOOL_ROUNDS = 5
# 单篇文章返回给模型的最大字符数，避免撑爆上下文
MAX_ARTICLE_CONTENT_LENGTH = 12000
# 单次搜索最多返回条数
MAX_SEARCH_RESULTS = 20

# 注入给模型的系统提示词，告知其具备读取文章的能力
TOOL_SYSTEM_PROMPT = (
    '你可以调用工具读取当前用户的博客文章。'
    '当用户提到某篇文章、让你分析文章、写摘要或提建议时，'
    '先用 search_articles 找到目标文章，再用 get_article_content 读取正文。'
    '如果找不到对应文章，如实告诉用户，不要编造内容。'
)

# 提供给上游 API 的工具定义（OpenAI Function Calling 格式）
TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'search_articles',
            'description': (
                '按关键词搜索当前用户（博客作者）的文章，返回匹配的文章列表。'
                '返回每篇文章的 id、标题、摘要、状态、标签和创建时间。'
                '当用户想找某篇/某些文章，或不确定文章 id 时，先调用本工具。'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'keyword': {'type': 'string', 'description': '搜索关键词，匹配标题或摘要'},
                    'limit': {'type': 'integer', 'description': '最多返回条数，默认 5，最大 20'},
                },
                'required': ['keyword'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_article_content',
            'description': (
                '根据文章 id 获取文章完整内容（Markdown 原文）。'
                '当需要分析文章正文、撰写摘要、提出修改建议时，调用本工具。'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'article_id': {'type': 'string', 'description': '文章 id（UUID）'},
                },
                'required': ['article_id'],
            },
        },
    },
]


def _serialize_article(article):
    """序列化文章列表项，返回模型易于理解的精简结构"""
    tag_ids = ArticleTagRelation.objects.filter(article=article.id).values_list('tag', flat=True)
    tags = list(ArticleTag.objects.filter(id__in=tag_ids).values_list('name', flat=True))
    return {
        'id': str(article.id),
        'title': article.title,
        'abstract': article.abstract or '',
        'status': article.status,
        'tags': tags,
        'createTime': article.createTime.strftime('%Y-%m-%d %H:%M:%S') if article.createTime else '',
    }


def search_articles(user_id, keyword='', limit=5):
    """按关键词搜索当前用户的文章"""
    keyword = (keyword or '').strip()
    try:
        limit = max(1, min(int(limit or 5), MAX_SEARCH_RESULTS))
    except (TypeError, ValueError):
        limit = 5

    qs = (
        Article.objects
        .filter(author=user_id, isDelete=False)
        .filter(Q(title__icontains=keyword) | Q(abstract__icontains=keyword))
        .order_by('-updateTime')
    )
    total = qs.count()
    articles = list(qs[:limit])
    return {
        'total': total,
        'returned': len(articles),
        'articles': [_serialize_article(a) for a in articles],
    }


def get_article_content(user_id, article_id):
    """根据文章 id 获取完整正文"""
    try:
        article = Article.objects.get(id=article_id, author=user_id, isDelete=False)
    except Article.DoesNotExist:
        return {'error': f'未找到文章（id: {article_id}），请确认文章 id 是否正确'}

    try:
        detail = ArticleDetail.objects.get(article=article.id)
    except ArticleDetail.DoesNotExist:
        return {'error': f'文章《{article.title}》没有正文内容'}

    content = detail.content or ''
    truncated = len(content) > MAX_ARTICLE_CONTENT_LENGTH
    if truncated:
        content = content[:MAX_ARTICLE_CONTENT_LENGTH]

    return {
        'id': str(article.id),
        'title': article.title,
        'status': article.status,
        'abstract': article.abstract or '',
        'content': content,
        'truncated': truncated,
    }


def execute_tool(name, args, user_id):
    """工具执行器，统一异常处理"""
    try:
        if name == 'search_articles':
            return search_articles(user_id, args.get('keyword', ''), args.get('limit', 5))
        if name == 'get_article_content':
            return get_article_content(user_id, args.get('article_id', ''))
        return {'error': f'未知工具: {name}'}
    except Exception as e:
        logger.error(f'工具执行失败 {name}: {str(e)}')
        return {'error': f'工具执行失败: {str(e)}'}


def run_tool_loop(messages, model, user_id):
    """
    非流式工具调用循环。

    将消息连同工具定义发给上游 API，若模型返回 tool_calls 则执行对应工具、
    把结果作为 role=tool 消息回填，循环直到模型给出最终答复。

    Returns:
        (final_content, usage)  usage 为累计 token 用量 dict
    """
    current = [{'role': 'system', 'content': TOOL_SYSTEM_PROMPT}] + list(messages)

    total_prompt = 0
    total_completion = 0

    for _ in range(MAX_TOOL_ROUNDS):
        resp = requests.post(
            f'{sysConfig.AI_API_BASE_URL}/chat/completions',
            headers={
                'Authorization': f'Bearer {sysConfig.AI_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'messages': current,
                'tools': TOOLS,
            },
            timeout=120,
        )

        if resp.status_code != 200:
            error_msg = f'上游 API 返回错误 ({resp.status_code})'
            try:
                error_body = resp.json()
                if 'error' in error_body:
                    error_msg = error_body['error'].get('message', error_msg)
            except Exception:
                error_body = resp.text[:200]
                if error_body:
                    error_msg = f'{error_msg}: {error_body}'
            raise RuntimeError(error_msg)

        data = resp.json()
        usage = data.get('usage')
        if usage:
            total_prompt += usage.get('prompt_tokens') or 0
            total_completion += usage.get('completion_tokens') or 0

        choice = data.get('choices', [{}])[0]
        message = choice.get('message', {})
        tool_calls = message.get('tool_calls')

        # 没有工具调用，说明是最终答复
        if not tool_calls:
            return message.get('content', ''), {
                'prompt_tokens': total_prompt,
                'completion_tokens': total_completion,
            }

        # 组装 assistant 消息（含 tool_calls）回填上下文
        assistant_msg = {
            'role': 'assistant',
            'tool_calls': [
                {
                    'id': tc.get('id'),
                    'type': 'function',
                    'function': {
                        'name': tc.get('function', {}).get('name'),
                        'arguments': tc.get('function', {}).get('arguments', ''),
                    },
                }
                for tc in tool_calls
            ],
        }
        if message.get('content'):
            assistant_msg['content'] = message['content']
        current.append(assistant_msg)

        # 逐个执行工具，回填 tool 消息
        for tc in tool_calls:
            fn = tc.get('function', {})
            fn_name = fn.get('name')
            try:
                fn_args = json.loads(fn.get('arguments') or '{}')
            except json.JSONDecodeError:
                fn_args = {}
            result = execute_tool(fn_name, fn_args, user_id)
            current.append({
                'role': 'tool',
                'tool_call_id': tc.get('id'),
                'content': json.dumps(result, ensure_ascii=False),
            })

    # 超过最大轮数仍未收敛
    return '', {
        'prompt_tokens': total_prompt,
        'completion_tokens': total_completion,
    }
