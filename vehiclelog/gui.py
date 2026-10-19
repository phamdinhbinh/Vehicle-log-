"""Chức năng: giữ API giao diện cũ sau khi chia thành các component.

Sửa tại đây khi: cần bổ sung tên export công khai; không đặt bố cục hoặc logic mới ở đây.
Liên kết: ui/main_window.py ghép cửa sổ; ui/panels/ dựng bố cục;
ui/controllers/ xử lý thao tác; ui/dialogs/ chứa từng cửa sổ nhập liệu.
"""
# COMPONENT: ui.compatibility
from .ui.app import run_app
from .ui.main_window import MainWindow
from .ui.dialogs.dbc import DbcDialog
from .ui.dialogs.segment import SegmentDialog
from .ui.dialogs.formula import FormulaDialog
from .ui.dialogs.export import ExportDialog
from .ui.workers import TaskWorker
from .ui.trace_preview import trace_preview
from .ui.theme import COLORS, STYLE
from .ui.widgets import label, button, table, fill_table, time_spin

__all__ = [
    "run_app", "MainWindow", "DbcDialog", "SegmentDialog", "FormulaDialog",
    "ExportDialog", "TaskWorker", "trace_preview", "COLORS", "STYLE",
    "label", "button", "table", "fill_table", "time_spin",
]
