"""Chức năng: API công khai cho công thức, căn tín hiệu và kết quả tính toán.

Sửa tại đây khi: thêm/đổi API cho GUI, CLI hoặc exporter. Logic nằm trong
calculations/ để chỉnh từng chức năng mà không phải sửa file điều phối lớn.
Liên kết: calculations/syntax.py (biểu thức), alignment.py (căn mẫu), engine.py
(tổng hợp theo giai đoạn), traces.py (chuỗi tín hiệu). Các module này liên kết
đến timeline, units, polynomial, domains và integration cho logic chuyên biệt.
"""
# COMPONENT: formulas.public_api

from .calculations.alignment import align_values
from .calculations.engine import evaluate_all, evaluate_formula
from .calculations.syntax import formula_kind, validate_expression
from .calculations.traces import evaluate_trace, iter_evaluate_trace

__all__ = [
    "align_values", "evaluate_all", "evaluate_formula", "evaluate_trace",
    "formula_kind", "iter_evaluate_trace", "validate_expression",
]
