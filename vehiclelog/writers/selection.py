"""Chức năng: xác thực tín hiệu, phạm vi giai đoạn và nguồn gốc dữ liệu.

Sửa tại đây khi: đổi lựa chọn tín hiệu, phạm vi toàn log hoặc metadata giai đoạn.
Liên kết: excel.py và mf4.py; models.Segment xác thực ranh giới.
"""
# COMPONENT: writers.selection
from __future__ import annotations

from dataclasses import asdict

from ..models import Segment
from .common import _json

def _keys(store, keys):
    """Lọc khóa trùng, xác thực tín hiệu; None nghĩa là tất cả tín hiệu."""
    selected = list(store.signals) if keys is None else list(dict.fromkeys(keys))
    if not selected:
        raise ValueError("Cần chọn ít nhất một tín hiệu để xuất.")
    unknown = set(selected).difference(store.signals)
    if unknown:
        raise ValueError(f"Không tìm thấy tín hiệu: {', '.join(sorted(unknown))}")
    return selected

def _scopes(store, keys, segments):
    """Xác thực giai đoạn hoặc lấy toàn khoảng thời gian tín hiệu đã chọn."""
    if segments:
        scopes = list(segments)
        for segment in scopes:
            segment.validate()
        return scopes
    start = min(float(store.signals[k].start) for k in keys)
    end = max(float(store.signals[k].end) for k in keys)
    return [Segment("Toàn bộ log", start, end, id="full-log")]

def _provenance(store, segment, *, zero_time=False):
    """Lưu mốc thời gian nguồn và offset để truy ngược đoạn MF4 đã cắt."""
    return _json({"source": store.metadata.get("source", ""),
                  "signal_time_basis": "seconds relative to source log origin",
                  "segment": asdict(segment),
                  "output_time_offset_s": segment.start if zero_time else 0.0})
