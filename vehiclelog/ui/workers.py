"""Chức năng: Worker Qt dùng chung cho đọc log, tính công thức, xuất file và preview.

Sửa tại đây khi: đổi cách truyền tiến độ, hủy tác vụ hoặc báo lỗi từ thread nền.
Liên kết: controllers/background.py và controllers/previews.py quản lý vòng đời thread.
"""
# COMPONENT: ui.workers
from __future__ import annotations

from typing import Callable
from PySide6 import QtCore
from ..models import CancellationToken, CancelledError

class TaskWorker(QtCore.QObject):
    """Chạy một hàm nặng và gửi kết quả / lỗi / tiến độ về GUI bằng signal."""
    progress = QtCore.Signal(float, str)
    finished = QtCore.Signal(object)
    failed = QtCore.Signal(str)
    cancelled = QtCore.Signal()
    done = QtCore.Signal()

    def __init__(self, function: Callable, token: CancellationToken):
        super().__init__()
        self.function = function
        self.token = token

    @QtCore.Slot()
    def run(self):
        """Luôn phát done để thread được dọn kể cả khi lỗi hoặc hủy."""
        try:
            result = self.function(self.progress.emit, self.token)
            self.finished.emit(result)
        except CancelledError:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self.done.emit()


class GuiTaskRelay(QtCore.QObject):
    """Đầu nhận thật sự thuộc GUI thread, kể cả controller dùng Python mixin.

    @Slot trong một mixin không phải QObject không bảo đảm đăng ký đúng với
    meta-object của PySide. Worker luôn nối queued vào QObject này; callback
    controller chỉ được gọi tại GUI thread, không chạm widget từ worker.
    """

    def __init__(self, parent, *, progress=None, result=None, error=None, cancelled=None, cleanup=None):
        super().__init__(parent)
        self.callbacks = dict(progress=progress, result=result, error=error, cancelled=cancelled, cleanup=cleanup)

    @QtCore.Slot(float, str)
    def progress(self, fraction, message):
        callback = self.callbacks['progress']
        if callback:
            callback(fraction, message)

    @QtCore.Slot(object)
    def result(self, value):
        callback = self.callbacks['result']
        if callback:
            callback(value)

    @QtCore.Slot(str)
    def error(self, message):
        callback = self.callbacks['error']
        if callback:
            callback(message)

    @QtCore.Slot()
    def cancelled(self):
        callback = self.callbacks['cancelled']
        if callback:
            callback()

    @QtCore.Slot()
    def cleanup(self):
        callback = self.callbacks['cleanup']
        if callback:
            callback()

