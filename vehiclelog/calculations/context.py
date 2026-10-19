"""Chức năng: chuẩn bị dữ liệu và môi trường tính cho một công thức–giai đoạn.

Sửa tại đây khi: đổi cách đọc mẫu lân cận, kiểm tra cấu hình hoặc metadata đơn vị.
Liên kết: alignment.py căn mẫu; units.py kiểm tra thứ nguyên; engine.py/traces.py sử dụng ngữ cảnh.
"""
from __future__ import annotations

# COMPONENT: calculations.context

import ast
from dataclasses import dataclass
import math

import numpy as np

from ..models import Formula, Segment
from .alignment import align_values
from .syntax import parse_expression, referenced_aliases, evaluate_node
from .units import UNIT_DIMENSIONS, dimensions


@dataclass
class FormulaContext:
    """Ngữ cảnh dữ liệu riêng cho một cặp công thức–giai đoạn.

    arrays giữ dữ liệu đọc có mẫu lân cận; env căn dữ liệu khi được yêu cầu.
    Tất cả timestamp và max_gap tính bằng giây, không tự đổi thang đơn vị."""
    node: ast.AST
    arrays: dict
    formula: Formula
    segment: Segment
    unit_message: str

    def env(self, target):
        """Căn mọi tín hiệu lên target theo cấu hình hold/linear và max_gap."""
        return {alias: align_values(t, v, target, self.formula.interpolation, self.formula.max_gap)
                for alias, (t, v) in self.arrays.items()}


def prepare_context(store, formula, segment):
    """Kiểm tra cấu hình, đọc đúng tín hiệu và chuẩn bị một giai đoạn.

    Đọc kèm mẫu lân cận để căn chính xác tại ranh giới. Kiểm tra thứ nguyên
    không thay thế chuyển thang đo; đơn vị lạ được ghi rõ là chưa xác minh."""
    segment.validate()
    if formula.interpolation not in {"hold", "linear"}:
        raise ValueError("Nội suy phải là hold hoặc linear.")
    if not math.isfinite(formula.max_gap) or formula.max_gap <= 0:
        raise ValueError("max_gap phải hữu hạn và lớn hơn 0.")
    node = parse_expression(formula.expression, formula.bindings)
    arrays, units, unknown = {}, {}, []
    for alias in sorted(referenced_aliases(node)):
        key = formula.bindings[alias]
        if key not in store.signals:
            raise ValueError(f"Không tìm thấy tín hiệu: {key}")
        times, values = store.read(key, segment.start, segment.end, neighbors=True)
        arrays[alias] = (times, values)
        unit = store.signals[key].unit.strip().lower()
        units[alias] = UNIT_DIMENSIONS.get(unit)
        if units[alias] is None:
            unknown.append(alias)
    dimension = dimensions(node, units)
    result_unit = formula.unit.strip().lower()
    if result_unit in UNIT_DIMENSIONS and dimension not in (None, "constant") and UNIT_DIMENSIONS[result_unit] != dimension:
        raise ValueError("Đơn vị kết quả không khớp thứ nguyên của công thức.")
    message = "Kiểm tra thứ nguyên; không tự đổi thang đơn vị (V/mV, W/kW, s/h)."
    if unknown or (result_unit and result_unit not in UNIT_DIMENSIONS):
        message += " Chưa xác minh đơn vị không nhận diện được: " + ", ".join(unknown + ([formula.unit] if result_unit not in UNIT_DIMENSIONS and result_unit else [])) + "."
    return FormulaContext(node, arrays, formula, segment, message)


def interval_environment(context, left, right):
    """Lấy giá trị hai đầu mỗi khoảng cho kiểm tra miền và đa thức.

    hold lấy giá trị ở giữa rồi giữ cố định; linear dùng hai đầu thực tế."""
    if context.formula.interpolation == "hold":
        middle = context.env(left + (right - left) / 2)
        return {name: (value, value) for name, value in middle.items()}
    low, high = context.env(left), context.env(right)
    return {name: (low[name], high[name]) for name in low}


def point_values(context, node, times):
    """Tính biểu thức tại timestamp đích và broadcast hằng số về đúng kích thước."""
    return np.broadcast_to(evaluate_node(node, context.env(times)), times.shape)
