"""Điểm import công khai của hệ thống cache (giữ tương thích mã cũ).

Chức năng: đưa các component lưu trữ ra một API ổn định.
Sửa logic tại: storage/identity.py, storage/writer.py, storage/reader.py.
Liên kết: readers, calculations, writers và UI đều có thể import từ đây.
"""
# COMPONENT: storage.api
from .storage.identity import cache_key, default_cache_root
from .storage.reader import SignalStore
from .storage.schema import SCHEMA_VERSION
from .storage.writer import StoreWriter

__all__ = ["SignalStore", "StoreWriter", "cache_key", "default_cache_root", "SCHEMA_VERSION"]
