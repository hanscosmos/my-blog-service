from datetime import datetime
from django.db.models import Q, F
from django.views.decorators.http import require_POST
from modules.article.models import Article, ArticleDetail, ArticleTagRelation, ArticleCategory, ArticleTag, ArticleReadLog
from modules.article.serializers.article import ArticleSerializers
from modules.article.service.article import validate_add_article_params
from modules.user.models import Users
from modules.user.service.user import add_user_activity
from utils.api_service import get_count_stats
from utils.auth import get_user_id
from utils.response import res_handle, res_search
from utils.tools import post_handle, limit_queryset, obj_has_attr


@require_POST
def get_article_list(request):
    params = post_handle(request)
    sql = Article.objects.all().filter(title__contains=params['title'], status='publish', visible='public')
    if obj_has_attr(params, 'category') and params['category'] != 0 and params['category'] != '':
        search_list = []
        cate_list = list(ArticleCategory.objects.filter(Q(father=params['category']) | Q(id=params['category']))
                         .values(*['id']))
        for cate in cate_list:
            search_list.append(cate['id'])
        sql = sql.filter(category__in=search_list)
    queryset_data = limit_queryset(params, sql)
    data = ArticleSerializers(instance=queryset_data['result'], many=True)
    return res_search({'result': data.data, 'total': queryset_data['total']})


@require_POST
def get_article_detail(request):
    cata_obj = None
    cata_father_obj = None
    params = post_handle(request)
    sql = Article.objects.all().get(id=params['id'])
    if sql.category:
        cata_obj = ArticleCategory.objects.get(id=sql.category)
        cata_father_obj = ArticleCategory.objects.get(id=cata_obj.father)
    user_obj = Users.objects.values(*['id', 'nickName', 'avatar']).get(id=sql.author)
    article_detail = ArticleDetail.objects.get(article=sql.id)
    tag_id_list = ArticleTagRelation.objects.filter(article=sql.id)
    tag_obj_list = []
    for tag_id in tag_id_list:
        tag_obj = ArticleTag.objects.get(id=tag_id.tag)
        tag_obj_list.append(tag_obj)
    return res_handle(0, '查询成功',
                      {'baseInfo': sql, 'categoryInfo': {'base': cata_obj, 'father': cata_father_obj.name}
                      if cata_obj else None, 'authorInfo': user_obj, 'tagList': tag_obj_list,
                       'detailInfo': article_detail, 'createTime': sql.createTime})


@require_POST
def add_article(request):
    params = post_handle(request)
    msg = validate_add_article_params(params)
    if msg:
        return res_handle(501, msg, False)
    params['author'] = get_user_id(request)
    params['updateTime'] = datetime.now()
    exclude_keys = ['content', 'tags']
    model_params = {k: v for k, v in params.items() if k not in exclude_keys}
    article_obj = Article.objects.create(**model_params)
    ArticleDetail.objects.create(article=article_obj.id, content=params['content'])
    tag_list = []
    for item in params['tags']:
        tag_list.append(ArticleTagRelation(tag=item, article=article_obj.id))
    ArticleTagRelation.objects.bulk_create(tag_list)
    if params['status'] == 'publish':
        add_user_activity(request, 'publish_article', article_obj.id, '发表文章', {'title': params['title']})
    else:
        add_user_activity(request, 'create_draft', article_obj.id, '创建草稿', {'title': params['title']})
    return res_handle(0, '添加成功', article_obj.id)


@require_POST
def edit_article(request):
    params = post_handle(request)
    msg = validate_add_article_params(params)
    if msg:
        return res_handle(501, msg, False)
    article_obj = Article.objects.get(id=params['id'])
    author = article_obj.author
    params['author'] = get_user_id(request)
    if str(author) != str(params['author']):
        return res_handle(500, '您没有修改此文章的权限')
    if article_obj.status != 'publish' and params['status'] == 'publish':
        params['createTime'] = datetime.now()
        add_user_activity(request, 'publish_article', article_obj.id, '发表文章', {'title': params['title']})
    elif article_obj.status == 'publish' and params['status'] == 'publish':
        add_user_activity(request, 'update_article', article_obj.id, '更新文章', {'title': params['title']})
    params['updateTime'] = datetime.now()
    exclude_keys = ['content', 'tags']
    model_params = {k: v for k, v in params.items() if k not in exclude_keys}
    Article.objects.filter(id=params['id']).update(**model_params)
    ArticleDetail.objects.filter(article=params['id']).update(content=params['content'])
    ArticleTagRelation.objects.filter(article=params['id']).delete()
    tag_list = []
    for item in params['tags']:
        tag_list.append(ArticleTagRelation(tag=item, article=article_obj.id))
    ArticleTagRelation.objects.bulk_create(tag_list)
    return res_handle(0, '修改成功', True)


@require_POST
def delete_article(request):
    params = post_handle(request)
    article_obj = Article.objects.filter(id=params['id']).first()
    title = article_obj.title if article_obj else ''
    add_user_activity(request, 'delete_article', params['id'], '删除文章', {'title': title})
    Article.objects.filter(id=params['id']).delete()
    ArticleDetail.objects.filter(article=params['id']).delete()
    ArticleTagRelation.objects.filter(article=params['id']).delete()
    return res_handle(0, '删除成功', True)


@require_POST
def get_hot_article_list(request):
    queryset = Article.objects.filter(status='publish').order_by('-createTime')[:10]
    data = ArticleSerializers(instance=queryset, many=True)
    return res_search(data.data)


@require_POST
def get_article_publish_stat(request):
    params = post_handle(request)
    queryset = Article.objects.filter(status='publish')

    data = get_count_stats(
        queryset=queryset,
        date_field="createTime",
        range_type=params['rangeType'],
        start_date=params['startDate'],
        end_date=params['endDate']
    )
    return res_search(data)


def record_article_read(article_id, user_id=None, ip=None):
    today = datetime.now().date()
    if user_id:
        already_read = ArticleReadLog.objects.filter(
            article=article_id, user=user_id, readTime__date=today
        ).exists()
    else:
        already_read = ArticleReadLog.objects.filter(
            article=article_id, ip=ip, readTime__date=today
        ).exists()

    if not already_read:
        ArticleReadLog.objects.create(article=article_id, user=user_id, ip=ip)
        Article.objects.filter(id=article_id).update(readCount=F('readCount') + 1)


@require_POST
def get_article_read_stat(request):
    params = post_handle(request)
    article_id = params['id']

    today = datetime.now().date()
    today_count = ArticleReadLog.objects.filter(
        article=article_id, readTime__date=today
    ).count()
    total_count = ArticleReadLog.objects.filter(article=article_id).count()

    return res_search({
        'todayRead': today_count,
        'totalRead': total_count,
    })
