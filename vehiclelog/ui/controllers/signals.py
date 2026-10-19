"""Chức năng: Tìm kiếm và chọn tín hiệu hiển thị.

Sửa tại đây khi: đổi quy tắc lọc hoặc thao tác tick / bỏ chọn tín hiệu.
Liên kết: panels/signals.py dựng widget; plots.py dựng lại đồ thị sau thay đổi.
"""
# COMPONENT: ui.controllers.signals
from __future__ import annotations

from PySide6 import QtCore

Qt = QtCore.Qt


class SignalsController:
    """Mixin chức năng của MainWindow, không khởi tạo độc lập.

    self.project / self.store và widget được main_window.py cùng panels/ cung cấp.
    Callback có thể gọi controller khác qua cùng self; backend giữ thuật toán dữ liệu.
    """

    def _filter_signals(self, *_):
        """Lọc danh sách hiển thị theo tên, ID, message và kênh; không xóa dữ liệu."""
        search = self.search_edit.text().strip().casefold()
        for i in range(self.signal_list.count()):
            item = self.signal_list.item(i)
            item.setHidden(search not in str(item.data(Qt.ItemDataRole.UserRole + 1)).casefold())


    def _signal_changed(self, *_):
        """Lưu tín hiệu đã tick vào dự án rồi dựng lại đồ thị."""
        self.project.selected_signals = [self.signal_list.item(i).data(Qt.ItemDataRole.UserRole)
                                        for i in range(self.signal_list.count())
                                        if self.signal_list.item(i).checkState() == Qt.CheckState.Checked]
        self._dirty = True
        self._rebuild_plots()


    def clear_selection(self):
        """Bỏ tick hàng loạt và chỉ phát một lần cập nhật đồ thị."""
        self.signal_list.blockSignals(True)
        for i in range(self.signal_list.count()):
            self.signal_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.signal_list.blockSignals(False)
        self._signal_changed()

