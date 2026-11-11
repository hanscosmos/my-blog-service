from django.views.decorators.http import require_POST
from modules.article.models import Article, ArticleColumn
from modules.user.models import Users, UserTask
from utils.api_service import get_month_stats, get_week_stats, get_current_stat
from utils.auth import get_user_id
from utils.response import res_handle, res_search
from utils.tools import post_handle
from utils.upload import upload_file_to_server

# 音频与音乐封面文件名带 nanoid、内容不会原地覆盖，适合长缓存
MUSIC_CACHE_TYPES = ('music', 'music-cover')
MUSIC_CACHE_CONTROL = 'public, max-age=31536000'


# Create your views here.
@require_POST
def upload_file(request):
    params = request.POST
    cache_control = MUSIC_CACHE_CONTROL if params['type'] in MUSIC_CACHE_TYPES else None
    upload_result = upload_file_to_server(
        request.FILES['file'], params['name'], params['type'], cache_control
    )
    return res_handle(0, '上传成功', upload_result)


def get_self_stats(request):
    user_id = get_user_id(request)
    article_sql = Article.objects.filter(author=user_id, status='publish')
    draft_sql = Article.objects.filter(author=user_id, status='draft')
    task_sql = UserTask.objects.filter(user=user_id, status='done')
    article_stats = get_current_stat(article_sql)
    draft_stats = get_current_stat(draft_sql)
    task_stats = get_current_stat(task_sql)
    return res_search({'article': article_stats, 'draft': draft_stats, 'task': task_stats})


def get_sys_stat(request):
    params = post_handle(request)
    sql_dict = {
        'article': Article.objects.filter(status='publish'),
        'drafts': Article.objects.filter(status='draft'),
        'user': Users.objects,
        'column': ArticleColumn.objects
    }
    result = get_week_stats(sql_dict[params['type']]) if params['rangeType'] == 'week' else get_month_stats(
        sql_dict[params['type']])
    return res_handle(0, '查询成功', result)
