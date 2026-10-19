"""Chức năng: Các hàm tạo label, nút, bảng và ô thời gian dùng chung.

Sửa tại đây khi: đổi mặc định của widget lặp lại trên nhiều màn hình.
Liên kết: panels/ và dialogs/ sử dụng các hàm này; không chứa logic xử lý log.
"""
# COMPONENT: ui.widgets
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

Qt = QtCore.Qt

def label(text, role=None):
    """Tạo nhãn; role nối với selector trong theme.STYLE như title hoặc muted."""
    obj = QtWidgets.QLabel(text)
    if role:
        obj.setObjectName(role)
    return obj


def button(text, callback=None, primary=False):
    """Tạo nút và nối callback; primary dùng màu nhấn của stylesheet."""
    obj = QtWidgets.QPushButton(text)
    if primary:
        obj.setObjectName("primary")
    if callback:
        obj.clicked.connect(callback)
    return obj


def table(headers):
    """Tạo bảng chọn theo hàng, ẩn số hàng và giãn cột cuối mặc định."""
    obj = QtWidgets.QTableWidget(0, len(headers))
    obj.setHorizontalHeaderLabels(headers)
    obj.verticalHeader().hide()
    obj.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    obj.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
    obj.setAlternatingRowColors(True)
    obj.horizontalHeader().setStretchLastSection(True)
    return obj


def fill_table(widget, rows):
    """Nạp dữ liệu chỉ đọc vào bảng; bảng con trỏ tự xử lý ô có thể sửa."""
    widget.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            item = QtWidgets.QTableWidgetItem(str(value))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            widget.setItem(r, c, item)
    widget.resizeColumnsToContents()


def time_spin(value=0.0):
    """Tạo ô nhập thời gian giây với độ chính xác sáu chữ số thập phân."""
    obj = QtWidgets.QDoubleSpinBox()
    obj.setRange(0, 1e12)
    obj.setDecimals(6)
    obj.setSuffix(" s")
    obj.setValue(value)
    return obj


