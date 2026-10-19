"""Chức năng: bảng đơn vị và kiểm tra thứ nguyên công thức.

Sửa tại đây khi: thêm đơn vị hoặc thay quy tắc thứ nguyên của một hàm.
Liên kết: context.py kiểm tra đơn vị đầu vào/kết quả; syntax.py định nghĩa các hàm được phép.
"""
from __future__ import annotations

# COMPONENT: calculations.units

import ast

from .syntax import constant_value


# Thứ nguyên: khối lượng, chiều dài, thời gian, cường độ dòng điện.
# Chỉ kiểm tra thứ nguyên; việc đổi thang đơn vị luôn phải ghi trong công thức.
_D0 = (0., 0., 0., 0.)
_DV = (1., 2., -3., -1.)
_DA = (0., 0., 0., 1.)
_DW = (1., 2., -3., 0.)
_DE = (1., 2., -2., 0.)
UNIT_DIMENSIONS = {
    "1": _D0, "%": _D0, "bool": _D0, "-": _D0,
    "v": _DV, "mv": _DV, "kv": _DV, "a": _DA, "ma": _DA,
    "w": _DW, "kw": _DW, "mw": _DW, "j": _DE, "kj": _DE,
    "wh": _DE, "kwh": _DE, "ws": _DE, "w*s": _DE,
    "s": (0., 0., 1., 0.), "ms": (0., 0., 1., 0.),
    "m": (0., 1., 0., 0.), "km": (0., 1., 0., 0.),
    "m/s": (0., 1., -1., 0.), "km/h": (0., 1., -1., 0.),
    "kph": (0., 1., -1., 0.), "rpm": (0., 0., -1., 0.),
    "hz": (0., 0., -1., 0.), "ah": (0., 0., 1., 1.),
}

def dimensions(node, units):
    """Suy ra thứ nguyên và từ chối phép cộng/trừ không tương thích.

    Chỉ kiểm tra thứ nguyên, không chuyển V/mV, W/kW hoặc giây/giờ.
    None biểu thị đơn vị chưa nhận diện; hằng số không áp đặt thang đo."""
    if isinstance(node, ast.Constant):
        return "constant"
    if isinstance(node, ast.Name):
        return units[node.id]
    if isinstance(node, ast.UnaryOp):
        return dimensions(node.operand, units)
    if isinstance(node, ast.BinOp):
        a, b = dimensions(node.left, units), dimensions(node.right, units)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            if a == "constant":
                return b
            if b == "constant":
                return a
            if a is not None and b is not None and a != b:
                raise ValueError("Không thể cộng/trừ các tín hiệu có thứ nguyên khác nhau.")
            return a if a == b else None
        if isinstance(node.op, ast.Pow):
            if a is None or a == "constant":
                return a
            return tuple(x * constant_value(node.right) for x in a)
        if a is None or b is None:
            return None
        a, b = _D0 if a == "constant" else a, _D0 if b == "constant" else b
        return tuple(x + (-y if isinstance(node.op, ast.Div) else y) for x, y in zip(a, b))
    name = node.func.id
    args = [dimensions(arg, units) for arg in node.args]
    value = args[0]
    if name == "safe_div":
        numerator, denominator, threshold = args
        if denominator not in (None,"constant") and threshold not in (None,"constant") and denominator != threshold:
            raise ValueError("Ngưỡng safe_div phải cùng thứ nguyên với mẫu số.")
        if numerator is None or denominator is None:
            return None
        numerator = _D0 if numerator == "constant" else numerator
        denominator = _D0 if denominator == "constant" else denominator
        return tuple(x-y for x,y in zip(numerator,denominator))
    if name == "clip":
        for other in args[1:]:
            if value is not None and other not in (None, "constant") and value != "constant" and value != other:
                raise ValueError("Giới hạn clip phải cùng thứ nguyên với tín hiệu.")
    if value in (None, "constant"):
        value = _D0 if value == "constant" else None
    if name == "integral" and value is not None:
        return tuple(x + y for x, y in zip(value, (0., 0., 1., 0.)))
    if name == "sqrt" and value is not None:
        return tuple(x / 2 for x in value)
    return value
