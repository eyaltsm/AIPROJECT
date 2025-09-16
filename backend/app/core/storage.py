import boto3
import urllib.parse
from datetime import timedelta
from typing import Optional
from app.core.config import settings
from botocore.exceptions import ClientError


# S3 client configuration
s3_client = boto3.client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT_URL,
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
    region_name=getattr(settings, 'S3_REGION', 'us-east-1')
)


def make_presigned_get(object_key: str, expires_in: Optional[int] = None) -> str:
    """Generate a presigned URL for downloading an object."""
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": object_key},
            ExpiresIn=expires_in or settings.S3_SIGNED_URL_EXPIRE_SECONDS,
        )
        return response
    except ClientError as e:
        raise Exception(f"Error generating presigned URL: {e}")


def make_presigned_put(object_key: str, content_type: str, expires_in: int = 600) -> str:
    """Generate a presigned URL for uploading an object."""
    try:
        response = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.S3_BUCKET, 
                "Key": object_key, 
                "ContentType": content_type
            },
            ExpiresIn=expires_in,
        )
        return response
    except ClientError as e:
        raise Exception(f"Error generating presigned upload URL: {e}")


def delete_object(object_key: str) -> bool:
    """Delete an object from S3."""
    try:
        s3_client.delete_object(Bucket=settings.S3_BUCKET, Key=object_key)
        return True
    except ClientError as e:
        print(f"Error deleting object {object_key}: {e}")
        return False


def object_exists(object_key: str) -> bool:
    """Check if an object exists in S3."""
    try:
        s3_client.head_object(Bucket=settings.S3_BUCKET, Key=object_key)
        return True
    except ClientError:
        return False


def get_object_metadata(object_key: str) -> Optional[dict]:
    """Get object metadata from S3."""
    try:
        response = s3_client.head_object(Bucket=settings.S3_BUCKET, Key=object_key)
        return {
            "size": response.get("ContentLength"),
            "last_modified": response.get("LastModified"),
            "content_type": response.get("ContentType"),
            "etag": response.get("ETag")
        }
    except ClientError:
        return None


def generate_object_key(prefix: str, filename: str) -> str:
    """Generate a secure object key for S3 storage."""
    # Remove any path components from filename
    safe_filename = filename.split('/')[-1]
    # Add timestamp to prevent collisions
    from datetime import datetime
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}/{timestamp}_{safe_filename}"


def setup_bucket_lifecycle():
    """Set up S3 bucket lifecycle policies for automatic cleanup."""
    lifecycle_config = {
        "Rules": [
            {
                "ID": "outputs_cleanup",
                "Status": "Enabled",
                "Filter": {"Prefix": "outputs/"},
                "Expiration": {"Days": 90}
            },
            {
                "ID": "datasets_cleanup",
                "Status": "Enabled", 
                "Filter": {"Prefix": "datasets/"},
                "Expiration": {"Days": 30}
            },
            {
                "ID": "temp_cleanup",
                "Status": "Enabled",
                "Filter": {"Prefix": "temp/"},
                "Expiration": {"Days": 1}
            }
        ]
    }
    
    try:
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=settings.S3_BUCKET,
            LifecycleConfiguration=lifecycle_config
        )
        return True
    except ClientError as e:
        print(f"Error setting up lifecycle policy: {e}")
        return False


