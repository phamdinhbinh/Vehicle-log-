"""Chức năng: ghi các bảng Summary, Signals, Segments, Formulas và Results.

Sửa tại đây khi: thêm cột metadata, đổi tiêu đề hoặc bố cục báo cáo kết quả.
Liên kết: excel.py gọi _metadata; excel_sheets.py lo định dạng và chia sheet.
"""
# COMPONENT: writers.excel_metadata
from __future__ import annotations

from datetime import datetime, timezone

from .common import _json
from .excel_sheets import _Rows

def _metadata(sheets, store, keys, scopes, formulas, results, raster, interpolation, max_gap):
    """Ghi nguồn dữ liệu, tín hiệu, giai đoạn, định nghĩa công thức và kết quả.

    Sửa danh sách tiêu đề và rows.write tương ứng khi thêm cột báo cáo.
    Hàm chỉ ghi metadata, không tự tính lại kết quả công thức.
    """
    rows = _Rows(sheets, "Summary", ["Property", "Value"])
    for key, value in store.metadata.items():
        rows.write([str(key), value if isinstance(value, (str, int, float, bool)) else _json(value)])
    for key, value in {"exported_utc": datetime.now(timezone.utc).isoformat(),
                       "time_basis": "seconds relative to source log origin",
                       "layout": "native per signal" if raster is None else "raster",
                       "raster_s": raster, "interpolation": interpolation, "max_gap_s": max_gap,
                       "missing_data": "blank values; native Valid column marks invalid samples"}.items():
        rows.write([key, value])
    rows.finish()
    rows = _Rows(sheets, "Signals", ["Key", "Name", "Unit", "CAN channel", "Message", "CAN ID", "Source samples", "Source"])
    for key in keys:
        info = store.signals[key]
        rows.write([key, info.name, info.unit, info.channel, info.message, info.can_id, info.count, info.source])
    rows.finish()
    rows = _Rows(sheets, "Segments", ["ID", "Name", "Start_s", "End_s", "Duration_s"])
    for scope in scopes:
        rows.write([scope.id, scope.name, scope.start, scope.end, scope.end-scope.start])
    rows.finish()
    rows = _Rows(sheets, "Formulas", ["ID", "Name", "Expression", "Bindings", "Unit", "Segment IDs", "Interpolation", "Max gap_s"])
    for formula in formulas or []:
        rows.write([formula.id, formula.name, formula.expression, _json(formula.bindings), formula.unit,
                    _json(formula.segment_ids), formula.interpolation, formula.max_gap])
    rows.finish()
    rows = _Rows(sheets, "Results", ["Segment ID", "Segment", "Formula ID", "Formula", "Value", "Unit", "Status", "Coverage", "Message"])
    for result in results or []:
        rows.write([result.segment_id, result.segment_name, result.formula_id, result.formula_name,
                    result.value, result.unit, result.status, result.coverage, result.message])
    rows.finish()
