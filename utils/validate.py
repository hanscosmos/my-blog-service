
def validate_post(post):
    error_arr = []
    for key in post.keys():
        if not post[key]:
            err_dict = {'key': key, 'message': '关键项不能为空'}
            error_arr.append(err_dict)
    return error_arr

