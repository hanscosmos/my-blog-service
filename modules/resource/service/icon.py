from modules.resource.models import Icon, IconCategory


def validate_add_icon_params(params, icon_id):
    msg: str = ''
    name, url = params['name'], params['url']
    if not name:
        msg = '图标名不得为空'
    if not url:
        msg = '路径不得为空'
    if len(name) < 1 or len(name) > 10:
        msg = '图标名长度为1-10'
    name_sql = Icon.objects.filter(name=name)
    url_sql = Icon.objects.filter(url=url)
    if not icon_id:
        is_name_exist = name_sql.exists()
        is_url_exist = url_sql.exists()
    else:
        is_name_exist = name_sql.exclude(id=icon_id).exists()
        is_url_exist = url_sql.exclude(id=icon_id).exists()
    if is_name_exist:
        msg = '图标名已存在'
    if is_url_exist:
        msg = '路径已存在'
    return msg