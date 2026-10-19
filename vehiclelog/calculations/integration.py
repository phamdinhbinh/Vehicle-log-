"""Chức năng: tích phân thích nghi và xác minh cực trị phi đa thức.

Sửa tại đây khi: đổi sai số hội tụ, quy tắc Gauss hoặc giới hạn tài nguyên cực trị.
Liên kết: engine.py gọi phép tính; domains.py cung cấp cận; context.py cung cấp dữ liệu căn thời gian.
"""
from __future__ import annotations

# COMPONENT: calculations.integration

import numpy as np

from .common import CHUNK_SIZE, check_cancelled
from .context import point_values, interval_environment
from .domains import interval_bounds
from .syntax import evaluate_node


G8, W8 = np.polynomial.legendre.leggauss(8)
G16, W16 = np.polynomial.legendre.leggauss(16)


def integrate_intervals(context, node, left, right, token=None, depth=0):
    """Tích phân thích nghi Gauss 8/16 điểm, thời gian tính bằng giây.

    Không hội tụ trong giới hạn thì báo lỗi; không trả tổng chưa xác minh.
    token được kiểm tra ở mỗi lần chia nhỏ để người dùng có thể hủy."""
    if not len(left):
        return np.empty(0)
    check_cancelled(token)
    width, midpoint = right-left, left+(right-left)/2
    def calc(nodes, weights):
        positions = midpoint[:,None] + width[:,None] * nodes / 2
        values = np.broadcast_to(evaluate_node(node, context.env(positions)), positions.shape)
        return width/2 * np.sum(values*weights,axis=1)
    coarse, fine = calc(G8,W8), calc(G16,W16)
    tolerance = 1e-10 * np.maximum(np.abs(fine), 1e-4) + width * 1e-11
    refine = np.isfinite(fine) & (np.abs(fine-coarse) > tolerance)
    if np.any(refine):
        if depth >= 30 or np.any((midpoint[refine] <= left[refine]) | (midpoint[refine] >= right[refine])):
            raise ValueError("Tích phân không hội tụ; kiểm tra công thức hoặc chia nhỏ giai đoạn.")
        fine[refine] = (integrate_intervals(context,node,left[refine],midpoint[refine],token,depth+1)
                        + integrate_intervals(context,node,midpoint[refine],right[refine],token,depth+1))
    return fine


def nonlinear_extreme(context, node, left, right, name, best, token=None):
    """Tìm cực trị phi đa thức bằng cận khoảng thay vì chỉ lấy mẫu.

    Nếu không siết được cận trong giới hạn tài nguyên thì báo lỗi rõ ràng,
    tránh âm thầm bỏ sót đỉnh nằm giữa hai timestamp nguồn."""
    for _ in range(48):
        check_cancelled(token)
        if not len(left):
            return best
        middle=left+(right-left)/2
        values=point_values(context,node,middle)
        if np.any(~np.isfinite(values)):
            raise ValueError("Miền tính min/max có giá trị không hợp lệ.")
        best=(min(best,float(np.min(values))) if name=="min" else max(best,float(np.max(values))))
        low,high=interval_bounds(node,interval_environment(context,left,right),len(left))
        if np.any(~np.isfinite(low)|~np.isfinite(high)):
            raise ValueError("Không xác minh được miền tính min/max; kiểm tra công thức.")
        tolerance=1e-9*max(abs(best),1e-6)+1e-11
        unresolved=(low<best-tolerance) if name=="min" else (high>best+tolerance)
        if not np.any(unresolved):
            return best
        left,right,middle=left[unresolved],right[unresolved],middle[unresolved]
        if len(left)>CHUNK_SIZE*8 or np.any((middle<=left)|(middle>=right)):
            break
        left,right=np.concatenate([left,middle]),np.concatenate([middle,right])
    raise ValueError("Min/max không hội tụ trong giới hạn tài nguyên; chia nhỏ giai đoạn hoặc đơn giản hóa công thức.")
