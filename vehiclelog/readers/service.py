"""Chức năng: điều phối nhập log, xác thực nguồn và vòng đời bộ nhớ đệm.

Sửa tại đây khi: đổi lựa chọn bộ đọc, fingerprint hoặc cách tạo/mở lại cache.
Liên kết: importers.py là API tương thích; blf.py/mf4.py đọc dữ liệu; store.py lưu cache.
"""
# COMPONENT: readers.service

from __future__ import annotations

from pathlib import Path
import uuid

from ..models import report
from ..store import SignalStore, StoreWriter, cache_key, default_cache_root
from .blf import import_blf
from .common import check_cancelled
from .dbc import normalize_dbc_mapping
from .mf4 import import_mf4

# Tăng phiên bản khi cấu trúc/ý nghĩa cache nhập thay đổi.
IMPORTER_SCHEMA = 2


def import_log(source, dbc_map=None, cache_root=None, progress=None,
               token=None, force=False) -> SignalStore:
    """Nhập BLF/MF4 số; tái sử dụng cache theo fingerprint nguồn và DBC.

    Nhập lại bắt buộc tạo cache mới để đồ thị/xuất file đang dùng cache cũ
    không mất dữ liệu. Không tự xóa cache còn được các thành phần khác sử dụng.
    """
    source = Path(source).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Không tìm thấy log: {source}")
    extension = source.suffix.lower()
    if extension not in {".blf", ".mf4", ".mdf"}:
        raise ValueError("Định dạng hỗ trợ: .blf, .mf4 và .mdf (MDF 4).")
    mapping = normalize_dbc_mapping(dbc_map)
    check_cancelled(token)
    fingerprint = cache_key(source, mapping)
    root = Path(cache_root) if cache_root is not None else default_cache_root()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"import{IMPORTER_SCHEMA}-{fingerprint}"
    if destination.exists() and not force:
        store = SignalStore(destination)
        if store.metadata.get("fingerprint") == fingerprint:
            report(progress, 1.0, "Đã mở dữ liệu từ bộ nhớ đệm.")
            return store
        # Cache chưa hoàn tất hoặc thuộc phiên bản bộ nhập khác.
        force = True
    if force and destination.exists():
        destination = root / f"import{IMPORTER_SCHEMA}-{fingerprint}-{uuid.uuid4().hex[:8]}"
    metadata = {
        "source": str(source), "source_size": source.stat().st_size,
        "dbc_map": {str(k): v for k, v in mapping.items()},
        "fingerprint": fingerprint, "importer_schema": IMPORTER_SCHEMA,
        "numeric_storage": "float64",
        "warnings": [], "start_time": 0.0, "duration": 0.0,
    }
    report(progress, 0.0, "Đang kiểm tra dữ liệu đầu vào…")
    with StoreWriter(destination, metadata=metadata) as writer:
        if extension == ".blf":
            import_blf(source, mapping, writer, progress, token)
        else:
            import_mf4(source, mapping, writer, progress, token)
        check_cancelled(token)
        # Chỉ công bố cache nếu log và DBC không đổi trong toàn bộ lần nhập.
        if cache_key(source, mapping) != fingerprint:
            raise ValueError(
                "File log hoặc DBC đã thay đổi trong lúc nhập. "
                "Hãy dừng ghi log và nhập lại; dữ liệu chưa được công bố."
            )
        store = writer.finish()
    report(progress, 1.0, "Đã đọc và lưu dữ liệu.")
    return store
