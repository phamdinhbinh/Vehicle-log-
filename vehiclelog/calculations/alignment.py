"""Chức năng: căn tín hiệu theo timestamp với hold/linear và giới hạn mất mẫu.

Sửa tại đây khi: đổi quy tắc nội suy, tuổi mẫu hoặc xử lý ngoài phạm vi dữ liệu.
Liên kết: context.py gọi align_values; timeline.py bổ sung mốc hết hạn hold.
"""
from __future__ import annotations

# COMPONENT: calculations.alignment

import math

import numpy as np


def align_values(times, values, target, interpolation="hold", max_gap=1.0):
    """Căn tín hiệu lên timestamp đích (giây); không ngoại suy ngoài dữ liệu nguồn.

    hold: tuổi mẫu <= max_gap. linear: hai mẫu kẹp cách nhau <= max_gap;
    mẫu gốc chính xác vẫn hợp lệ. Giá trị lỗi/quá hạn trả NaN. Dung sai máy
    tránh nhận nhầm khoảng lấy mẫu thập phân đều là mất dữ liệu."""
    if interpolation not in {"hold", "linear"}:
        raise ValueError("Nội suy phải là hold hoặc linear.")
    if not math.isfinite(max_gap) or max_gap <= 0:
        raise ValueError("max_gap phải hữu hạn và lớn hơn 0.")
    times, values = np.asarray(times), np.asarray(values)
    target = np.asarray(target, dtype=float)
    result = np.full(target.shape, np.nan)
    if not len(times):
        return result
    indices = np.searchsorted(times, target, side="right") - 1
    safe = np.clip(indices, 0, len(times) - 1)
    valid = (indices >= 0) & (target <= times[-1]) & np.isfinite(target)
    # Khoảng CAN 100 ms không biểu diễn chính xác bằng số nhị phân.
    tolerance = 8*np.finfo(float).eps*np.maximum(1.,np.maximum(np.abs(target),np.abs(times[safe])))
    if interpolation == "hold":
        valid &= target - times[safe] <= max_gap+tolerance
        result[valid] = np.asarray(values)[safe[valid]]
    else:
        exact = valid & (target == times[safe])
        result[exact] = np.asarray(values)[safe[exact]]
        right = np.minimum(safe + 1, len(times) - 1)
        width = times[right] - times[safe]
        between = valid & ~exact & (right > safe) & (width <= max_gap+tolerance)
        if np.any(between):
            ix, jx = safe[between], right[between]
            f = (target[between] - times[ix]) / (times[jx] - times[ix])
            result[between] = values[ix] + f * (values[jx] - values[ix])
    result[~np.isfinite(result)] = np.nan
    return result
