"""Chức năng: Điều phối xuất Excel hoặc MF4 từ lựa chọn giao diện.

Sửa tại đây khi: đổi hộp thoại lưu, ánh xạ tùy chọn hoặc thông báo hoàn tất xuất.
Liên kết: dialogs/export.py cấu hình; backend exports.py ghi dữ liệu; background.py chạy tác vụ.
"""
# COMPONENT: ui.controllers.exports
from __future__ import annotations

from pathlib import Path
from PySide6 import QtWidgets
from ..dialogs.export import ExportDialog


class ExportsController:
    """Mixin chức năng của MainWindow, không khởi tạo độc lập.

    self.project / self.store và widget được main_window.py cùng panels/ cung cấp.
    Callback có thể gọi controller khác qua cùng self; backend giữ thuật toán dữ liệu.
    """

    def export_data(self):
        """Thu thập tùy chọn xuất, kiểm tra đầu ra và gọi API export ở nền."""
        if not self.store or self._worker:
            return
        dialog = ExportDialog(self.store, self.project, self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        kind = dialog.format_combo.currentData()
        extension = ".xlsx" if kind == "excel" else ".mf4"
        suggestion = str(Path(self.project.source).with_suffix("")) + "_export" + extension if self.project.source else "export" + extension
        destination, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Xuất dữ liệu", suggestion,
                        "Excel (*.xlsx)" if kind == "excel" else "Measurement data (*.mf4)")
        if not destination:
            return
        if not destination.lower().endswith(extension):
            destination += extension
        if Path(destination).exists():
            self._notify("File đã tồn tại", "Hãy chọn tên file mới. Ứng dụng không ghi đè file có sẵn.")
            return
        keys = dialog.checked(dialog.signal_list)
        segments = dialog.selected_segments()
        if segments is not None:
            try:
                for segment in segments:
                    segment.validate()
            except ValueError as exc:
                self._notify("Giai đoạn chưa hợp lệ", str(exc))
                return
        from ...exports import export_excel, export_mf4, export_raw_mf4
        zero_time, include_derived = dialog.zero_check.isChecked(), dialog.derived_check.isChecked()
        store, project = self.store, self.project
        mapping = {int(k): v for k, v in project.dbc_map.items()}
        def work(progress, token):
            common = {"segments": segments, "progress": progress, "token": token}
            if kind == "excel":
                return export_excel(store, destination, keys=keys, formulas=project.formulas,
                                    results=project.results, **common)
            if kind == "mf4":
                return export_mf4(store, destination, keys=keys, zero_time=zero_time,
                                  formulas=project.formulas if include_derived else None, **common)
            return export_raw_mf4(project.source, destination, dbc_map=mapping, zero_time=zero_time, **common)
        self._run_task("Đang xuất dữ liệu…", work, lambda path: self.status_label.setText(f"Đã xuất: {path}"))

