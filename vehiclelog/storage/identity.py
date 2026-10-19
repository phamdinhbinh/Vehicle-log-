"""Định danh log/DBC và chọn nơi lưu cache.

Chức năng: chọn thư mục cache, tạo fingerprint từ file nguồn và DBC.
Sửa tại đây khi: muốn đổi ổ cache mặc định hoặc quy tắc tái sử dụng cache.
Liên kết: readers.service gọi cache_key trước/sau import; writer ghi kết quả.
"""
# COMPONENT: storage.identity
from __future__ import annotations

from pathlib import Path
import hashlib
import os
import tempfile

from .schema import SCHEMA_VERSION


def default_cache_root() -> Path:
    """Ưu tiên biến VEHICLELOG_CACHE_DIR, cache hệ điều hành, rồi thư mục tạm."""
    override = os.environ.get("VEHICLELOG_CACHE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else os.environ.get("XDG_CACHE_HOME")
    path = Path(base or Path.home() / ".cache") / "vehicle-log-studio"
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        # Managed/headless executors may have a read-only home directory.
        return Path(tempfile.gettempdir()) / f"vehicle-log-studio-{os.getuid() if hasattr(os, 'getuid') else 'user'}"


def cache_key(source, dbc_map=None) -> str:
    """Fingerprint gồm metadata/nội dung mẫu của log và toàn bộ nội dung DBC.

    Không băm toàn bộ log lớn. Đổi quy tắc này sẽ khiến cache được tạo lại.
    """
    path = Path(source).resolve()
    stat = path.stat()
    h = hashlib.sha256()
    h.update(f"v{SCHEMA_VERSION}|{path}|{stat.st_size}|{stat.st_mtime_ns}".encode())
    with path.open("rb") as f:
        h.update(f.read(131072))
        if stat.st_size > 131072:
            f.seek(max(0, stat.st_size - 131072))
            h.update(f.read(131072))
    for channel, dbc in sorted((dbc_map or {}).items(), key=lambda p: str(p[0])):
        dbc_path = Path(dbc).resolve()
        h.update(f"|{channel}|{dbc_path}|".encode())
        h.update(dbc_path.read_bytes())
    return h.hexdigest()[:32]
