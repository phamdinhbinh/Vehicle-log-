"""Chức năng: đọc giá trị tại hai con trỏ và chênh lệch ΔY.

Sửa tại đây khi: đổi cách lấy mẫu tại mốc; mặc định giữ mẫu ngay trước mốc.
Liên kết: UI bảng đo gọi measure_between; không dùng dữ liệu preview đồ thị.
"""
# COMPONENT: measurements.cursor_values
from dataclasses import dataclass
import math

import numpy as np


@dataclass
class CursorMeasurement:
    """Một hàng kết quả đo; None biểu thị không có mẫu hợp lệ tại mốc."""
    key: str
    name: str
    unit: str
    start_value: float | None
    end_value: float | None
    delta: float | None
    start_age: float | None
    end_age: float | None


def sample_at(store, key, time):
    """Lấy mẫu trước/gặp mốc từ dữ liệu gốc; không ngoại suy ngoài tín hiệu."""
    info = store.signals[key]
    if not info.count or not math.isfinite(time) or time < info.start or time > info.end:
        return None, None
    times, values = store.read(key, start=time, end=time, neighbors=True)
    index = int(np.searchsorted(times, time, side="right")) - 1
    if index < 0 or not math.isfinite(float(values[index])):
        return None, None
    return float(values[index]), float(time - times[index])


def measure_between(store, keys, start, end):
    """Đo Y(start), Y(end), ΔY=Y(end)−Y(start) cho từng tín hiệu đã chọn."""
    rows = []
    for key in keys:
        info = store.signals[key]
        a, age_a = sample_at(store, key, start)
        b, age_b = sample_at(store, key, end)
        delta = b - a if a is not None and b is not None else None
        rows.append(CursorMeasurement(key, info.name, info.unit, a, b, delta, age_a, age_b))
    return rows
