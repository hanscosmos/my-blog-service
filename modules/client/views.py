from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from modules.article.models import Article, ArticleDetail, ArticleTagRelation, ArticleCategory, ArticleTag, ArticleColumn, ArticleReadLog
from modules.article.serializers.article import ArticleSerializers
from modules.article.views.article import record_article_read
from modules.user.models import Users
from utils.response import res_handle, res_search
from utils.tools import post_handle, limit_queryset, obj_has_attr
from utils.auth import get_user_id


@require_POST
def get_client_article_list(request):
    params = post_handle(request)
    user_id = get_user_id(request)
    if user_id:
        sql = Article.objects.all().filter(
            title__contains=params['title'],
            status='publish',
        ).filter(Q(visible='public') | Q(visible='private', author=user_id))
    else:
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
def get_client_article_detail(request):
    cata_obj = None
    cata_father_obj = None
    params = post_handle(request)
    sql = Article.objects.all().get(id=params['id'])

    user_id = get_user_id(request)
    if sql.visible == 'private' and sql.author != user_id:
        return res_handle(403, '您没有权限查看该文章', None)
    ip = request.META.get('REMOTE_ADDR', None)
    record_article_read(article_id=sql.id, user_id=user_id, ip=ip)

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
def get_article_count_by_category(request):
    """统计每个类别下的已发布文章数量，父类别包含子类别的数量"""
    categories = list(ArticleCategory.objects.all())

    # 构建 children 映射: parent_id -> [child_ids]
    children_map = {}
    for c in categories:
        if c.father:
            children_map.setdefault(c.father, []).append(c.id)

    def get_all_descendants(cid):
        """递归获取类别及其所有子类别的 ID 集合"""
        ids = {cid}
        for child_id in children_map.get(cid, []):
            ids.update(get_all_descendants(child_id))
        return ids

    # 预计算每个类别的子孙 ID 集合
    descendants_map = {c.id: get_all_descendants(c.id) for c in categories}

    # 统计每个类别的直接文章数
    article_stat = Article.objects.filter(
        status='publish', visible='public'
    ).values('category').annotate(cnt=Count('id'))
    direct_count_map = {row['category']: row['cnt'] for row in article_stat}

    result = []
    for cate in categories:
        count = sum(direct_count_map.get(cid, 0) for cid in descendants_map[cate.id])
        result.append({'id': cate.id, 'name': cate.name, 'count': count})
    return res_search(result)


@require_POST
def get_article_count_by_tag(request):
    """统计每个标签关联的文章数量"""
    tags = ArticleTag.objects.all()
    result = []
    for tag in tags:
        count = ArticleTagRelation.objects.filter(tag=tag.id).count()
        result.append({'id': tag.id, 'name': tag.name, 'count': count})
    return res_search(result)


@require_POST
def get_article_count_by_column(request):
    """统计每个专栏下的已发布文章数量"""
    columns = ArticleColumn.objects.all()
    result = []
    for col in columns:
        count = Article.objects.filter(column=col.id, status='publish', visible='public').count()
        result.append({'id': col.id, 'name': col.name, 'count': count})
    return res_search(result)
