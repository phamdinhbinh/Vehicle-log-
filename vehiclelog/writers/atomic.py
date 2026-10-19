"""Chức năng: bảo vệ file nguồn/DBC/cache và công bố file xuất hoàn tất.

Sửa tại đây khi: đổi chính sách đường dẫn, file tạm hoặc chống ghi đè.
Liên kết: excel.py, mf4.py và raw_mf4.py đều dùng _output.
"""
# COMPONENT: writers.atomic
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import tempfile

from .common import _check

def _protected(store=None, source=None, dbc_map=None):
    """Thu thập đường dẫn nguồn và DBC tuyệt đối để chặn ghi đè."""
    paths = []
    if source:
        paths.append(Path(source).expanduser().resolve())
    if store is not None:
        metadata = store.metadata
        if metadata.get("source"):
            paths.append(Path(metadata["source"]).expanduser().resolve())
        dbc_map = metadata.get("dbc_map", dbc_map)
    if dbc_map:
        paths.extend(Path(p).expanduser().resolve() for p in dbc_map.values())
    return paths

@contextmanager
def _output(destination, *, store=None, source=None, dbc_map=None, token=None):
    """Ghi vào file tạm, chỉ công bố khi thành công và không ghi đè đích."""
    destination = Path(destination).expanduser().resolve()
    if destination in _protected(store, source, dbc_map):
        raise ValueError("Không được ghi đè file nguồn hoặc DBC.")
    if store is not None:
        store_path = Path(store.path).resolve()
        if destination == store_path or store_path in destination.parents:
            raise ValueError("Không được ghi kết quả vào bên trong bộ nhớ đệm dữ liệu.")
    if destination.exists():
        raise FileExistsError(f"File đích đã tồn tại: {destination}")
    if not destination.parent.is_dir():
        raise FileNotFoundError(f"Thư mục đích không tồn tại: {destination.parent}")
    _check(token)
    fd, name = tempfile.mkstemp(prefix=f".{destination.stem}-", suffix=destination.suffix.lower(),
                                dir=destination.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        yield temporary
        _check(token)
        # File tạm ở cùng filesystem: công bố nguyên tử, không được ghi đè
        # ngay cả khi tác vụ khác vừa tạo đích sau lần kiểm tra exists().
        if os.name == "nt":
            # Windows rename từ chối đích đã có và chạy trên ổ không có hardlink.
            os.rename(temporary, destination)
        else:
            os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
