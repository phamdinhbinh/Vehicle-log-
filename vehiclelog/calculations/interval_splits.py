"""Chức năng: chèn mốc đổi dấu và đổi nhánh của hàm trước khi tích phân.

Sửa tại đây khi: thêm hàm từng đoạn hoặc cần bảo toàn xung hẹp giữa hai mẫu.
Liên kết: context.py cung cấp hai đầu khoảng; polynomial.py tìm nghiệm; engine.py/traces.py dùng grid mới.
"""
from __future__ import annotations

# COMPONENT: calculations.interval_splits

import ast

import numpy as np

from .context import interval_environment
from .polynomial import polynomial_coefficients, interval_roots


def split_transition_times(context, grid):
    """Chèn nghiệm đổi dấu/clip/sqrt để không bỏ sót xung hẹp khi tích phân.

    Chỉ cần với nội suy linear. Timestamp đầu ra vẫn tăng và không trùng."""
    if context.formula.interpolation != "linear" or not context.arrays:
        return grid
    left, right = grid[:-1], grid[1:]
    env = interval_environment(context, left, right)
    additions = []
    for node in ast.walk(context.node):
        candidates = []
        if isinstance(node, ast.Call) and node.func.id in {"abs", "positive", "negative", "sqrt"}:
            candidates.append(polynomial_coefficients(node.args[0], env))
        elif isinstance(node, ast.Call) and node.func.id == "clip":
            p = polynomial_coefficients(node.args[0], env)
            for bound in node.args[1:]:
                q = polynomial_coefficients(bound, env)
                if p is not None and q is not None:
                    candidates.append([(p[i] if i < len(p) else 0) - (q[i] if i < len(q) else 0) for i in range(max(len(p),len(q)))])
        for p in candidates:
            ix, u = interval_roots(p, len(left))
            if len(ix):
                additions.append(left[ix] + u * (right[ix] - left[ix]))
    return np.unique(np.concatenate([grid] + additions)) if additions else grid
