"""Chức năng: xuất tín hiệu gốc hoặc đồng bộ thời gian sang Excel theo từng phần.

Sửa tại đây khi: đổi cấu trúc dữ liệu Excel, raster, nội suy hoặc tiến độ xuất.
Liên kết: excel_sheets.py định dạng; excel_metadata.py báo cáo; atomic.py công bố file.
"""
# COMPONENT: writers.excel
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from ..models import report
from .atomic import _output
from .common import _check
from .selection import _keys, _scopes
from .excel_metadata import _metadata
from .excel_sheets import _Rows, _Sheets
from . import excel_sheets

CHUNK_SIZE = 50_000
RASTER_CHUNK_SIZE = 2_000

def export_excel(store, destination, keys=None, segments=None, formulas=None, results=None,
                 raster=None, interpolation="hold", max_gap=1.0, progress=None, token=None):
    """Xuất Excel theo mẫu gốc từng tín hiệu hoặc một trục thời gian chung.

    Giá trị thiếu/hỏng để trống; chế độ gốc có thêm cột Valid. Tín hiệu,
    giai đoạn, công thức và kết quả do người gọi chọn; không dùng dữ liệu
    rút gọn của đồ thị. File chỉ được công bố sau khi ghi xong.
    """
    import xlsxwriter
    if Path(destination).suffix.lower() != ".xlsx":
        raise ValueError("File Excel phải có phần mở rộng .xlsx.")
    selected = _keys(store, keys)
    scopes = _scopes(store, selected, segments)
    if interpolation not in {"hold", "linear"}:
        raise ValueError("Cách nội suy phải là hold hoặc linear.")
    if not math.isfinite(max_gap) or max_gap <= 0:
        raise ValueError("Khoảng mất mẫu tối đa phải lớn hơn 0.")
    if raster is not None and (not math.isfinite(raster) or raster <= 0):
        raise ValueError("Bước thời gian phải lớn hơn 0.")
    with _output(destination, store=store, token=token) as temporary:
        with xlsxwriter.Workbook(str(temporary), {"constant_memory": True, "strings_to_formulas": False,
                                                  "strings_to_urls": False}) as workbook:
            sheets = _Sheets(workbook)
            _metadata(sheets, store, selected, scopes, formulas, results, raster, interpolation, max_gap)
            if raster is None:
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
            else:
                from ..formulas import align_values
                # Raster nhiều tín hiệu chia ngang theo cột; _Rows chia theo hàng.
                width = max(1, excel_sheets.EXCEL_MAX_COLUMNS-3)
                blocks = [selected[i:i+width] for i in range(0, len(selected), width)]
                total = len(scopes)*len(blocks)
                complete = 0
                for scope in scopes:
                    count = max(1, int(math.floor((scope.end-scope.start)/raster+1e-9))+1)
                    for block_number, block in enumerate(blocks):
                        headers = ["Segment ID", "Segment", "Time_s"] + [f"{store.signals[k].name} [{store.signals[k].unit}] ({k})" for k in block]
                        rows = _Rows(sheets, f"Raster_{scope.name}_{block_number+1}", headers)
                        chunk_size = max(1, min(RASTER_CHUNK_SIZE, 1_000_000//len(block)))
                        for offset in range(0, count, chunk_size):
                            _check(token)
                            target = scope.start + np.arange(offset, min(offset+chunk_size, count), dtype=float)*raster
                            columns = []
                            for key in block:
                                _check(token)
                                times, values = store.read(key, start=float(target[0]), end=float(target[-1]), neighbors=True)
                                columns.append(align_values(times, values, target, interpolation=interpolation, max_gap=max_gap))
                            for i, timestamp in enumerate(target):
                                rows.write([scope.id, scope.name, float(timestamp)] + [float(col[i]) for col in columns])
                            report(progress, (complete+(offset+len(target))/count)/total, f"Đang xuất {scope.name}")
                        rows.finish()
                        complete += 1
    report(progress, 1.0, "Đã xuất Excel")
    return Path(destination).expanduser().resolve()
