import logging
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.pantry_cache import PantryListCache

logger = logging.getLogger(__name__)


class PantryCacheService:
    """Cache service facade for pantry list use-cases."""

    def __init__(
        self,
        redis_client: Redis,
        *,
        enabled: bool = True,
        ttl_seconds: int = 120,
        key_prefix: str = "smartpantry:pantry-list",
    ) -> None:
        self.enabled = enabled
        self._adapter = PantryListCache(
            redis_client,
            ttl_seconds=ttl_seconds,
            key_prefix=key_prefix,
        )

    def get_pantry_list(self, *, user_id: int, query_state: dict[str, Any]) -> tuple[list[dict], int] | None:
        if not self.enabled:
            return None
        key = self._adapter.build_key(user_id=user_id, filters=query_state)
        try:
            cached = self._adapter.get(key)
            if cached is None:
                logger.info("CACHE MISS key=%s user_id=%s", key, user_id)
                return None
            logger.info("CACHE HIT key=%s user_id=%s", key, user_id)
            return cached
        except RedisError as exc:
            logger.warning("REDIS ERROR FALLBACK action=get user_id=%s error=%s", user_id, exc)
            return None

    def set_pantry_list(self, *, user_id: int, query_state: dict[str, Any], rows: list[dict], total: int) -> None:
        if not self.enabled:
            return
        key = self._adapter.build_key(user_id=user_id, filters=query_state)
        try:
            self._adapter.set(key, rows, total)
            logger.info("CACHE SET key=%s user_id=%s ttl_seconds=%s", key, user_id, self._adapter.ttl_seconds)
        except RedisError as exc:
            logger.warning("REDIS ERROR FALLBACK action=set user_id=%s error=%s", user_id, exc)

    def invalidate_user_pantry_list(self, user_id: int) -> None:
        if not self.enabled:
            return
        try:
            self._adapter.invalidate_user(user_id)
            logger.info("CACHE INVALIDATE user_id=%s prefix=%s", user_id, self._adapter.key_prefix)
        except RedisError as exc:
            logger.warning("REDIS ERROR FALLBACK action=invalidate user_id=%s error=%s", user_id, exc)
