import asyncio
from typing import Optional
from app.adapters.storage.base import BaseStorageAdapter
from app.core.config import settings

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    ClientError = Exception  # type: ignore


class S3StorageAdapter(BaseStorageAdapter):
    """S3 / Supabase Storage adapter using boto3 with 2MB payload ceiling."""

    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region_name: str = "us-east-1",
    ):
        if not BOTO3_AVAILABLE:
            raise RuntimeError("boto3 is required for S3StorageAdapter. Please install boto3.")

        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=endpoint_url,
            region_name=region_name,
        )

    async def save(
        self, storage_key: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        # Enforce single payload ceiling (2 MB max)
        if len(content) > settings.PAYLOAD_MAX_SINGLE_BYTES:
            raise ValueError(
                f"Payload size ({len(content)} bytes) exceeds maximum single payload limit ({settings.PAYLOAD_MAX_SINGLE_BYTES} bytes)."
            )

        loop = asyncio.get_running_loop()
        def _upload():
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=storage_key,
                Body=content,
                ContentType=content_type,
            )
        await loop.run_in_executor(None, _upload)
        return storage_key

    async def get(self, storage_key: str) -> bytes:
        loop = asyncio.get_running_loop()
        def _download():
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=storage_key)
            return response["Body"].read()
        try:
            return await loop.run_in_executor(None, _download)
        except ClientError as e:
            raise FileNotFoundError(f"S3 Object '{storage_key}' not found in bucket '{self.bucket_name}': {e}")

    async def exists(self, storage_key: str) -> bool:
        loop = asyncio.get_running_loop()
        def _check():
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=storage_key)
                return True
            except ClientError:
                return False
        return await loop.run_in_executor(None, _check)

    async def delete(self, storage_key: str) -> bool:
        loop = asyncio.get_running_loop()
        def _delete():
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=storage_key)
        try:
            await loop.run_in_executor(None, _delete)
            return True
        except ClientError:
            return False

