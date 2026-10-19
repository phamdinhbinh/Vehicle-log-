"""Chức năng: API tương thích để nhập BLF/MF4 vào cache tín hiệu.

Sửa tại đây khi: đổi tên API công khai; logic nằm trong các component readers/.
Liên kết: readers/service.py điều phối; readers/blf.py, mf4.py đọc từng định dạng.
"""
# COMPONENT: importers.facade

from .readers.service import IMPORTER_SCHEMA, import_log
from .readers.blf import (
    BLF_BATCH_FRAMES, BLF_BATCH_VALUES, DIAGNOSTIC_LIMIT, FRAME_PREVIEW_LIMIT,
)
from .readers.mf4 import MF4_BATCH_SAMPLES, MF4_READ_FRAGMENT_SIZE

__all__ = ["import_log"]
