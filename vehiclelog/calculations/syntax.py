"""Chức năng: cú pháp an toàn, phân loại công thức và tính biểu thức AST.

Sửa tại đây khi: thêm phép toán/hàm hoặc thay quy tắc scalar và trace.
Liên kết: units.py kiểm tra thứ nguyên; engine.py tính tổng hợp; formulas.py là API công khai.
"""
from __future__ import annotations

# COMPONENT: calculations.syntax

import ast
import math
from typing import Iterable

import numpy as np


AGGREGATE_FUNCTIONS = {"integral", "mean", "sample_mean", "min", "max", "first", "last", "delta"}
FUNCTION_ARITIES = {name: 1 for name in AGGREGATE_FUNCTIONS | {"abs", "positive", "negative", "sqrt"}}
FUNCTION_ARITIES["clip"] = 3
FUNCTION_ARITIES["safe_div"] = 3

def constant_value(node):
    """Đọc hằng số số học của AST; chỉ dùng sau khi biểu thức qua whitelist."""
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = constant_value(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    raise ValueError("Số mũ phải là hằng số.")


def parse_expression(expression: str, aliases: Iterable[str]):
    """Phân tích và kiểm tra whitelist trước khi tính, tuyệt đối không chạy mã Python.

    Giới hạn độ dài, số nút, số đối số, bí danh và số mũ; cấm lồng hàm tổng hợp.
    Thêm một hàm mới phải cập nhật whitelist, bộ tính và kiểm tra thứ nguyên."""
    aliases = set(aliases)
    if not expression or len(expression) > 4096:
        raise ValueError("Công thức trống hoặc quá dài (tối đa 4096 ký tự).")
    if any(not name.isidentifier() or name.startswith("_") or name in FUNCTION_ARITIES for name in aliases):
        raise ValueError("Bí danh phải là tên hợp lệ, không bắt đầu bằng _ và không trùng tên hàm.")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("Cú pháp công thức không hợp lệ.") from exc
    if sum(1 for _ in ast.walk(tree)) > 256:
        raise ValueError("Công thức quá phức tạp (tối đa 256 nút).")

    def visit(node, inside_aggregate=False):
        if isinstance(node, ast.Expression):
            visit(node.body, inside_aggregate)
        elif isinstance(node, ast.Constant):
            if type(node.value) not in (int, float) or abs(node.value) > 1e100 or not math.isfinite(node.value):
                raise ValueError("Chỉ chấp nhận hằng số hữu hạn.")
        elif isinstance(node, ast.Name):
            if node.id not in aliases:
                raise ValueError(f"Chưa gán tín hiệu cho bí danh: {node.id}")
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            visit(node.operand, inside_aggregate)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            visit(node.left, inside_aggregate)
            visit(node.right, inside_aggregate)
            if isinstance(node.op, ast.Pow):
                power = constant_value(node.right)
                if not power.is_integer() or abs(power) > 8:
                    raise ValueError("Số mũ phải là số nguyên từ -8 đến 8; dùng sqrt cho căn bậc hai.")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTION_ARITIES:
            name = node.func.id
            if node.keywords or len(node.args) != FUNCTION_ARITIES[name]:
                raise ValueError(f"Hàm {name} cần {FUNCTION_ARITIES[name]} đối số, không dùng đối số có tên.")
            if name in AGGREGATE_FUNCTIONS and inside_aggregate:
                raise ValueError("Không lồng các hàm tổng hợp bên trong nhau.")
            for arg in node.args:
                visit(arg, inside_aggregate or name in AGGREGATE_FUNCTIONS)
        else:
            raise ValueError("Chỉ cho phép tín hiệu, số, + - * / ** và các hàm được hỗ trợ.")
    visit(tree)
    return tree.body


def validate_expression(expression, aliases):
    """Kiểm tra cú pháp và bí danh; phát sinh ValueError khi công thức không được phép."""
    parse_expression(expression, aliases)


def formula_kind(formula):
    """Phân loại scalar/trace; cấm trộn kết quả tổng hợp với chuỗi ngoài hàm tổng hợp."""
    node = parse_expression(formula.expression, formula.bindings)
    if aggregate_calls(node) and not is_scalar(node):
        raise ValueError("Không trộn kết quả tổng hợp và chuỗi tín hiệu ngoài hàm tổng hợp.")
    return "scalar" if is_scalar(node) else "trace"


def referenced_aliases(node):
    """Lấy các bí danh tín hiệu được dùng; bỏ qua tên hàm trong whitelist."""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and n.id not in FUNCTION_ARITIES}


def aggregate_calls(node):
    """Lấy các nút hàm tổng hợp để engine tính riêng theo từng giai đoạn."""
    return [n for n in ast.walk(node) if isinstance(n, ast.Call) and n.func.id in AGGREGATE_FUNCTIONS]


def is_scalar(node):
    """Xác định AST tạo một giá trị hay một chuỗi tín hiệu theo thời gian."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.Name):
        return False
    if isinstance(node, ast.UnaryOp):
        return is_scalar(node.operand)
    if isinstance(node, ast.BinOp):
        return is_scalar(node.left) and is_scalar(node.right)
    if isinstance(node, ast.Call):
        return node.func.id in AGGREGATE_FUNCTIONS or all(is_scalar(arg) for arg in node.args)
    return False


def evaluate_node(node, env, aggregate=None):
    """Tính AST đã xác thực bằng phép toán NumPy, không dùng eval/exec.

    safe_div chỉ hợp lệ khi ngưỡng >= 0 và abs(mẫu số) > ngưỡng; trường hợp
    còn lại trả NaN để engine từ chối công bố kết quả không hợp lệ."""
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.UnaryOp):
        value = evaluate_node(node.operand, env, aggregate)
        return -value if isinstance(node.op, ast.USub) else value
    with np.errstate(all="ignore"):
        if isinstance(node, ast.BinOp):
            left, right = evaluate_node(node.left, env, aggregate), evaluate_node(node.right, env, aggregate)
            if isinstance(node.op, ast.Add):
                return np.add(left, right)
            if isinstance(node.op, ast.Sub):
                return np.subtract(left, right)
            if isinstance(node.op, ast.Mult):
                return np.multiply(left, right)
            if isinstance(node.op, ast.Div):
                return np.divide(left, right)
            return np.power(left, right)
        name = node.func.id
        if name in AGGREGATE_FUNCTIONS:
            return aggregate[id(node)]
        args = [evaluate_node(arg, env, aggregate) for arg in node.args]
        if name == "abs":
            return np.abs(args[0])
        if name == "positive":
            return np.maximum(args[0], 0.0)
        if name == "negative":
            return np.maximum(-args[0], 0.0)
        if name == "sqrt":
            return np.sqrt(args[0])
        if name == "clip":
            return np.where(np.asarray(args[1]) <= args[2], np.clip(*args), np.nan)
        if name == "safe_div":
            numerator, denominator, threshold = args
            allowed = (np.asarray(threshold) >= 0) & (np.abs(denominator) > threshold)
            return np.where(allowed, np.divide(numerator, denominator), np.nan)
    raise ValueError("Hàm không được hỗ trợ.")
