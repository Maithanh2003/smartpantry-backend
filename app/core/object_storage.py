from dataclasses import dataclass

import boto3
from botocore.client import BaseClient
from botocore.config import Config


@dataclass
class ObjectStorageConfig:
    endpoint_url: str | None
    region: str
    bucket: str
    access_key_id: str
    secret_access_key: str


class ObjectStorageClient:
    def __init__(self, config: ObjectStorageConfig) -> None:
        self.config = config
        # MinIO + Cloudflare R2 expect path-style addressing when using a custom endpoint.
        client_config = None
        if config.endpoint_url:
            client_config = Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            )
        self.client: BaseClient = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            region_name=config.region,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            config=client_config,
        )

    def upload_bytes(self, *, path: str, content: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.config.bucket,
            Key=path,
            Body=content,
            ContentType=content_type,
        )
