import boto3
from botocore.client import Config
from app.config import settings

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )

def ensure_bucket_exists():
    s3_client = get_s3_client()
    try:
        s3_client.head_bucket(Bucket=settings.MINIO_BUCKET)
    except:
        s3_client.create_bucket(Bucket=settings.MINIO_BUCKET)
