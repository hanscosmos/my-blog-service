# config.py

from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Config:
    INIT_USER_PASSWORD: str
    ACCESS_TOKEN_WORK_TIME: float
    TOKEN_WORK_TIME: int
    USER_REFRESH_TOKEN_TIME: int
    JWT_SECRET_KEY: str
    COS_APPID: str
    COS_PROTOCOL: str
    COS_SECRET_ID: str
    COS_SECRET_KEY: str
    COS_REGION: str
    COS_TOKEN: str
    COS_BUCKET_NAME: str
    COS_DOMAIN: str
    CDN_DOMAIN: str
    AI_API_KEY: str
    AI_API_BASE_URL: str
    AI_MODEL: str

sysConfig = Config(INIT_USER_PASSWORD=os.getenv('INIT_USER_PASSWORD',''),
                   ACCESS_TOKEN_WORK_TIME=float(os.getenv('ACCESS_TOKEN_WORK_TIME','0.5')),
                   TOKEN_WORK_TIME=int(os.getenv('TOKEN_WORK_TIME','0')),
                   USER_REFRESH_TOKEN_TIME=int(os.getenv('USER_REFRESH_TOKEN_TIME','0')),
                   JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY',''),
                   COS_TOKEN=os.getenv('COS_TOKEN',''),
                   COS_APPID=os.getenv('COS_APPID',''),
                   COS_PROTOCOL=os.getenv('COS_PROTOCOL','http'),
                   COS_SECRET_ID=os.getenv('COS_SECRET_ID',''),
                   COS_SECRET_KEY=os.getenv('COS_SECRET_KEY',''),
                   COS_REGION=os.getenv('COS_REGION',''),
                   COS_BUCKET_NAME=os.getenv('COS_BUCKET_NAME',''),
                   COS_DOMAIN=os.getenv('COS_DOMAIN',''),
                   CDN_DOMAIN=os.getenv('CDN_DOMAIN',''),
                   AI_API_KEY=os.getenv('AI_API_KEY',''),
                   AI_API_BASE_URL=os.getenv('AI_API_BASE_URL','https://api.openai.com/v1'),
                   AI_MODEL=os.getenv('AI_MODEL','gpt-4o'))