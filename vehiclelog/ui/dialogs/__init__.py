"""Các hộp thoại nhập cấu hình của Vehicle Log Studio.

Chức năng: cung cấp điểm import ổn định cho bốn hộp thoại theo từng nghiệp vụ.
Sửa tại đây khi: thêm hoặc đổi tên hộp thoại công khai.
Liên kết: dbc.py, segment.py, formula.py, export.py chứa giao diện chi tiết.
"""
# COMPONENT: ui.dialogs.__init__
from .dbc import DbcDialog
from .segment import SegmentDialog
from .formula import FormulaDialog
from .export import ExportDialog

__all__ = ["DbcDialog", "SegmentDialog", "FormulaDialog", "ExportDialog"]
