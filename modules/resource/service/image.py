from modules.resource.models import Image, ImageCategory


def validate_add_image_params(params, image_id):
    msg: str = ''
    name, url = params['name'], params['url']
    if not name:
        msg = '图片名不得为空'
    if not url:
        msg = '路径不得为空'
    if len(name) < 2 or len(name) > 15:
        msg = '图片名长度为1-15'
    name_sql = Image.objects.filter(name=name)
    url_sql = Image.objects.filter(url=url)
    if not image_id:
        is_name_exist = name_sql.exists()
        is_url_exist = url_sql.exists()
    else:
        is_name_exist = name_sql.exclude(id=image_id).exists()
        is_url_exist = url_sql.exclude(id=image_id).exists()
    if is_name_exist:
        msg = '图片名已存在'
    if is_url_exist:
        msg = '路径已存在'

    return msg

