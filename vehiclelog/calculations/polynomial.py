"""Chức năng: biểu diễn đa thức và tìm nghiệm theo từng khoảng nội suy.

Sửa tại đây khi: đổi giới hạn bậc, thuật toán nghiệm hoặc biểu diễn hệ số.
Liên kết: interval_splits.py chèn mốc đổi dấu; domains.py kiểm tra miền; engine.py tìm cực trị.
"""
from __future__ import annotations

# COMPONENT: calculations.polynomial

import ast

import numpy as np

from .syntax import constant_value


def polynomial_coefficients(node, env):
    """Biểu diễn AST thành hệ số đa thức trên tọa độ khoảng u ∈ [0, 1].

    Mỗi hệ số là vector theo khoảng; trả None nếu không chứng minh được
    dạng đa thức hoặc bậc vượt giới hạn, để dùng nhánh kiểm tra bảo thủ."""
    if isinstance(node, ast.Constant):
        return [np.full_like(next(iter(env.values()))[0], float(node.value))] if env else [np.asarray(float(node.value))]
    if isinstance(node, ast.Name):
        a, b = env[node.id]
        return [a, b - a]
    if isinstance(node, ast.UnaryOp):
        p = polynomial_coefficients(node.operand, env)
        return None if p is None else [-c for c in p] if isinstance(node.op, ast.USub) else p
    if not isinstance(node, ast.BinOp):
        return None
    p, q = polynomial_coefficients(node.left, env), polynomial_coefficients(node.right, env)
    if p is None or q is None:
        return None
    if isinstance(node.op, (ast.Add, ast.Sub)):
        n = max(len(p), len(q))
        return [(p[i] if i < len(p) else 0) + (-1 if isinstance(node.op, ast.Sub) else 1) * (q[i] if i < len(q) else 0) for i in range(n)]
    if isinstance(node.op, ast.Div):
        if any(np.any(c != 0) for c in q[1:]):
            return None
        with np.errstate(all="ignore"):
            return [c / q[0] for c in p]
    if isinstance(node.op, ast.Pow):
        power = int(constant_value(node.right))
        if power < 0:
            return None
        q, result = p, [np.ones_like(p[0])]
        for _ in range(power):
            result = multiply_coefficients(result, q)
            if len(result) > 33:
                return None
        return result
    result = multiply_coefficients(p, q)
    return result if len(result) <= 33 else None


def multiply_coefficients(p, q):
    """Nhân hai đa thức dạng hệ số tăng dần; giữ vector theo từng khoảng thời gian."""
    result = [np.zeros_like(p[0]) for _ in range(len(p) + len(q) - 1)]
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            result[i + j] = result[i + j] + a * b
    return result


def interval_roots(polynomial, count, include_edges=False):
    """Tìm chỉ số khoảng và nghiệm thực theo u ∈ [0, 1], trong chunk hữu hạn.

    Mặc định bỏ hai đầu khoảng; include_edges dùng khi dò mẫu số bằng 0.
    Nghiệm bậc hai dùng công thức ổn định, có nhánh suy biến về bậc nhất."""
    if polynomial is None:
        return np.empty(0, dtype=int), np.empty(0)
    p = [np.broadcast_to(c, (count,)) for c in polynomial]
    while len(p) > 1 and np.all(p[-1] == 0):
        p.pop()
    if len(p) == 1:
        return np.flatnonzero(p[0] == 0) if include_edges else np.empty(0, dtype=int), np.zeros(np.count_nonzero(p[0] == 0)) if include_edges else np.empty(0)
    candidates = []
    if len(p) == 2:
        with np.errstate(all="ignore"):
            candidates.append(-p[0] / p[1])
    elif len(p) == 3:
        # Nghiệm bậc hai ổn định; xử lý suy biến tuyến tính riêng từng khoảng.
        a, b, c = p[2], p[1], p[0]
        with np.errstate(all="ignore"):
            disc = b*b - 4*a*c
            q = -0.5 * (b + np.where(b >= 0, 1., -1.) * np.sqrt(disc))
            r1 = q/a
            r2 = c/q
            r1 = np.where(a == 0, -c/b, r1)
            r2 = np.where((a == 0) | (disc < 0), np.nan, r2)
            r1 = np.where((a != 0) & (disc < 0), np.nan, r1)
            r2 = np.where((a != 0) & (q == 0) & (disc == 0), -b/(2*a), r2)
        candidates.extend([r1, r2])
    else:
        indices, values = [], []
        for i in range(count):
            coefficients = np.array([c[i] for c in p])
            if not np.all(np.isfinite(coefficients)):
                continue
            for root in np.polynomial.polynomial.polyroots(coefficients):
                if abs(root.imag) <= 1e-10:
                    u = float(root.real)
                    if (0 <= u <= 1) if include_edges else (0 < u < 1):
                        indices.append(i)
                        values.append(u)
        return np.asarray(indices, dtype=int), np.asarray(values)
    indices, values = [], []
    for roots in candidates:
        mask = np.isfinite(roots) & ((roots >= 0) & (roots <= 1) if include_edges else (roots > 0) & (roots < 1))
        indices.append(np.flatnonzero(mask))
        values.append(roots[mask])
    return np.concatenate(indices), np.concatenate(values)
