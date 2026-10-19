"""Chức năng: xuất từng tín hiệu sang Excel, giữ timestamp và mẫu gốc.

Sửa tại đây khi: đổi cấu trúc dữ liệu Excel, chia khối hoặc tiến độ xuất.
Liên kết: excel_sheets.py định dạng; excel_metadata.py báo cáo; atomic.py công bố file.
"""
# COMPONENT: writers.excel
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..models import report
from .atomic import _output
from .common import _check
from .selection import _keys, _scopes
from .excel_metadata import _metadata
from .excel_sheets import _Rows, _Sheets

CHUNK_SIZE = 50_000

def export_excel(store, destination, keys=None, segments=None, formulas=None, results=None,
                 progress=None, token=None):
    """Xuất từng tín hiệu theo timestamp gốc; không nội suy hoặc đổi bước lấy mẫu.

    Giá trị thiếu/hỏng để trống; chế độ gốc có thêm cột Valid. Tín hiệu,
    giai đoạn, công thức và kết quả do người gọi chọn; không dùng dữ liệu
    rút gọn của đồ thị. File chỉ được công bố sau khi ghi xong.
    """
    import xlsxwriter
    if Path(destination).suffix.lower() != ".xlsx":
        raise ValueError("File Excel phải có phần mở rộng .xlsx.")
    selected = _keys(store, keys)
    scopes = _scopes(store, selected, segments)
    with _output(destination, store=store, token=token) as temporary:
        with xlsxwriter.Workbook(str(temporary), {"constant_memory": True, "strings_to_formulas": False,
                                                  "strings_to_urls": False}) as workbook:
            sheets = _Sheets(workbook)
            _metadata(sheets, store, selected, scopes, formulas, results)
            for index, key in enumerate(selected):
                info = store.signals[key]
                rows = _Rows(sheets, f"Data_{info.name}", ["Segment ID", "Segment", "Time_s", "Value", "Valid", "Unit"])
                for scope in scopes:
                    for times, values in store.iter_chunks(key, start=scope.start, end=scope.end, chunk_size=CHUNK_SIZE):
                        _check(token)
                        for timestamp, value in zip(times, values):
                            rows.write([scope.id, scope.name, float(timestamp), float(value), bool(np.isfinite(value)), info.unit])
                rows.finish()
                report(progress, (index+1)/len(selected), f"Đã xuất tín hiệu {info.name}")
    report(progress, 1.0, "Đã xuất Excel")
    return Path(destination).expanduser().resolve()
