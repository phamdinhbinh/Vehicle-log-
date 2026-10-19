"""Lưu và khôi phục cấu hình project JSON.

Chức năng: ghi nguyên tử, kiểm tra liên kết ID và khôi phục đường dẫn nguồn.
Sửa tại đây khi: thay định dạng project, thêm trường hoặc quy tắc migrate.
Liên kết: models.Project là schema; ui/controllers/project.py xử lý thao tác UI.
"""
# COMPONENT: project.persistence
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import tempfile

from .models import Project, Cursor, Segment, Formula, FormulaResult


def save_project(project: Project, path):
    """Ghi cấu hình qua file tạm; bảo vệ log/DBC khỏi bị ghi đè."""
    target = Path(path).resolve()
    protected = [project.source, *project.dbc_map.values()]
    if any(p and target == Path(p).resolve() for p in protected):
        raise ValueError("Không được ghi đè file nguồn hoặc DBC.")
    target.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".tmp", dir=target.parent, delete=False) as f:
            name = f.name
            json.dump(project.to_dict(), f, ensure_ascii=False, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, target)
    finally:
        if name and Path(name).exists():
            Path(name).unlink()
    return target


def load_project(path) -> Project:
    """Đọc JSON, kiểm tra ID/thời gian và resolve đường dẫn theo thư mục project."""
    target = Path(path).resolve()
    data = json.loads(target.read_text(encoding="utf-8"))
    if data.get("schema_version", 1) != 1:
        raise ValueError("Phiên bản project không được hỗ trợ.")
    project = Project(**{k: v for k, v in data.items() if k in {"source", "dbc_map", "selected_signals", "cache_path", "schema_version"}})
    project.cursors = [Cursor(**row) for row in data.get("cursors", [])]
    project.segments = [Segment(**row) for row in data.get("segments", [])]
    project.formulas = [Formula(**row) for row in data.get("formulas", [])]
    project.results = [FormulaResult(**row) for row in data.get("results", [])]
    for cursor in project.cursors:
        if not math.isfinite(cursor.time):
            raise ValueError("Vị trí con trỏ không hợp lệ.")
    for segment in project.segments:
        segment.validate()
    for collection in (project.cursors, project.segments, project.formulas):
        if len({item.id for item in collection}) != len(collection):
            raise ValueError("Project có ID bị trùng.")
    cursor_ids = {cursor.id for cursor in project.cursors}
    segment_ids = {segment.id for segment in project.segments}
    for segment in project.segments:
        if any(link is not None and link not in cursor_ids for link in (segment.start_cursor, segment.end_cursor)):
            raise ValueError(f"Giai đoạn {segment.name} tham chiếu con trỏ không tồn tại.")
    for formula in project.formulas:
        if not set(formula.segment_ids).issubset(segment_ids):
            raise ValueError(f"Công thức {formula.name} tham chiếu giai đoạn không tồn tại.")
    # Đường dẫn tương đối tính từ file project để có thể sao chép cả thư mục.
    def resolve(value):
        return str((target.parent / value).resolve()) if value and not Path(value).is_absolute() else value
    project.source = resolve(project.source)
    project.cache_path = resolve(project.cache_path)
    project.dbc_map = {str(ch): resolve(dbc) for ch, dbc in project.dbc_map.items()}
    return project
