"""Cấu trúc dữ liệu dùng chung giữa giao diện và xử lý log.

Chức năng: mô tả tín hiệu, con trỏ, giai đoạn, công thức, kết quả và project.
Sửa tại đây khi: thêm trường cấu hình; kiểm tra project.py nếu cần lưu JSON.
Liên kết: UI tạo/sửa các đối tượng này; readers/calculations/writers sử dụng.
"""
# COMPONENT: models
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Callable
import uuid


def new_id() -> str:
    """Tạo ID ngắn để liên kết con trỏ, giai đoạn và công thức trong project."""
    return uuid.uuid4().hex[:12]


class CancelledError(Exception):
    """Báo hủy tác vụ; caller dọn file tạm, không công bố kết quả chưa hoàn tất."""


class CancellationToken:
    """Cờ hủy an toàn giữa luồng giao diện và luồng đọc/tính/ghi."""
    def __init__(self):
        import threading
        self._event = threading.Event()

    def cancel(self):
        """UI yêu cầu hủy; worker dừng ở lần check tiếp theo."""
        self._event.set()

    def check(self):
        """Worker gọi giữa các khối để phản hồi yêu cầu hủy."""
        if self._event.is_set():
            raise CancelledError("Đã hủy tác vụ.")


Progress = Callable[[float, str], None]


def report(progress: Progress | None, fraction: float, message: str):
    """Gửi tiến độ trong [0, 1] cho GUI/CLI mà không phụ thuộc Qt."""
    if progress:
        progress(max(0.0, min(1.0, fraction)), message)


@dataclass
class SignalInfo:
    """Metadata của một tín hiệu; key phân biệt tên trùng giữa kênh/message."""
    key: str
    name: str
    unit: str = ""
    channel: str = ""
    message: str = ""
    can_id: int | None = None
    count: int = 0
    start: float = 0.0
    end: float = 0.0
    choices: dict = field(default_factory=dict)
    source: str = ""


@dataclass
class Cursor:
    """Mốc thời gian trên đồ thị, thời gian tương đối của log tính bằng giây."""
    name: str
    time: float
    color: str = "#efb04c"
    locked: bool = False
    id: str = field(default_factory=new_id)


@dataclass
class Segment:
    """Khoảng phân tích [start, end] theo giây; có thể liên kết hai con trỏ."""
    name: str
    start: float
    end: float
    color: str = "#4488cc"
    id: str = field(default_factory=new_id)
    start_cursor: str | None = None
    end_cursor: str | None = None

    def validate(self):
        """Từ chối timestamp không hữu hạn hoặc khoảng có thời lượng <= 0."""
        import math
        if not math.isfinite(self.start) or not math.isfinite(self.end) or self.end <= self.start:
            raise ValueError("Giai đoạn phải có thời điểm kết thúc lớn hơn bắt đầu.")


@dataclass
class Formula:
    """Công thức do người dùng đặt tên và gán cho các giai đoạn cụ thể.

    bindings: bí danh trong biểu thức → signal key; segment_ids rỗng là chưa gán.
    interpolation: hold/linear; max_gap là ngưỡng mất mẫu tính bằng giây.
    """
    name: str
    expression: str
    bindings: dict[str, str]
    unit: str = ""
    segment_ids: list[str] = field(default_factory=list)
    interpolation: str = "hold"
    max_gap: float = 1.0
    id: str = field(default_factory=new_id)


@dataclass
class FormulaResult:
    """Kết quả một cặp công thức–giai đoạn, gồm trạng thái và độ phủ [0, 1]."""
    formula_id: str
    formula_name: str
    segment_id: str
    segment_name: str
    value: float | None
    unit: str
    status: str = "ok"
    message: str = ""
    coverage: float = 1.0


@dataclass
class Project:
    """Cấu hình phiên làm việc; không nhúng toàn bộ log hay DBC vào JSON."""
    source: str = ""
    dbc_map: dict[str, str] = field(default_factory=dict)
    selected_signals: list[str] = field(default_factory=list)
    cursors: list[Cursor] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    formulas: list[Formula] = field(default_factory=list)
    results: list[FormulaResult] = field(default_factory=list)
    cache_path: str = ""
    schema_version: int = 1

    def to_dict(self):
        """Chuyển dataclass lồng nhau thành dữ liệu JSON cho project.save_project."""
        return asdict(self)
