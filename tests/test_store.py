import numpy as np
import pytest

from vehiclelog.models import SignalInfo, Project, Segment, Formula, Cursor
from vehiclelog.store import StoreWriter, SignalStore, cache_key
from vehiclelog.project import save_project, load_project


def test_duplicate_boundaries_and_window(tmp_path):
    with StoreWriter(tmp_path / "cache") as writer:
        writer.add_signal(SignalInfo("u", "Voltage", "V"))
        writer.append("u", [0, 1, 1, 2], [10, 11, 12, 13])
        writer.append("u", [2, 3, 4], [99, 14, 15])
        store = writer.finish()
    assert store.signals["u"].count == 5
    t, v = store.read("u", 1.5, 2.5, neighbors=True)
    np.testing.assert_array_equal(t, [1, 2, 3])
    np.testing.assert_array_equal(v, [12, 99, 14])
    assert len(list(store.iter_chunks("u", chunk_size=2))) == 3


def test_unfinished_cache_cleanup_and_backward_time(tmp_path):
    with pytest.raises(ValueError):
        with StoreWriter(tmp_path / "bad") as writer:
            writer.add_signal(SignalInfo("x", "x"))
            writer.append("x", [2, 3], [2, 3])
            writer.append("x", [1], [1])
    assert not list(tmp_path.iterdir())


def test_plot_envelope_preserves_spike_and_invalid(tmp_path):
    with StoreWriter(tmp_path / "cache") as writer:
        writer.add_signal(SignalInfo("x", "x"))
        values = np.zeros(10000)
        values[1234], values[7890], values[5000] = 999, -999, np.nan
        writer.append("x", np.arange(10000), values)
        store = writer.finish()
    t, v = store.plot_data("x", max_points=100)
    assert len(t) <= 100
    assert np.nanmax(v) == 999 and np.nanmin(v) == -999
    assert np.isnan(v).any()


def test_cache_fingerprint_and_tamper(tmp_path):
    source, dbc = tmp_path / "a.blf", tmp_path / "a.dbc"
    source.write_bytes(b"log")
    dbc.write_text("abc")
    before = cache_key(source, {1: dbc})
    dbc.write_text("xyz")
    assert before != cache_key(source, {1: dbc})
    with StoreWriter(tmp_path / "cache") as writer:
        writer.add_signal(SignalInfo("a", "a"))
        writer.append("a", [0], [1])
        store = writer.finish()
    next(store.path.glob("*.v")).write_bytes(b"")
    with pytest.raises(ValueError, match="Cache"):
        SignalStore(store.path)


def test_project_roundtrip_and_protect_source(tmp_path):
    project = Project(source=str(tmp_path / "a.blf"), cursors=[Cursor("M1", 1)], segments=[Segment("A", 1, 2)])
    project.formulas = [Formula("E", "integral(U)", {"U": "u"}, segment_ids=[project.segments[0].id])]
    path = save_project(project, tmp_path / "project.vls.json")
    loaded = load_project(path)
    assert loaded.to_dict() == project.to_dict()
    with pytest.raises(ValueError):
        save_project(project, tmp_path / "a.blf")


def test_project_rejects_dangling_assignments(tmp_path):
    project = Project(segments=[Segment("A", 0, 1)])
    project.formulas = [Formula("E", "1", {}, segment_ids=["missing"])]
    target = save_project(project, tmp_path / "bad.json")
    with pytest.raises(ValueError, match="giai đoạn không tồn tại"):
        load_project(target)
