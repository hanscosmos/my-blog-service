from modules.resource.models import Image, ImageCategory

BATCH_NAME_MAX = 15


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


def validate_batch_add_image_params(params):
    """批量新增图片的逐条校验

    规则与单条新增保持一致（名称长度、名称唯一、路径唯一），
    但逐条返回跳过原因，便于前端汇总提示。

    :return: (待入库列表, 跳过明细列表)
    """
    category = params['category']
    items = params['list']
    exist_names = set(
        Image.objects.filter(name__in=[item['name'] for item in items]).values_list('name', flat=True))
    exist_urls = set(
        Image.objects.filter(url__in=[item['url'] for item in items]).values_list('url', flat=True))

    valid_list, skip_list = [], []
    seen_names, seen_urls = set(), set()
    for item in items:
        name, url = item['name'], item['url']
        if len(name) < 2 or len(name) > BATCH_NAME_MAX:
            skip_list.append({'name': name, 'reason': f'名称长度需为2-{BATCH_NAME_MAX}字符'})
        elif name in exist_names or name in seen_names:
            skip_list.append({'name': name, 'reason': '图片名已存在'})
        elif url in exist_urls or url in seen_urls:
            skip_list.append({'name': name, 'reason': '路径已存在'})
        else:
            seen_names.add(name)
            seen_urls.add(url)
            valid_list.append({
                'name': name,
                'url': url,
                'category': category,
                'sort': 0,
                'desc': '',
            })

    return valid_list, skip_list
