"""Kiểm tra giai đoạn liền kề và giữ đúng lựa chọn công thức khi chia/gộp."""
from dataclasses import replace

import pytest

from vehiclelog.models import Cursor, Formula, Project, Segment
from vehiclelog.stages import synchronize_stages


def _project():
    project = Project(cursors=[Cursor("x", t) for t in (0, 10, 20)])
    synchronize_stages(project)
    return project


def test_adjacent_pairs_sorted_and_numbered():
    project = Project(cursors=[Cursor("z", t, locked=True) for t in (30, 0, 20, 10)])
    synchronize_stages(project)
    assert [c.name for c in project.cursors] == ["M1", "M2", "M3", "M4"]
    assert not any(c.locked for c in project.cursors)
    assert [(s.start, s.end) for s in project.segments] == [(0, 10), (10, 20), (20, 30)]
    assert all((s.start_cursor, s.end_cursor) == (a.id, b.id)
               for s, a, b in zip(project.segments, project.cursors, project.cursors[1:]))


def test_moving_middle_keeps_ids_and_formula_assignment():
    project = _project()
    ids = [s.id for s in project.segments]
    project.formulas = [Formula("E", "integral(P)", {}, segment_ids=[ids[1]])]
    project.cursors[1].time = 12
    synchronize_stages(project)
    assert [s.id for s in project.segments] == ids
    assert [(s.start, s.end) for s in project.segments] == [(0, 12), (12, 20)]
    assert project.formulas[0].segment_ids == [ids[1]]
    assert not synchronize_stages(project)


def test_split_inherits_selected_scope_and_merge_does_not_broaden_partial_choice():
    project = _project()
    project.formulas = [Formula("E", "1", {}, segment_ids=[project.segments[0].id])]
    project.cursors.append(Cursor("", 5))
    synchronize_stages(project)
    assert [(s.start, s.end) for s in project.segments] == [(0, 5), (5, 10), (10, 20)]
    assert project.formulas[0].segment_ids == [s.id for s in project.segments[:2]]
    # Chỉ chọn nửa đầu rồi xóa mốc 5: không tự gán công thức cho cả 0–10.
    project.formulas[0].segment_ids = [project.segments[0].id]
    project.cursors.pop(1)
    synchronize_stages(project)
    assert [(s.start, s.end) for s in project.segments] == [(0, 10), (10, 20)]
    assert project.formulas[0].segment_ids == []


def test_merging_fully_selected_intervals_keeps_assignment():
    project = _project()
    project.formulas = [Formula("E", "1", {}, segment_ids=[s.id for s in project.segments])]
    project.cursors.pop(1)
    synchronize_stages(project)
    assert len(project.segments) == 1
    assert project.formulas[0].segment_ids == [project.segments[0].id]


def test_legacy_manual_scopes_convert_to_adjacent_pairs():
    project = Project(cursors=[Cursor("x", t) for t in (0, 10, 20, 30)],
                      segments=[Segment("Whole", 0, 30), Segment("Urban", 10, 20)])
    project.formulas = [Formula("Whole energy", "1", {}, segment_ids=[project.segments[0].id]),
                        Formula("Urban energy", "1", {}, segment_ids=[project.segments[1].id])]
    synchronize_stages(project)
    assert len(project.segments) == 3
    assert project.formulas[0].segment_ids == [s.id for s in project.segments]
    assert project.formulas[1].segment_ids == [project.segments[1].id]
    assert project.segments[1].name == "Urban"


def test_zero_or_one_marker_and_duplicate_legacy_markers():
    project = Project(cursors=[Cursor("a", 0), Cursor("b", 0)])
    synchronize_stages(project)
    assert len(project.cursors) == 1 and project.segments == []
    project.cursors.clear()
    synchronize_stages(project)
    assert project.segments == []


def test_nonfinite_marker_rejected():
    with pytest.raises(ValueError):
        synchronize_stages(Project(cursors=[Cursor("bad", float("nan"))]))
