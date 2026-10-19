"""Chức năng: xuất MF4 tín hiệu đã giải mã và tín hiệu công thức được gán giai đoạn.

Sửa tại đây khi: đổi nhóm tín hiệu MF4, invalidation bits hoặc mốc thời gian đầu ra.
Liên kết: selection.py phạm vi/nguồn gốc; common.py ghi MF4; atomic.py chống ghi đè.
"""
# COMPONENT: writers.mf4
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np

from ..models import report
from .atomic import _output
from .common import _check, _json, _save_mf4, _set_start_time
from .selection import _keys, _scopes, _provenance

CHUNK_SIZE = 50_000

def export_mf4(store, destination, keys=None, segments=None, zero_time=False, progress=None,
               token=None, formulas=None):
    """Xuất tín hiệu gốc và chuỗi công thức vào các group MF4 theo giai đoạn.

    Chỉ thêm công thức dạng chuỗi vào giai đoạn được gán trong segment_ids;
    công thức tổng hợp thuộc báo cáo kết quả Excel. Xuất toàn log mặc định
    không mở rộng phạm vi áp dụng công thức. Giữ timestamp nguồn trừ khi
    người gọi chọn zero_time, khi đó trừ đúng thời điểm bắt đầu giai đoạn.
    """
    from asammdf import MDF, Signal
    if Path(destination).suffix.lower() != ".mf4":
        raise ValueError("File MDF4 phải có phần mở rộng .mf4.")
    selected = _keys(store, keys)
    scopes = _scopes(store, selected, segments)
    with _output(destination, store=store, token=token) as temporary:
        with MDF(version="4.10") as mdf:
            _set_start_time(mdf, store.metadata)
            derived = []
            if formulas and segments:
                from ..formulas import formula_kind, iter_evaluate_trace
                derived = [(formula, scope) for formula in formulas for scope in scopes
                           if scope.id in formula.segment_ids and formula_kind(formula) == "trace"]
            groups_written = 0
            total = len(scopes)*len(selected)+len(derived)
            for scope_number, scope in enumerate(scopes):
                for key_number, key in enumerate(selected):
                    info = store.signals[key]
                    group = None
                    for times, values in store.iter_chunks(key, start=scope.start, end=scope.end, chunk_size=CHUNK_SIZE):
                        _check(token)
                        if not len(times):
                            continue
                        times = np.asarray(times, dtype=np.float64)
                        values = np.asarray(values, dtype=np.float64)
                        if zero_time:
                            # Offset là đầu giai đoạn, không phải mẫu đầu tìm được.
                            times = times - scope.start
                        # Giữ mẫu NaN/inf và cờ invalidity, không biến thành số 0.
                        invalid = ~np.isfinite(values)
                        if group is None:
                            signal = Signal(values, times, name=info.name, unit=info.unit,
                                            invalidation_bits=invalid,
                                            comment=_json({"signal_key": key, "segment_id": scope.id,
                                                           "can_channel": info.channel, "message": info.message}))
                            group = mdf.append([signal], common_timebase=True,
                                               comment=_provenance(store, scope, zero_time=zero_time))
                            groups_written += 1
                        else:
                            mdf.extend(group, [(times, None), (values, invalid)])
                    report(progress, (scope_number*len(selected)+key_number+1)/total*0.9,
                           f"Đã chuẩn bị MF4: {scope.name} / {info.name}")
            for index, (formula, scope) in enumerate(derived):
                group = None
                for times, values in iter_evaluate_trace(store, formula, scope, token=token):
                    _check(token)
                    if not len(times):
                        continue
                    times = np.asarray(times, dtype=np.float64)
                    values = np.asarray(values, dtype=np.float64)
                    if zero_time:
                        times = times-scope.start
                    # Quy tắc invalidity giống tín hiệu gốc, kể cả chuỗi công thức.
                    invalid = ~np.isfinite(values)
                    if group is None:
                        signal = Signal(values, times, name=formula.name, unit=formula.unit,
                                        invalidation_bits=invalid,
                                        comment=_json({"formula": asdict(formula), "segment_id": scope.id}))
                        group = mdf.append([signal], common_timebase=True,
                                           comment=_provenance(store, scope, zero_time=zero_time))
                        groups_written += 1
                    else:
                        mdf.extend(group, [(times, None), (values, invalid)])
                report(progress, (len(scopes)*len(selected)+index+1)/total*0.9,
                       f"Đã chuẩn bị công thức MF4: {scope.name} / {formula.name}")
            if not groups_written:
                raise ValueError("Không có mẫu dữ liệu trong phạm vi đã chọn.")
            _check(token)
            _save_mf4(mdf, temporary, progress, token)
    report(progress, 1.0, "Đã xuất MF4")
    return Path(destination).expanduser().resolve()
