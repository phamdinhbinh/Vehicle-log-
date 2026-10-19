"""Chức năng: tạo tên sheet hợp lệ, định dạng và ghi từng hàng có chia sheet.

Sửa tại đây khi: đổi giao diện workbook, giới hạn hàng/cột hoặc làm sạch ô.
Liên kết: excel.py ghi dữ liệu; excel_metadata.py ghi các bảng mô tả.
"""
# COMPONENT: writers.excel_sheets
from __future__ import annotations

import math
import re

import numpy as np

EXCEL_MAX_ROWS = 1_048_576
EXCEL_MAX_COLUMNS = 16_384

class _Sheets:
    """Quản lý tên sheet duy nhất và định dạng tiêu đề dùng chung."""

    def __init__(self, workbook):
        self.workbook = workbook
        self.names = set()
        self.header_format = workbook.add_format({"bold": True, "bg_color": "#18334B", "font_color": "white"})

    def create(self, name, headers):
        """Tạo sheet có tên hợp lệ, cố định tiêu đề và đặt độ rộng cột."""
        base = re.sub(r"[\[\]:*?/\\]", "_", name).strip("'") or "Data"
        base = base[:31]
        name, suffix = base, 1
        while name.casefold() in self.names:
            suffix += 1
            tail = f"_{suffix}"
            name = base[:31-len(tail)] + tail
        self.names.add(name.casefold())
        sheet = self.workbook.add_worksheet(name)
        sheet.freeze_panes(1, 0)
        sheet.write_row(0, 0, headers, self.header_format)
        sheet.set_column(0, min(len(headers)-1, EXCEL_MAX_COLUMNS-1), 20)
        return sheet

class _Rows:
    """Ghi từng hàng và tự chia sheet khi chạm giới hạn Excel.

    Bất biến: luôn hoàn tất hàng trước khi ghi hàng kế tiếp; chế độ
    constant_memory của xlsxwriter không hỗ trợ quay lại hàng đã ghi.
    """
    def __init__(self, sheets, name, headers):
        self.sheets, self.name, self.headers = sheets, name, headers
        self.sheet = None
        self.row = 1
        self.parts = 0
        self._next()

    def _next(self):
        """Chốt bộ lọc sheet hiện tại rồi tạo phần dữ liệu kế tiếp."""
        if self.sheet is not None:
            self.sheet.autofilter(0, 0, self.row-1, len(self.headers)-1)
        self.parts += 1
        self.sheet = self.sheets.create(self.name if self.parts == 1 else f"{self.name}_{self.parts}", self.headers)
        self.row = 1

    def write(self, cells):
        """Ghi một hàng; ô NaN/inf thành trống, chuỗi giữ trong giới hạn Excel."""
        if self.row >= EXCEL_MAX_ROWS:
            self._next()
        safe = []
        for value in cells:
            if isinstance(value, (np.integer, np.floating)):
                value = value.item()
            if isinstance(value, float) and not math.isfinite(value):
                value = None
            elif isinstance(value, str):
                value = value[:32767]
            safe.append(value)
        self.sheet.write_row(self.row, 0, safe)
        self.row += 1

    def finish(self):
        """Đặt bộ lọc đến hàng cuối cùng sau khi hoàn tất nhóm dữ liệu."""
        self.sheet.autofilter(0, 0, self.row-1, len(self.headers)-1)
