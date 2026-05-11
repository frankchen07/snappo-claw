"""File-based JSON cache with TTL."""

import json
import os
import re
import time
from typing import Any


class FileCache:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _key_to_path(self, key: str) -> str:
        safe = re.sub(r"[^\w\-]", "_", key)
        return os.path.join(self.cache_dir, f"{safe}.json")

    def get(self, key: str) -> tuple[Any, bool] | None:
        path = self._key_to_path(key)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            entry = json.load(f)
        cached_at = entry["cached_at"]
        ttl = entry["ttl_seconds"]
        is_fresh = (time.time() - cached_at) < ttl
        return entry["data"], is_fresh

    def set(self, key: str, data: Any, ttl_seconds: int = 3600) -> None:
        path = self._key_to_path(key)
        entry = {
            "data": data,
            "cached_at": time.time(),
            "ttl_seconds": ttl_seconds,
        }
        with open(path, "w") as f:
            json.dump(entry, f)

    def invalidate(self, key: str) -> None:
        path = self._key_to_path(key)
        if os.path.exists(path):
            os.remove(path)

    def manifest(self) -> dict:
        result = {}
        for fname in os.listdir(self.cache_dir):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(self.cache_dir, fname)
            try:
                with open(path) as f:
                    entry = json.load(f)
                cached_at = entry["cached_at"]
                ttl = entry["ttl_seconds"]
                result[fname[:-5]] = {
                    "cached_at": cached_at,
                    "ttl_seconds": ttl,
                    "is_fresh": (time.time() - cached_at) < ttl,
                }
            except Exception:
                pass
        return result
