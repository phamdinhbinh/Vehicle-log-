"""Chức năng: tạo giai đoạn liên tiếp giữa các con trỏ M1–M2, M2–M3…

Sửa tại đây khi: đổi quy tắc đánh số mốc hoặc giữ gán công thức khi thêm/xóa mốc.
Liên kết: UI gọi synchronize_stages sau mỗi thay đổi; backend tích phân dùng Segment.
"""
# COMPONENT: stages.adjacent_cursors
from dataclasses import replace
import math
import re

from .models import Segment


def _covered(start, end, intervals):
    """Chỉ kế thừa công thức nếu toàn khoảng mới đã được chọn trước đó."""
    reached = start
    for left, right in sorted(intervals):
        if right <= reached:
            continue
        if left > reached + 1e-9:
            return False
        reached = max(reached, right)
        if reached >= end - 1e-9:
            return True
    return False


def synchronize_stages(project):
    """Đồng bộ n con trỏ thành n−1 giai đoạn, giữ ID của cặp còn tồn tại.

    Mốc được xếp theo thời gian, đánh số M1…Mn. Khi chia một giai đoạn, hai
    phần kế thừa công thức của nó. Khi gộp, chỉ kế thừa nếu toàn vùng đã được
    gán trước đó; không tự mở rộng một lựa chọn công thức sang vùng chưa chọn.
    Project cũ có giai đoạn thủ công được đối chiếu theo khoảng thời gian.
    """
    old = list(project.segments)
    before = [(s.id, s.start, s.end, s.start_cursor, s.end_cursor) for s in old]
    unique = {}
    for cursor in sorted(project.cursors, key=lambda c: c.time):
        if not math.isfinite(cursor.time):
            raise ValueError("Thời gian con trỏ không hợp lệ.")
        unique.setdefault(cursor.time, cursor)
    project.cursors = list(unique.values())
    for index, cursor in enumerate(project.cursors):
        cursor.name = f"M{index + 1}"
        cursor.locked = False  # Giữ trường cũ để đọc project, UI mới không có cơ chế khóa.
    by_pair = {(s.start_cursor, s.end_cursor): s for s in old if s.start_cursor and s.end_cursor}
    used = set()
    stages = []
    for index, (a, b) in enumerate(zip(project.cursors, project.cursors[1:])):
        previous = by_pair.get((a.id, b.id))
        if previous is None:
            previous = next((s for s in old if s.id not in used and
                             math.isclose(s.start, a.time, abs_tol=1e-9, rel_tol=0) and
                             math.isclose(s.end, b.time, abs_tol=1e-9, rel_tol=0)), None)
        if previous is not None:
            stage = replace(previous, start=a.time, end=b.time, start_cursor=a.id, end_cursor=b.id)
            if re.fullmatch(r"Giai đoạn \d+", stage.name):
                stage.name = f"Giai đoạn {index + 1}"
        else:
            stage = Segment(f"Giai đoạn {index + 1}", a.time, b.time, a.color,
                            start_cursor=a.id, end_cursor=b.id)
        used.add(stage.id)
        stages.append(stage)
    for formula in project.formulas:
        selected = set(formula.segment_ids)
        intervals = [(s.start, s.end) for s in old if s.id in selected]
        formula.segment_ids = [s.id for s in stages if s.id in selected or _covered(s.start, s.end, intervals)]
    project.segments = stages
    changed = before != [(s.id, s.start, s.end, s.start_cursor, s.end_cursor) for s in stages]
    if changed:
        project.results.clear()
    return changed
