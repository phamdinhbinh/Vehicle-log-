"""Ghi cache tín hiệu theo từng khối và hoàn tất nguyên tử.

Chức năng: ghi file timestamp/giá trị float64, thống kê mẫu, tạo manifest.
Sửa tại đây khi: thay cách ghi, xử lý timestamp trùng hoặc hoàn tất cache.
Liên kết: các readers gửi từng khối vào StoreWriter; reader mở cache hoàn tất.
"""
# COMPONENT: storage.writer
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile

import numpy as np

from ..models import SignalInfo
from .schema import SCHEMA_VERSION
from .reader import SignalStore


class StoreWriter:
    """Nhận mẫu theo thứ tự thời gian; chỉ công bố cache khi finish thành công.

    Dùng trong khối with để tự dọn cache tạm nếu lỗi hoặc người dùng hủy.
    """

    def __init__(self, path, metadata=None):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise FileExistsError(self.path)
        self._temporary = Path(tempfile.mkdtemp(prefix=f".{self.path.name}.partial-", dir=self.path.parent))
        self.signals: dict[str, SignalInfo] = {}
        self.metadata = dict(metadata or {})
        self._files: dict[str, str] = {}
        self._finished = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if not self._finished:
            shutil.rmtree(self._temporary, ignore_errors=True)

    def add_signal(self, info: SignalInfo):
        """Đăng ký metadata và hai file nhị phân cho một tín hiệu mới."""
        if info.key in self.signals:
            return
        info = SignalInfo(**asdict(info))
        info.count = 0
        info.start = info.end = 0.0
        self.signals[info.key] = info
        name = hashlib.sha256(info.key.encode()).hexdigest()[:32]
        self._files[info.key] = name
        (self._temporary / f"{name}.t").touch()
        (self._temporary / f"{name}.v").touch()

    def append(self, key, times, values):
        """Ghi một khối mẫu; timestamp trùng lấy mẫu cuối, đi lùi bị từ chối."""
        info = self.signals[key]
        t = np.asarray(times, dtype="<f8").reshape(-1)
        v = np.asarray(values, dtype="<f8").reshape(-1)
        if len(t) != len(v):
            raise ValueError("Timestamp và giá trị phải có cùng số mẫu.")
        if not len(t):
            return
        if not np.all(np.isfinite(t)):
            raise ValueError("Timestamp không hợp lệ.")
        if np.any(t[1:] < t[:-1]):
            order = np.argsort(t, kind="stable")
            t, v = t[order], v[order]
        # Timestamp trùng lấy giá trị cuối, kể cả ở ranh giới hai khối đọc.
        keep = np.r_[t[1:] != t[:-1], True]
        t, v = t[keep], v[keep]
        if info.count and t[0] < info.end:
            raise ValueError(f"Timestamp đi lùi giữa các khối của {info.name}; cần kiểm tra log.")
        replace_last = bool(info.count and t[0] == info.end)
        stem = self._files[key]
        for suffix, array in (("t", t), ("v", v)):
            with (self._temporary / f"{stem}.{suffix}").open("r+b") as f:
                f.seek(-8 if replace_last else 0, os.SEEK_END)
                array.tofile(f)
        if not info.count:
            info.start = float(t[0])
        info.end = float(t[-1])
        info.count += len(t) - int(replace_last)

    def finish(self) -> "SignalStore":
        """Ghi manifest, đổi thư mục tạm thành cache hoàn chỉnh và mở reader."""
        if self._finished:
            raise RuntimeError("Store đã hoàn tất.")
        if self.path.exists():
            raise FileExistsError(self.path)
        self.metadata["duration"] = max(float(self.metadata.get("duration", 0)), max((s.end for s in self.signals.values()), default=0.0))
        manifest = {"schema_version": SCHEMA_VERSION, "metadata": self.metadata,
                    "signals": [asdict(s) for s in self.signals.values()], "files": self._files}
        with (self._temporary / "manifest.json").open("w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2, allow_nan=False, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(self._temporary, self.path)
        self._finished = True
        return SignalStore(self.path)
