"""Chức năng: hợp nhất trục thời gian lớn bằng các chunk giới hạn bộ nhớ.

Sửa tại đây khi: đổi cách chia chunk, gộp timestamp hoặc thêm mốc hết hạn hold.
Liên kết: engine.py và traces.py cùng gọi iter_time_grid; common.py chứa CHUNK_SIZE.
"""
from __future__ import annotations

# COMPONENT: calculations.timeline

import numpy as np

from .common import CHUNK_SIZE


def iter_time_grid(arrays, segment, interpolation, max_gap, chunk_size=CHUNK_SIZE):
    """Hợp nhất timestamp theo chunk, không concatenate toàn bộ memmap.

    Giữ hai ranh giới giai đoạn và mốc hết hạn hold để đo đúng độ phủ.
    Các chunk kề nhau dùng chung một điểm biên; consumer phải tránh đếm
    hai lần khi tính sample_mean hoặc ghép trace."""
    streams = []
    for times, _ in arrays.values():
        lo = np.searchsorted(times, segment.start, side="right")
        hi = np.searchsorted(times, segment.end, side="left")
        streams.append([times, int(lo), int(hi), 0.0])
        if interpolation == "hold":
            # Mốc hết hạn dư chỉ chia nhỏ khoảng hợp lệ, không đổi giá trị tính.
            lo = np.searchsorted(times, segment.start - max_gap, side="right")
            hi = np.searchsorted(times, segment.end - max_gap, side="left")
            streams.append([times, int(lo), int(hi), max_gap])
    previous = segment.start
    while True:
        active = sum(index < end for _, index, end, _ in streams)
        per_stream = max(1, chunk_size // max(1, active))
        ends = [times[min(index + per_stream, end) - 1] + shift
                for times, index, end, shift in streams if index < end]
        if not ends:
            if previous < segment.end:
                yield np.array([previous, segment.end])
            return
        boundary = min(ends)
        parts = [np.array([previous])]
        for stream in streams:
            times, index, end, shift = stream
            stop = min(int(np.searchsorted(times, np.nextafter(boundary - shift, np.inf), side="right")), end)
            if stop > index:
                parts.append(np.asarray(times[index:stop]) + shift)
            stream[1] = stop
        nodes = np.unique(np.concatenate(parts))
        nodes = nodes[(nodes >= previous) & (nodes <= segment.end)]
        if len(nodes) > 1:
            yield nodes
        # Tránh phát lại điểm biên do sai số khi cộng mốc hết hạn.
        if len(nodes):
            previous = float(nodes[-1])
