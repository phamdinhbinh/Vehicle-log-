"""Chức năng: kiểm tra miền hợp lệ và cận bảo thủ trên các khoảng thời gian.

Sửa tại đây khi: đổi quy tắc chia cho 0, safe_div, sqrt, clip hoặc cận phi đa thức.
Liên kết: syntax.py tính AST; polynomial.py xác định nghiệm; integration.py/engine.py/traces.py kiểm tra khoảng.
"""
from __future__ import annotations

# COMPONENT: calculations.domains

import ast

import numpy as np

from .polynomial import polynomial_coefficients, interval_roots
from .syntax import constant_value, evaluate_node


def invalid_domains(node, env, count):
    """Đánh dấu khoảng vi phạm miền, kể cả nghiệm mẫu số giữa các mẫu.

    safe_div phải vượt ngưỡng trên cả khoảng; sqrt phải không âm.
    Với biểu thức phi đa thức dùng cận bảo thủ, không chỉ dò vài điểm."""
    bad = np.zeros(count, dtype=bool)
    for item in ast.walk(node):
        if isinstance(item, ast.Call) and item.func.id == "sqrt":
            low, high = interval_bounds(item.args[0],env,count)
            bad |= (low < 0) | ~np.isfinite(low) | ~np.isfinite(high)
        if isinstance(item, ast.Call) and item.func.id == "clip":
            lower_min,lower_max=interval_bounds(item.args[1],env,count)
            upper_min,upper_max=interval_bounds(item.args[2],env,count)
            bad |= lower_max > upper_min
        if isinstance(item, ast.Call) and item.func.id == "safe_div":
            low, high = interval_bounds(item.args[1],env,count)
            threshold_low, threshold_high = interval_bounds(item.args[2],env,count)
            bad |= (low <= threshold_high) & (high >= -threshold_high)
            bad |= (threshold_low < 0) | ~np.isfinite(threshold_low) | ~np.isfinite(threshold_high)
        denominator = None
        if isinstance(item, ast.BinOp) and isinstance(item.op, ast.Div):
            denominator = item.right
        elif isinstance(item, ast.BinOp) and isinstance(item.op, ast.Pow) and constant_value(item.right) < 0:
            denominator = item.left
        if denominator is not None:
            p = polynomial_coefficients(denominator, env)
            if p is not None:
                ix, _ = interval_roots(p, count, include_edges=True)
                bad[ix] = True
            else:
                # Cận khoảng bảo thủ tránh bỏ sót hai nghiệm mẫu số rất gần nhau.
                low, high = interval_bounds(denominator, env, count)
                bad |= (low <= 0) & (high >= 0)
                bad |= ~np.isfinite(low) | ~np.isfinite(high)
    return bad


def interval_bounds(node, env, count):
    """Tính cận bảo thủ trên từng khoảng để kiểm tra miền và cực trị phi đa thức."""
    polynomial = polynomial_coefficients(node,env)
    if polynomial is not None:
        coefficients=[np.broadcast_to(c,(count,)) for c in polynomial]
        at_zero=np.broadcast_to(evaluate_node(node,{name:a for name,(a,b) in env.items()}),(count,))
        at_one=np.broadcast_to(evaluate_node(node,{name:b for name,(a,b) in env.items()}),(count,))
        low,high=np.minimum(at_zero,at_one).copy(),np.maximum(at_zero,at_one).copy()
        if len(coefficients)>2:
            derivative=[i*coefficients[i] for i in range(1,len(coefficients))]
            ix,u=interval_roots(derivative,count)
            if len(ix):
                point_env={name:a[ix]+(b[ix]-a[ix])*u for name,(a,b) in env.items()}
                values=np.broadcast_to(evaluate_node(node,point_env),u.shape)
                np.minimum.at(low,ix,values)
                np.maximum.at(high,ix,values)
        return low,high
    if isinstance(node, ast.Constant):
        value = np.full(count, float(node.value))
        return value, value
    if isinstance(node, ast.Name):
        a, b = env[node.id]
        return np.minimum(a, b), np.maximum(a, b)
    if isinstance(node, ast.UnaryOp):
        low, high = interval_bounds(node.operand, env, count)
        return (-high, -low) if isinstance(node.op, ast.USub) else (low, high)
    with np.errstate(all="ignore"):
        if isinstance(node, ast.BinOp):
            a, b = interval_bounds(node.left, env, count)
            c, d = interval_bounds(node.right, env, count)
            if isinstance(node.op, ast.Add):
                return a+c, b+d
            if isinstance(node.op, ast.Sub):
                if ast.dump(node.left) == ast.dump(node.right):
                    return np.zeros(count), np.zeros(count)
                return a-d, b-c
            if isinstance(node.op, ast.Pow):
                exponent = int(constant_value(node.right))
                if exponent == 0:
                    return np.ones(count), np.ones(count)
                low, high = np.minimum(a**exponent,b**exponent), np.maximum(a**exponent,b**exponent)
                crossing = (a <= 0) & (b >= 0)
                if exponent < 0:
                    return np.where(crossing,-np.inf,low), np.where(crossing,np.inf,high)
                if exponent % 2 == 0:
                    low=np.where(crossing,0.,low)
                return low, high
            if isinstance(node.op, ast.Div):
                crossing = (c <= 0) & (d >= 0)
                possibilities=np.stack([a/c,a/d,b/c,b/d])
                return np.where(crossing,-np.inf,np.min(possibilities,axis=0)),np.where(crossing,np.inf,np.max(possibilities,axis=0))
            possibilities=np.stack([a*c,a*d,b*c,b*d])
            return np.min(possibilities,axis=0),np.max(possibilities,axis=0)
        name=node.func.id
        low,high=interval_bounds(node.args[0],env,count)
        if name=="positive":
            return np.maximum(low,0.),np.maximum(high,0.)
        if name=="negative":
            return np.maximum(-high,0.),np.maximum(-low,0.)
        if name=="abs":
            return np.where((low<=0)&(high>=0),0.,np.minimum(np.abs(low),np.abs(high))),np.maximum(np.abs(low),np.abs(high))
        if name=="sqrt":
            return np.sqrt(low),np.sqrt(high)
        if name=="clip":
            lower_a,lower_b=interval_bounds(node.args[1],env,count)
            upper_a,upper_b=interval_bounds(node.args[2],env,count)
            return np.minimum(np.maximum(low,lower_a),upper_a),np.minimum(np.maximum(high,lower_b),upper_b)
        if name=="safe_div":
            denominator_low,denominator_high=interval_bounds(node.args[1],env,count)
            threshold_low,threshold_high=interval_bounds(node.args[2],env,count)
            unsafe=((denominator_low<=threshold_high)&(denominator_high>=-threshold_high))|(threshold_low<0)
            possibilities=np.stack([low/denominator_low,low/denominator_high,high/denominator_low,high/denominator_high])
            return np.where(unsafe,-np.inf,np.min(possibilities,axis=0)),np.where(unsafe,np.inf,np.max(possibilities,axis=0))
    return np.full(count,-np.inf),np.full(count,np.inf)
