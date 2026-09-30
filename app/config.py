import os
from functools import lru_cache

from pydantic import BaseModel

# 定義設定模型
class Settings(BaseModel):
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    s3_bucket_name: str
    cloudfront_domain: str
    database_url: str

# 使用 lru_cache 來快取設定，避免每次都重新讀取環境變數
@lru_cache
def get_settings() -> Settings:
    missing = [
        key
        for key in (
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_REGION",
            "S3_BUCKET_NAME",
            "CLOUDFRONT_DOMAIN",
            "DATABASE_URL",
        )
        if not os.getenv(key)
    ]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    return Settings(
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        aws_region=os.environ["AWS_REGION"],
        s3_bucket_name=os.environ["S3_BUCKET_NAME"],
        cloudfront_domain=os.environ["CLOUDFRONT_DOMAIN"].removeprefix("https://").removesuffix("/"),
        database_url=os.environ["DATABASE_URL"],
    )
