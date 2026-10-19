"""Chức năng: tiện ích JSON, thời gian gốc, tiến độ và hủy khi ghi MF4.

Sửa tại đây khi: đổi cách lưu metadata, mốc UTC hoặc tích hợp tiến độ asammdf.
Liên kết: atomic.py, selection.py, excel_metadata.py, mf4.py và raw_mf4.py.
"""
# COMPONENT: writers.common
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json

from ..models import CancelledError, report

def _check(token):
    """Kiểm tra yêu cầu hủy; dùng chung cho mọi bước ghi theo từng phần."""
    if token:
        token.check()

def _json(value):
    """Tuần tự hóa metadata/dataclass, giữ nguyên tiếng Việt trong báo cáo."""
    if is_dataclass(value):
        value = asdict(value)
    return json.dumps(value, ensure_ascii=False, default=str)

def _set_start_time(mdf, metadata):
    """Gán mốc UTC nguồn cho header MF4, bỏ qua metadata thời gian hỏng."""
    value = metadata.get("start_time")
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif isinstance(value, (int, float)):
            value = datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, datetime):
            mdf.header.start_time = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, OSError):
        pass

def _save_mf4(mdf, path, progress, token):
    """Nối tiến độ/hủy của asammdf vào callback độc lập với giao diện Qt."""
    from types import SimpleNamespace
    from asammdf.blocks.utils import Terminated

    class SaveProgress:
        """Adapter cấu trúc progress do asammdf yêu cầu khi lưu file."""
        def __init__(self):
            self.signals = SimpleNamespace(setValue=SimpleNamespace(emit=self.emit))

        def emit(self, value):
            report(progress, 0.9+min(float(value), 100)/100*0.099, "Đang ghi file MF4")

        @property
        def stop(self):
            try:
                _check(token)
            except CancelledError:
                return True
            return False

    _check(token)
    try:
        mdf.save(str(path), overwrite=True, compression=2, progress=SaveProgress())
    except Terminated:
        _check(token)
        raise
    _check(token)
