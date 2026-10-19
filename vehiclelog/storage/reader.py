"""Đọc cache bằng memory map và tạo dữ liệu xem trước đồ thị.

Chức năng: đọc tín hiệu/vùng thời gian, lặp từng khối, lấy bao min/max.
Sửa tại đây khi: thay truy vấn cửa sổ thời gian hoặc cách rút gọn đồ thị.
Liên kết: calculations/writers dùng read/iter_chunks; UI dùng plot_data.
"""
# COMPONENT: storage.reader
from __future__ import annotations

from pathlib import Path
import hashlib
import json

import numpy as np

from ..models import SignalInfo
from .schema import SCHEMA_VERSION


class SignalStore:
    """Cache chỉ đọc; tín hiệu được ánh xạ ổ đĩa, không nạp toàn log vào RAM."""

    def __init__(self, path):
        self.path = Path(path).resolve()
        manifest = json.loads((self.path / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Phiên bản cache không được hỗ trợ.")
        self.metadata = manifest["metadata"]
        self.signals = {row["key"]: SignalInfo(**row) for row in manifest["signals"]}
        self._files = manifest["files"]
        for key, info in self.signals.items():
            stem = self._files[key]
            if stem != hashlib.sha256(key.encode()).hexdigest()[:32]:
                raise ValueError("Tên tệp cache không hợp lệ.")
            for suffix in ("t", "v"):
                if (self.path / f"{stem}.{suffix}").stat().st_size != info.count * 8:
                    raise ValueError(f"Cache thiếu hoặc hỏng dữ liệu: {info.name}.")

    def read(self, key, start=None, end=None, neighbors=False):
        """Lấy mẫu trong khoảng đóng [start, end]; neighbors thêm mẫu hai bên.

        Mẫu lân cận phục vụ nội suy tại ranh giới, không phải ngoại suy.
        """
        info = self.signals[key]
        if not info.count:
            return np.array([], dtype=float), np.array([], dtype=float)
        if start is not None and end is not None and end < start:
            raise ValueError("Khoảng thời gian không hợp lệ.")
        stem = self._files[key]
        t = np.memmap(self.path / f"{stem}.t", dtype="<f8", mode="r")
        v = np.memmap(self.path / f"{stem}.v", dtype="<f8", mode="r")
        lo = 0 if start is None else int(np.searchsorted(t, start, side="left"))
        hi = len(t) if end is None else int(np.searchsorted(t, end, side="right"))
        if neighbors:
            lo, hi = max(0, lo - 1), min(len(t), hi + 1)
        return t[lo:hi], v[lo:hi]

    def iter_chunks(self, key, start=None, end=None, chunk_size=100000):
        """Lặp từng khối đầy đủ để xuất/tính, không dùng dữ liệu rút gọn."""
        if chunk_size <= 0:
            raise ValueError("chunk_size phải lớn hơn 0.")
        t, v = self.read(key, start, end)
        for i in range(0, len(t), chunk_size):
            yield t[i:i + chunk_size], v[i:i + chunk_size]

    def plot_data(self, key, start=None, end=None, max_points=4000):
        """Bao min/max giữ đỉnh và NaN; chỉ để vẽ, không dùng tính năng lượng."""
        t, v = self.read(key, start, end)
        max_points = max(8, int(max_points))
        if len(t) <= max_points:
            return np.asarray(t), np.asarray(v)
        buckets = max(1, (max_points - 2) // 3)
        edges = np.linspace(0, len(t), buckets + 1, dtype=int)
        indexes = [0, len(t) - 1]
        for lo, hi in zip(edges[:-1], edges[1:]):
            block = v[lo:hi]
            finite = np.isfinite(block)
            if finite.any():
                safe = np.where(finite, block, np.nan)
                indexes.extend((lo + int(np.nanargmin(safe)), lo + int(np.nanargmax(safe))))
            if not finite.all():
                indexes.append(lo + int(np.flatnonzero(~finite)[0]))
        indexes = np.unique(indexes)
        return np.asarray(t[indexes]), np.asarray(v[indexes])
