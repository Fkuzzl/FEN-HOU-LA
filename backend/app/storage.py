"""Provider-independent private receipt storage.

Local storage is the default. R2 uses its S3-compatible API and is only
constructed when explicitly selected with complete server-side credentials.
"""

from pathlib import Path
from typing import Protocol


class PrivateObjectStore(Protocol):
    def put(self, key: str, content: bytes) -> None: ...
    def delete(self, key: str) -> None: ...
    def get(self, key: str) -> bytes | None: ...


class LocalPrivateObjectStore:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if candidate.parent != self.root or candidate == self.root:
            raise ValueError("invalid storage key")
        return candidate

    def put(self, key: str, content: bytes) -> None:
        self._safe_path(key).write_bytes(content)

    def delete(self, key: str) -> None:
        self._safe_path(key).unlink(missing_ok=True)

    def get(self, key: str) -> bytes | None:
        candidate = self._safe_path(key)
        return candidate.read_bytes() if candidate.is_file() else None


class R2PrivateObjectStore:
    def __init__(self, endpoint: str, access_key_id: str, secret_access_key: str, bucket: str):
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - exercised only in R2 deployments
            raise RuntimeError("R2 storage requires the boto3 dependency") from exc
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )

    def put(self, key: str, content: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content)

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def get(self, key: str) -> bytes | None:
        from botocore.exceptions import ClientError
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
                return None
            raise
