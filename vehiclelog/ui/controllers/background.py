"""Chức năng: Vòng đời tác vụ nền, tiến độ và hủy.

Sửa tại đây khi: đổi quy tắc chạy / dọn worker hoặc cập nhật tiến độ.
Liên kết: ../workers.py chạy tác vụ; các controller khác gọi _run_task.
"""
# COMPONENT: ui.controllers.background
from __future__ import annotations

from PySide6 import QtCore
from ...models import CancellationToken
from ..workers import TaskWorker


class BackgroundController:
    """Mixin chức năng của MainWindow, không khởi tạo độc lập.

    self.project / self.store và widget được main_window.py cùng panels/ cung cấp.
    Callback có thể gọi controller khác qua cùng self; backend giữ thuật toán dữ liệu.
    """

    def _run_task(self, title, function, callback=None):
        """Chạy hàm nặng trên QThread; giữ tham chiếu tới khi thread dừng hẳn."""
        if self._worker is not None:
            self.status_label.setText("Đang có tác vụ chạy.")
            return
        self._token = CancellationToken()
        self._pending_result = None
        self._job_failed = False
        self._job_callback = callback
        self._thread = QtCore.QThread(self)
        self._worker = TaskWorker(function, self._token)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._task_progress)
        self._worker.finished.connect(self._task_finished)
        self._worker.failed.connect(self._task_error)
        self._worker.cancelled.connect(self._task_cancelled)
        self._worker.done.connect(self._thread.quit)
        self._worker.done.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._task_cleanup)
        self.progress_bar.setValue(0)
        self.status_label.setText(title)
        self._set_available()
        self._thread.start()


    @QtCore.Slot(float, str)
    def _task_progress(self, fraction, message):
        """Nhận tiến độ từ worker và cập nhật widget trên GUI thread."""
        self.progress_bar.setValue(int(max(0.0, min(1.0, fraction)) * 1000))
        self.status_label.setText(message)


    @QtCore.Slot(object)
    def _task_finished(self, result):
        """Giữ kết quả; callback chỉ được gọi sau khi worker đã kết thúc."""
        self._pending_result = result


    @QtCore.Slot(str)
    def _task_error(self, message):
        """Ghi trạng thái thất bại và hiển thị lỗi do worker trả về."""
        self._job_failed = True
        self.status_label.setText("Tác vụ thất bại — xem thông báo lỗi")
        self._notify("Không thể hoàn tất", message)


    def _task_cancelled(self):
        """Ghi nhận worker đã dừng theo yêu cầu hủy."""
        self._job_failed = True
        self.status_label.setText("Đã hủy tác vụ")


    @QtCore.Slot()
    def _task_cleanup(self):
        """Dọn thread trước khi gọi callback, tránh đóng GUI khi thread còn chạy."""
        callback, result, failed = self._job_callback, self._pending_result, self._job_failed
        thread = self._thread
        self._worker = None
        self._thread = None
        self._token = None
        self._job_callback = None
        self._pending_result = None
        if thread:
            thread.deleteLater()
        self._set_available()
        if not failed:
            self.status_label.setText("Hoàn tất")
            if callback:
                try:
                    callback(result)
                except Exception as exc:
                    self._notify("Không thể cập nhật giao diện", str(exc))
        elif self._loading_project is not None:
            self._loading_project = None


    def cancel_task(self):
        """Gửi tín hiệu hủy hợp tác; worker dừng tại điểm kiểm tra token kế tiếp."""
        if self._token:
            self._token.cancel()
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Đang hủy an toàn, vui lòng chờ…")

