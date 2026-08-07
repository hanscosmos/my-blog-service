import os
from django.conf import settings
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
from config.config import sysConfig

config = CosConfig(Region=sysConfig.COS_REGION, SecretId=sysConfig.COS_SECRET_ID, SecretKey=sysConfig.COS_SECRET_KEY, Token=sysConfig.COS_TOKEN,
                   Scheme=sysConfig.COS_PROTOCOL)
client = CosS3Client(config)


def handle_uploaded_file(f, path, filename):
    if not os.path.exists(path):
        os.makedirs(path)
    with open(os.path.join(path, filename), 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def upload_file_to_server(file, file_name, file_dir):
    if not file:
        return ''
    file_path = os.path.join(settings.BASE_DIR, 'static', 'img')
    handle_uploaded_file(file, file_path, file_name)
    real_path = os.path.join('static', 'img', file_name)
    # 上传文件
    file_target = file_dir + '/' + file_name
    response = client.upload_file(
        Bucket=sysConfig.COS_BUCKET_NAME,
        LocalFilePath=real_path,  # 本地文件的路径
        Key=file_target,  # 上传到桶之后的文件名
        PartSize=1,  # 上传分成几部分
        MAXThread=10,  # 支持最多的线程数
        EnableMD5=False  # 是否支持MD5
    )
    file_url = sysConfig.COS_PROTOCOL + '://' + sysConfig.CDN_DOMAIN + '/' + file_target
    os.remove(real_path)
    if not response['ETag']:
        return {'code': 500, 'msg': '上传失败'}
    return file_url
