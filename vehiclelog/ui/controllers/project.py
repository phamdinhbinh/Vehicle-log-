"""Chức năng: Lưu / mở cấu hình dự án và kiểm tra thay đổi chưa lưu.

Sửa tại đây khi: đổi hành vi lưu JSON, khôi phục cache hoặc chọn lại nguồn.
Liên kết: backend project.py quản lý định dạng; session.py đọc lại nguồn / DBC.
"""
# COMPONENT: ui.controllers.project
from __future__ import annotations

from pathlib import Path
from PySide6 import QtWidgets


class ProjectController:
    """Mixin chức năng của MainWindow, không khởi tạo độc lập.

    self.project / self.store và widget được main_window.py cùng panels/ cung cấp.
    Callback có thể gọi controller khác qua cùng self; backend giữ thuật toán dữ liệu.
    """

    def _confirm_discard(self):
        """Hỏi lưu thay đổi trước khi thay nguồn hoặc đóng cửa sổ."""
        if not self._dirty:
            return True
        answer = QtWidgets.QMessageBox.question(self, "Lưu thay đổi?", "Cấu hình hiện tại chưa được lưu. Bạn có muốn lưu trước khi tiếp tục?",
                    QtWidgets.QMessageBox.StandardButton.Save | QtWidgets.QMessageBox.StandardButton.Discard | QtWidgets.QMessageBox.StandardButton.Cancel,
                    QtWidgets.QMessageBox.StandardButton.Save)
        if answer == QtWidgets.QMessageBox.StandardButton.Cancel:
            return False
        if answer == QtWidgets.QMessageBox.StandardButton.Save:
            return bool(self.save_project())
        return True


    def save_project(self):
        """Lưu cấu hình dự án JSON; chỉ bỏ cờ thay đổi khi ghi thành công."""
        if self._worker:
            return False
        from ...project import save_project
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Lưu dự án", str(self._project_path or "vehicle-analysis.vlog.json"),
                                                       "Vehicle Log project (*.vlog.json *.json)")
        if not path:
            return False
        if not path.lower().endswith(".json"):
            path += ".vlog.json"
        try:
            save_project(self.project, path)
        except Exception as exc:
            self._notify("Không thể lưu dự án", str(exc))
            return False
        self._project_path = path
        self._dirty = False
        self.status_label.setText(f"Đã lưu dự án: {path}")
        return True


    def load_project(self):
        """Mở dự án; ưu tiên kiểm tra lại nguồn / DBC trước khi dùng cache."""
        if self._worker or not self._confirm_discard():
            return
        from ...project import load_project
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Mở dự án", "", "Vehicle Log project (*.vlog.json *.json)")
        if not path:
            return
        try:
            project = load_project(path)
        except Exception as exc:
            self._notify("Không thể mở dự án", str(exc))
            return
        self._project_path = path
        # Kiểm tra nguồn / DBC để tránh dùng cache cũ sau khi file thay đổi.
        if project.source and Path(project.source).is_file():
            self._import_source(project.source, {int(k): v for k,v in project.dbc_map.items()}, project)
        elif project.cache_path and Path(project.cache_path).is_dir():
            try:
                from ...store import SignalStore
                self.project = project
                self.project.results.clear()
                self.set_store(SignalStore(project.cache_path))
                self._dirty = False
                self.status_label.setText("Đã mở từ cache. Không tìm thấy file nguồn; xuất CAN thô cần chọn lại nguồn.")
            except Exception as exc:
                self._notify("Không thể mở cache", str(exc))
        else:
            source, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Không tìm thấy nguồn — chọn lại log", "", "Vehicle logs (*.blf *.mf4 *.mdf)")
            if source:
                project.source = source
                project.results.clear()
                self._import_source(source, {int(k): v for k,v in project.dbc_map.items()}, project)

