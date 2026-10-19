"""Chức năng: Tạo đồ thị xem trước công thức với số điểm và bộ nhớ giới hạn.

Sửa tại đây khi: đổi cách rút gọn đồ thị công thức nhưng vẫn giữ đỉnh và khoảng thiếu dữ liệu.
Liên kết: controllers/formulas.py gọi hàm; backend formulas.py cung cấp dữ liệu đầy đủ.
"""
# COMPONENT: ui.trace_preview
from __future__ import annotations

import numpy as np

def trace_preview(store, formula, segment, progress=None, token=None, max_points=4000):
    """Tạo bao min/max giới hạn bộ nhớ, chỉ dùng để vẽ đồ thị.

    Chuỗi nhỏ giữ nguyên mẫu; chuỗi lớn giữ cực trị tại timestamp thật
    và ngắt NaN khi thiếu dữ liệu. Không dùng kết quả này để tính hoặc xuất.
    """
    from ..formulas import iter_evaluate_trace
    bin_count = max(1, max_points // 3)
    minimum = np.full(bin_count, np.inf)
    maximum = np.full(bin_count, -np.inf)
    min_times = np.full(bin_count, np.inf)
    max_times = np.full(bin_count, -np.inf)
    gap_times = np.full(bin_count, np.inf)
    span = max(segment.end - segment.start, np.finfo(float).eps)
    small_chunks = []
    total = 0
    for times, values in iter_evaluate_trace(store, formula, segment, token=token):
        if token:
            token.check()
        total += len(times)
        if total <= max_points:
            small_chunks.append((times.copy(), values.copy()))
        else:
            small_chunks.clear()
        indices = np.clip(((times - segment.start) * bin_count / span).astype(np.int64), 0, bin_count - 1)
        valid = np.isfinite(values)
        ids, vals, stamps = indices[valid], values[valid], times[valid]
        previous_min, previous_max = minimum.copy(), maximum.copy()
        np.minimum.at(minimum, ids, vals)
        np.maximum.at(maximum, ids, vals)
        min_times[minimum < previous_min] = np.inf
        max_times[maximum > previous_max] = -np.inf
        low = vals == minimum[ids]
        high = vals == maximum[ids]
        np.minimum.at(min_times, ids[low], stamps[low])
        np.maximum.at(max_times, ids[high], stamps[high])
        np.minimum.at(gap_times, indices[~valid], times[~valid])
        if progress and len(times):
            progress(min(1.0, max(0.0, (float(times[-1]) - segment.start) / span)), "Đang tạo đồ thị công thức…")
    if total <= max_points:
        return (np.concatenate([t for t, _ in small_chunks]), np.concatenate([v for _, v in small_chunks])) if small_chunks else (np.empty(0), np.empty(0))
    output = []
    for index in range(bin_count):
        if np.isfinite(min_times[index]):
            output.append((min_times[index], minimum[index]))
        if np.isfinite(max_times[index]) and max_times[index] != min_times[index]:
            output.append((max_times[index], maximum[index]))
        if np.isfinite(gap_times[index]):
            output.append((gap_times[index], np.nan))
    output.sort(key=lambda point: point[0])
    if not output:
        return np.empty(0), np.empty(0)
    data = np.asarray(output, dtype=float)
    return data[:, 0], data[:, 1]

