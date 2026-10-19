"""Chức năng: tính chuỗi tín hiệu theo công thức để vẽ hoặc xuất tuần tự.

Sửa tại đây khi: đổi cách chèn NaN cho khoảng lỗi, ghép chunk hoặc tạo trace hoàn chỉnh.
Liên kết: engine.py tính scalar riêng; timeline.py sinh chunk; context.py căn dữ liệu; domains.py kiểm tra miền.
"""
from __future__ import annotations

# COMPONENT: calculations.traces

import numpy as np

from . import timeline
from .common import check_cancelled
from .context import prepare_context, point_values, interval_environment
from .domains import invalid_domains
from .interval_splits import split_transition_times
from .syntax import aggregate_calls


def iter_evaluate_trace(store, formula, segment, token=None):
    """Sinh chunk (timestamp giây, giá trị) và chèn NaN ở khoảng mất/lỗi dữ liệu.

    Dùng cho xuất dữ liệu lớn; bỏ điểm biên trùng giữa hai chunk kế tiếp.
    Chỉ chấp nhận biểu thức chuỗi, không nhận hàm tổng hợp."""
    context=prepare_context(store,formula,segment)
    if segment.id not in formula.segment_ids:
        raise ValueError("Công thức chưa được gán cho giai đoạn này.")
    if aggregate_calls(context.node):
        raise ValueError("Đồ thị công thức chỉ nhận biểu thức tín hiệu, không chứa hàm tổng hợp.")
    first_chunk=True
    for grid in timeline.iter_time_grid(context.arrays,segment,formula.interpolation,formula.max_gap):
        check_cancelled(token)
        grid=split_transition_times(context,grid)
        left,right=grid[:-1],grid[1:]
        midpoint=left+(right-left)/2
        values=point_values(context,context.node,grid)
        middle_values=point_values(context,context.node,midpoint)
        bad=~np.isfinite(middle_values)|invalid_domains(context.node,interval_environment(context,left,right),len(left))
        if np.any(bad):
            combined=np.concatenate([grid,midpoint[bad]])
            combined_values=np.concatenate([values,np.full(np.count_nonzero(bad),np.nan)])
            order=np.argsort(combined)
            grid,values=combined[order],combined_values[order]
        if not first_chunk:
            grid,values=grid[1:],values[1:]
        first_chunk=False
        yield grid,values


def evaluate_trace(store, formula, segment, token=None):
    """Ghép trace trong RAM, dùng khi vẽ một giai đoạn có kích thước phù hợp.

    Dữ liệu vẫn tính theo chunk nhưng mảng kết quả chiếm RAM theo độ dài.
    Luồng xuất file lớn nên dùng iter_evaluate_trace để tránh ghép toàn bộ."""
    chunks=list(iter_evaluate_trace(store,formula,segment,token))
    return (np.concatenate([t for t,_ in chunks]),np.concatenate([v for _,v in chunks])) if chunks else (np.empty(0),np.empty(0))
