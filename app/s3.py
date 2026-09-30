import uuid
from pathlib import PurePath

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile

from app.config import get_settings

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024

# 根據上傳的檔案內容類型，返回對應的副檔名
def _extension_for(upload: UploadFile) -> str:
    content_type = (upload.content_type or "").lower()
    if content_type in ALLOWED_CONTENT_TYPES:
        return ALLOWED_CONTENT_TYPES[content_type]

    suffix = PurePath(upload.filename or "").suffix.lower()
    allowed_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    if suffix in allowed_suffixes:
        return ".jpg" if suffix == ".jpeg" else suffix

    raise HTTPException(status_code=400, detail="Only JPEG, PNG, WebP, or GIF images are allowed")


# 上傳圖片到 S3
def upload_image(upload: UploadFile) -> str:
    settings = get_settings()
    extension = _extension_for(upload)
    raw = upload.file.read(MAX_IMAGE_BYTES + 1)
    if not raw:
        raise HTTPException(status_code=400, detail="Image file is empty")
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image must be 5MB or smaller")

    key = f"messages/{uuid.uuid4().hex}{extension}"
    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    try:
        client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=key,
            Body=raw,
            ContentType=upload.content_type or "application/octet-stream",
        )
    except ClientError as exc:
        raise HTTPException(status_code=502, detail="Failed to upload image to S3") from exc

    return f"https://{settings.cloudfront_domain}/{key}"
