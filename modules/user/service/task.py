def validate_add_task_params(params):
    msg: str = ''
    title = params['title']
    if not title:
        msg = '任务标题不得为空'
    if len(title) < 2 or len(title) > 64:
        msg = '任务标题长度为2-64'
    return msg