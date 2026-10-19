"""Chức năng: Điều phối trạng thái cửa sổ, kéo thả và đóng an toàn.

Sửa tại đây khi: đổi khóa nút khi bận, thông báo, hướng dẫn hoặc thao tác đóng cửa sổ.
Liên kết: main_window.py khởi tạo trạng thái; background.py và previews.py dọn thread.
"""
# COMPONENT: ui.controllers.window
from __future__ import annotations

from pathlib import Path
from PySide6 import QtWidgets
from ..dialogs.dbc import DbcDialog


class WindowController:
    """Mixin chức năng của MainWindow, không khởi tạo độc lập.

    self.project / self.store và widget được main_window.py cùng panels/ cung cấp.
    Callback có thể gọi controller khác qua cùng self; backend giữ thuật toán dữ liệu.
    """

    def _set_available(self):
        """Khóa thao tác sửa dữ liệu khi worker đang dùng cùng trạng thái dự án."""
        busy = self._worker is not None
        has_store = self.store is not None
        for widget in (self.open_button, self.demo_button, self.dbc_button, self.save_button):
            widget.setEnabled(not busy)
        for widget in (self.cursor_button, self.export_button, self.segment_add, self.segment_edit,
                       self.segment_delete, self.formula_add, self.formula_edit, self.formula_duplicate,
                       self.formula_delete, self.formula_plot, self.calculate_button, self.trace_button, self.delete_cursor_button,
                       self.cursor_color_button):
            widget.setEnabled(has_store and not busy)
        # Không cho sửa đầu vào khi tác vụ nền đang dùng dữ liệu dự án.
        for widget in (self.signal_list, self.cursor_table, self.segment_table, self.formula_table):
            widget.setEnabled(not busy)
        for lines in self.cursor_lines.values():
            for cursor_id, line in lines.items():
                cursor = next((c for c in self.project.cursors if c.id == cursor_id), None)
                line.setMovable(not busy and cursor is not None and not cursor.locked)
        self.cancel_button.setEnabled(busy)
        self.cancel_button.setVisible(busy)
        self.progress_bar.setVisible(busy)


    def _notify(self, title, message):
        """Hiển thị cảnh báo giao diện; không thay đổi dữ liệu nguồn."""
        QtWidgets.QMessageBox.warning(self, title, str(message))


    def _mark_changed(self):
        """Đánh dấu dự án đã sửa và xóa kết quả có thể đã hết hiệu lực."""
        self._dirty = True
        self.project.results.clear()
        self._refresh_results()


    def _refresh_tables(self):
        """Đồng bộ các bảng sau khi dữ liệu dự án hoặc store thay đổi."""
        self._refresh_cursors()
        self._refresh_segments()
        self._refresh_formulas()
        self._refresh_results()
        self._refresh_values()


    def show_help(self):
        """Hiện hướng dẫn các bước thao tác và phím tắt."""
        QtWidgets.QMessageBox.information(self, "Hướng dẫn nhanh",
            "1. Mở BLF và gán DBC cho từng kênh CAN, hoặc mở MF4.\n"
            "2. Tick tín hiệu bên trái. Zoom bằng chuột; kéo vùng timeline để đổi khoảng xem.\n"
            "3. Thêm con trỏ, kéo mốc hoặc sửa thời gian trong bảng bên phải.\n"
            "4. Tạo giai đoạn bằng hai mốc hoặc nhập thời gian trực tiếp.\n"
            "5. Tạo công thức: đặt tên, chọn tín hiệu / bí danh, biểu thức, đơn vị và tick giai đoạn.\n"
            "6. Tính kết quả, kiểm tra trạng thái dữ liệu; xuất Excel hoặc MF4.\n"
            "7. Lưu dự án để giữ bố cục, mốc, giai đoạn và công thức.\n\n"
            "Phím tắt: Ctrl+O mở log · Ctrl+S lưu dự án · Ctrl+E xuất.\n"
            "Demo là dữ liệu mô phỏng. Xác minh đơn vị, dấu dòng điện và sai số trước khi sử dụng kết quả.")


    def dragEnterEvent(self, event):
        """Chấp nhận kéo một file log có định dạng được hỗ trợ."""
        if not self._worker and event.mimeData().hasUrls():
            files = [url.toLocalFile() for url in event.mimeData().urls()]
            if len(files) == 1 and Path(files[0]).suffix.lower() in (".blf", ".mf4", ".mdf"):
                event.acceptProposedAction()


    def dropEvent(self, event):
        """Mở log được thả sau khi xử lý thay đổi chưa lưu và DBC."""
        if self._worker or not self._confirm_discard():
            return
        source = event.mimeData().urls()[0].toLocalFile()
        mapping = {int(k): v for k,v in self.project.dbc_map.items()}
        if Path(source).suffix.lower() == ".blf":
            dialog = DbcDialog(mapping, self)
            if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return
            mapping = dialog.mapping()
        self._import_source(source, mapping)
        event.acceptProposedAction()


    def closeEvent(self, event):
        """Chặn đóng khi job đang chạy, hủy preview trước khi thoát an toàn."""
        if self._worker:
            self._notify("Tác vụ đang chạy", "Hãy hủy tác vụ và chờ hoàn tất trước khi đóng ứng dụng.")
            event.ignore()
            return
        if not self._confirm_discard():
            event.ignore()
            return
        if self._preview_thread is not None:
            self._closing_after_preview = True
            self._dirty = False
            if self._preview_token:
                self._preview_token.cancel()
            self.status_label.setText("Đang đóng sau khi dừng tải đồ thị…")
            event.ignore()
            return
        event.accept()

