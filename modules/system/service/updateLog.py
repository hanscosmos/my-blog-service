from modules.system.models import UpdateLog


def validate_add_log_params(params):
    msg: str = ''
    summary, version, status = params['summary'], params['version'], params['status']
    if not summary:
        msg = '更新日志summary不得为空'
    if not version:
        msg = '更新日志version不得为空'
    if not status:
        msg = '更新日志分类不得为空'
    if len(summary) < 1 or len(summary) > 64:
        msg = '更新日志summary长度为1-64'
    if len(version) < 1 or len(version) > 16:
        msg = '更新日志version长度为1-16'
    return msg
