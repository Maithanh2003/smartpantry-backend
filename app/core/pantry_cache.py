import hashlib
import json
from typing import Any

from redis import Redis
from redis.exceptions import RedisError


class PantryListCache:
    """Redis cache adapter for pantry list endpoint."""

    def __init__(self, redis_client: Redis, *, ttl_seconds: int = 120, key_prefix: str = "smartpantry:pantry-list") -> None:
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix

    def _canonical_filters(self, filters: dict[str, Any]) -> str:
        return json.dumps(filters, sort_keys=True, separators=(",", ":"), default=str)

    def build_key(self, *, user_id: int, filters: dict[str, Any]) -> str:
        digest = hashlib.sha256(self._canonical_filters(filters).encode("utf-8")).hexdigest()
        return f"{self.key_prefix}:u:{user_id}:q:{digest}"

    def get(self, key: str) -> tuple[list[dict], int] | None:
        raw = self.redis_client.get(key)
        if not raw:
            return None
        try:
            payload = json.loads(raw)
            return payload["rows"], int(payload["total"])
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def set(self, key: str, rows: list[dict], total: int) -> None:
        body = json.dumps({"rows": rows, "total": total}, default=str, separators=(",", ":"))
        self.redis_client.setex(key, self.ttl_seconds, body)

    def invalidate_user(self, user_id: int) -> None:
        pattern = f"{self.key_prefix}:u:{user_id}:q:*"
        cursor = 0
        while True:
            cursor, keys = self.redis_client.scan(cursor=cursor, match=pattern, count=200)
            if keys:
                self.redis_client.delete(*keys)
            if cursor == 0:
                break
