"""Chức năng: Tải và cache dữ liệu đồ thị theo vùng xem, có worker cho tín hiệu lớn.

Sửa tại đây khi: đổi giới hạn cache, số điểm hoặc cách lên lịch tải preview.
Liên kết: plots.py gọi cập nhật; store.plot_data trả min/max; không dùng preview để tính / xuất.
"""
# COMPONENT: ui.controllers.previews
from __future__ import annotations

from PySide6 import QtCore
from ...models import CancellationToken
from ..workers import TaskWorker


class PreviewsController:
    """Mixin chức năng của MainWindow, không khởi tạo độc lập.

    self.project / self.store và widget được main_window.py cùng panels/ cung cấp.
    Callback có thể gọi controller khác qua cùng self; backend giữ thuật toán dữ liệu.
    """

    def _preview_key(self, key, start, end, points):
        """Tạo khóa cache theo nguồn, tín hiệu, khoảng xem và số điểm hiển thị."""
        return (str(self.store.path), key, start, end, points)


    def _remember_preview(self, request, data):
        """Lưu cache LRU giới hạn 160 mục để giữ bộ nhớ đồ thị có giới hạn."""
        self._preview_cache[request] = data
        self._preview_cache.move_to_end(request)
        while len(self._preview_cache) > 160:
            self._preview_cache.popitem(last=False)


    def _update_curves(self):
        """Dùng cache hoặc lên lịch tải preview; dữ liệu này chỉ phục vụ hiển thị."""
        if not self.store or not self.plots:
            return
        start, end = next(iter(self.plots.values())).viewRange()[0]
        # Làm tròn khóa để không đọc lại ổ đĩa vì dịch chuyển nhỏ hơn một pixel.
        start, end = round(start, 7), round(end, 7)
        self.range_label.setText(f"{start:,.3f} → {end:,.3f} s")
        requests = []
        for key, curve in self.curves.items():
            request = self._preview_key(key, start, end, 4000)
            if request in self._preview_cache:
                times, values = self._preview_cache[request]
                curve.setData(times, values, connect="finite")
            elif self.store.signals[key].count <= 100_000:
                # Tín hiệu nhỏ có thể đọc ngay; tín hiệu lớn chuyển sang worker nền.
                data = self.store.plot_data(key, start=start, end=end, max_points=4000)
                self._remember_preview(request, data)
                curve.setData(*data, connect="finite")
            elif request not in self._preview_errors:
                requests.append(request)
        if self._overview_key is not None:
            request = self._preview_key(self._overview_key, None, None, 1800)
            if request not in self._preview_cache:
                if self.store.signals[self._overview_key].count <= 100_000:
                    self._remember_preview(request, self.store.plot_data(self._overview_key, max_points=1800))
                elif request not in self._preview_errors:
                    requests.append(request)
            if request in self._preview_cache:
                self.overview_curve.setData(*self._preview_cache[request], connect="finite")
        if requests:
            self._queue_previews(self.store, requests)


    def _queue_previews(self, store, requests):
        """Tải preview lớn trên QThread riêng, gộp yêu cầu mới khi đang bận."""
        if self._closing_after_preview:
            return
        if self._preview_thread is not None:
            self._preview_pending = (store, requests)
            return
        self._preview_result = None
        self._preview_failed_requests = requests
        self._preview_token = CancellationToken()
        self._preview_thread = QtCore.QThread(self)
        def work(progress, token):
            result = []
            for request in requests:
                token.check()
                _, key, start, end, count = request
                data = store.plot_data(key, start=start, end=end, max_points=count)
                result.append((request, data))
            return result
        self._preview_worker = TaskWorker(work, self._preview_token)
        self._preview_worker.moveToThread(self._preview_thread)
        self._preview_thread.started.connect(self._preview_worker.run)
        self._preview_worker.finished.connect(self._preview_received)
        self._preview_worker.failed.connect(self._preview_error)
        self._preview_worker.done.connect(self._preview_thread.quit)
        self._preview_worker.done.connect(self._preview_worker.deleteLater)
        self._preview_thread.finished.connect(self._preview_cleanup)
        self._preview_thread.start()


    def _preview_received(self, result):
        """Giữ kết quả preview chờ thread kết thúc trước khi cập nhật đồ thị."""
        self._preview_result = result


    def _preview_error(self, message):
        """Ghi nhận yêu cầu lỗi để không lặp vô hạn khi làm mới đồ thị."""
        self._preview_errors.update(self._preview_failed_requests)
        self.status_label.setText(f"Lỗi tải đồ thị: {message}")


    def _preview_cleanup(self):
        """Bỏ kết quả của nguồn cũ, dọn thread và chạy yêu cầu xem mới nhất."""
        if self._preview_result:
            for request, data in self._preview_result:
                if self.store and request[0] == str(self.store.path):
                    self._remember_preview(request, data)
        thread = self._preview_thread
        self._preview_worker = None
        self._preview_thread = None
        self._preview_token = None
        self._preview_result = None
        if thread:
            thread.deleteLater()
        if self._closing_after_preview:
            self._preview_pending = None
            self.close()
            return
        pending = self._preview_pending
        self._preview_pending = None
        if pending and self.store and pending[0].path == self.store.path:
            requests = [request for request in pending[1] if request not in self._preview_cache and request not in self._preview_errors]
            if requests:
                self._queue_previews(pending[0], requests)
        self._update_curves()

