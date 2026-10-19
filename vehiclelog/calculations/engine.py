"""Chức năng: điều phối phép tính scalar cho các công thức và giai đoạn đã chọn.

Sửa tại đây khi: đổi tổng hợp, độ phủ, trạng thái kết quả hoặc lịch chạy công thức.
Liên kết: syntax/context chuẩn bị; timeline/interval_splits chia khoảng; integration/domains tính và kiểm tra; traces.py xử lý chuỗi.
"""
from __future__ import annotations

# COMPONENT: calculations.engine

import math

import numpy as np

from ..models import FormulaResult, report
from . import timeline
from .common import check_cancelled
from .context import prepare_context, interval_environment, point_values
from .domains import invalid_domains
from .integration import integrate_intervals, nonlinear_extreme
from .interval_splits import split_transition_times
from .polynomial import polynomial_coefficients, interval_roots
from .syntax import is_scalar, aggregate_calls, evaluate_node, referenced_aliases


def evaluate_formula(store, formula, segment, token=None):
    """Tính một công thức trong đúng giai đoạn được gán, không sửa dữ liệu nguồn.

    Timestamp tính bằng giây. Thiếu phủ dữ liệu hoặc miền tính không hợp lệ
    thì không công bố tổng một phần; value=None và status giải thích lỗi.
    Ngoại lệ hủy tác vụ được truyền ra ngoài để worker dừng bình thường."""
    result = FormulaResult(formula.id,formula.name,segment.id,segment.name,None,formula.unit)
    if segment.id not in formula.segment_ids:
        result.status, result.message, result.coverage = "not_applied", "Công thức chưa được gán cho giai đoạn này.", 0.
        return result
    try:
        # 1. Xác minh công thức, dữ liệu đầu vào và loại kết quả (scalar/trace).
        check_cancelled(token)
        context = prepare_context(store,formula,segment)
        if not is_scalar(context.node):
            if aggregate_calls(context.node):
                raise ValueError("Không trộn kết quả tổng hợp và chuỗi tín hiệu ngoài hàm tổng hợp.")
            result.status, result.message = "trace", "Công thức tín hiệu; dùng Vẽ công thức để xem đồ thị."
            return result
        calls = aggregate_calls(context.node)
        accumulators = {id(call): {"sum":0.,"weight":0.,"min":math.inf,"max":-math.inf,"first":None,"last":None} for call in calls}
        coverage, domain_failure = 0., False
        # 2. Duyệt các khoảng có biên chính xác; chỉ tích lũy mẫu hợp lệ.
        for original_grid in timeline.iter_time_grid(context.arrays,segment,formula.interpolation,formula.max_gap):
            check_cancelled(token)
            grid = split_transition_times(context,original_grid)
            left,right = grid[:-1],grid[1:]
            middle = left+(right-left)/2
            env_mid = context.env(middle)
            valid = np.ones(len(left),dtype=bool)
            for value in env_mid.values():
                valid &= np.isfinite(value)
            env_interval = interval_environment(context,left,right)
            # Kiểm tra đối số hàm tổng hợp trên từng khoảng; không đưa
            # toàn bộ AST tổng hợp vào phép kiểm tra miền chuỗi.
            for call in calls:
                bad = invalid_domains(call.args[0],env_interval,len(left))
                domain_failure |= bool(np.any(bad & valid))
                valid &= ~bad
                sample = np.broadcast_to(evaluate_node(call.args[0],env_mid),middle.shape)
                domain_failure |= bool(np.any(valid & ~np.isfinite(sample)))
                valid &= np.isfinite(sample)
            coverage += float(np.sum((right-left)[valid]))
            for call in calls:
                name, arg, state = call.func.id, call.args[0], accumulators[id(call)]
                if name in {"integral","mean"}:
                    if formula.interpolation == "hold":
                        sample = np.broadcast_to(evaluate_node(arg,env_mid),middle.shape)
                        contribution = sample[valid]*(right-left)[valid]
                    else:
                        contribution = integrate_intervals(context,arg,left[valid],right[valid],token)
                    if np.any(~np.isfinite(contribution)):
                        domain_failure = True
                    else:
                        state["sum"] += math.fsum(contribution)
                    state["weight"] += float(np.sum((right-left)[valid]))
                elif name == "sample_mean":
                    # Biên phải thuộc chunk sau, trừ cuối giai đoạn; tránh
                    # đếm hai lần trọng số mẫu khi tính sample_mean.
                    native_times = original_grid if original_grid[-1] == segment.end else original_grid[:-1]
                    native = np.zeros(len(native_times),dtype=bool)
                    for alias in referenced_aliases(arg):
                        source_times = context.arrays[alias][0]
                        indices = np.searchsorted(source_times,native_times)
                        if len(source_times):
                            native |= (indices < len(source_times)) & (source_times[np.minimum(indices,len(source_times)-1)] == native_times)
                    values = point_values(context,arg,native_times[native])
                    finite = np.isfinite(values)
                    state["sum"] += math.fsum(values[finite])
                    state["weight"] += int(np.count_nonzero(finite))
                elif name in {"min","max"}:
                    candidates = [grid]
                    p = polynomial_coefficients(arg,env_interval)
                    if p is not None and len(p)>1:
                        derivative = [i*p[i] for i in range(1,len(p))]
                        ix,u = interval_roots(derivative,len(left))
                        if len(ix):
                            candidates.append(left[ix]+u*(right[ix]-left[ix]))
                    values = point_values(context,arg,np.unique(np.concatenate(candidates)))
                    finite = values[np.isfinite(values)]
                    if len(finite):
                        state["min"] = min(state["min"],float(np.min(finite)))
                        state["max"] = max(state["max"],float(np.max(finite)))
                    if formula.interpolation=="linear" and p is None and np.any(valid):
                        state[name]=nonlinear_extreme(context,arg,left[valid],right[valid],name,state[name],token)
        # 3. Chặn tổng một phần: thiếu dữ liệu hoặc sai miền thì không trả value.
        result.coverage = max(0.,min(1.,coverage/(segment.end-segment.start)))
        if domain_failure:
            result.status,result.message = "invalid","Công thức có chia cho 0, giá trị không hữu hạn hoặc miền tính không hợp lệ."
            return result
        if result.coverage < 1.-1e-12:
            result.status,result.message = "incomplete",f"Thiếu/mất dữ liệu; độ phủ {result.coverage:.2%}. Không công bố tổng một phần."
            return result
        # 4. Chốt các hàm tổng hợp, rồi tính biểu thức scalar ngoài cùng.
        aggregates = {}
        for call in calls:
            name,state = call.func.id,accumulators[id(call)]
            if name in {"first","last","delta"}:
                endpoints = point_values(context,call.args[0],np.array([segment.start,segment.end]))
                if not np.all(np.isfinite(endpoints)):
                    raise ValueError("Không có giá trị hợp lệ tại ranh giới giai đoạn.")
                value = endpoints[0] if name=="first" else endpoints[1] if name=="last" else endpoints[1]-endpoints[0]
            elif name=="integral":
                value=state["sum"]
            elif name in {"mean","sample_mean"}:
                if not state["weight"]:
                    raise ValueError("Không có mẫu hợp lệ để tính trung bình.")
                value=state["sum"]/state["weight"]
            else:
                value=state[name]
            aggregates[id(call)] = value
        value=float(evaluate_node(context.node,{},aggregates))
        if not math.isfinite(value):
            raise ValueError("Kết quả không hữu hạn; kiểm tra chia cho 0 và miền tính.")
        result.value,result.message = value,context.unit_message
        return result
    except (ValueError,KeyError,FloatingPointError,OverflowError,ZeroDivisionError,np.linalg.LinAlgError) as exc:
        result.status,result.message,result.coverage = "invalid",str(exc),0.
        return result


def evaluate_all(store, formulas, segments, progress=None, token=None):
    """Chỉ tính các cặp công thức–giai đoạn được tick chọn và báo tiến độ từng cặp."""
    jobs=[(formula,segment) for formula in formulas for segment in segments if segment.id in formula.segment_ids]
    results=[]
    for i,(formula,segment) in enumerate(jobs):
        check_cancelled(token)
        report(progress,i/max(1,len(jobs)),f"Tính {formula.name}: {segment.name}")
        results.append(evaluate_formula(store,formula,segment,token))
    report(progress,1.,"Hoàn tất tính toán.")
    return results
