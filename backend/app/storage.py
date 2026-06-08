import re
from pathlib import Path
from uuid import uuid4

import boto3
from botocore.config import Config
from fastapi import HTTPException, status

from app.config import Settings


def safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(filename).name).strip("-")
    return cleaned or f"video-{uuid4().hex}"


def build_storage_key(room_code: str, filename: str) -> str:
    return f"rooms/{room_code}/{uuid4().hex}-{safe_filename(filename)}"


def public_url_for_key(settings: Settings, key: str) -> str | None:
    if not settings.s3_public_base_url:
        return None
    return f"{settings.s3_public_base_url.rstrip('/')}/{key}"


def s3_client(settings: Settings):
    if not settings.s3_bucket:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="S3 bucket is not configured")
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def create_presigned_upload(settings: Settings, key: str, content_type: str, size_bytes: int) -> dict:
    client = s3_client(settings)
    conditions = [
        ["content-length-range", 1, min(size_bytes, settings.max_upload_size_bytes)],
        {"Content-Type": content_type},
    ]
    fields = {"Content-Type": content_type}
    return client.generate_presigned_post(
        Bucket=settings.s3_bucket,
        Key=key,
        Fields=fields,
        Conditions=conditions,
        ExpiresIn=900,
    )
