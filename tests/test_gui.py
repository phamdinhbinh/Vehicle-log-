"""Headless checks for the desktop's data and analysis interactions."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6 import QtCore, QtWidgets

from vehiclelog.gui import FormulaDialog, MainWindow
from vehiclelog.models import Formula, FormulaResult, Segment, SignalInfo
from vehiclelog.store import StoreWriter


@pytest.fixture(scope="session")
def app():
    instance = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield instance


@pytest.fixture
def store(tmp_path):
    with StoreWriter(tmp_path / "store", {"source": "synthetic.blf", "duration": 5.0}) as writer:
        for key, name, unit, values in (
            ("voltage", "BatteryVoltage", "V", [400, 400, 400, 400, 400, 400]),
            ("current", "BatteryCurrent", "A", [10, 20, 10, -5, 0, 10]),
            ("speed", "VehicleSpeed", "km/h", [0, 10, 20, 30, 20, 0]),
        ):
            writer.add_signal(SignalInfo(key=key, name=name, unit=unit, channel="1"))
            writer.append(key, np.arange(6, dtype=float), np.asarray(values, dtype=float))
        return writer.finish()


@pytest.fixture
def window(app, store):
    instance = MainWindow()
    instance.set_store(store)
    yield instance
    instance._dirty = False
    instance.close()
    instance.deleteLater()
    app.processEvents()


def _item_with_key(widget, key):
    return next(
        widget.item(index)
        for index in range(widget.count())
        if widget.item(index).data(QtCore.Qt.ItemDataRole.UserRole) == key
    )


def test_store_signals_can_be_selected_and_removed_from_plot(window, app):
    assert window.signal_list.count() == 3
    item = _item_with_key(window.signal_list, "voltage")
    item.setCheckState(QtCore.Qt.CheckState.Checked)
    app.processEvents()

    assert "voltage" in window.project.selected_signals
    assert "voltage" in window.plots
    curves = window.plots["voltage"].listDataItems()
    assert curves
    times, values = curves[0].getData()
    np.testing.assert_array_equal(times, np.arange(6, dtype=float))
    np.testing.assert_array_equal(values, np.full(6, 400.0))

    item.setCheckState(QtCore.Qt.CheckState.Unchecked)
    app.processEvents()
    assert "voltage" not in window.project.selected_signals
    assert "voltage" not in window.plots


def test_linked_cursor_updates_segment_and_invalidates_results(window):
    window.add_cursor(time=1.0)
    cursor = window.project.cursors[-1]
    segment = Segment("Urban", 1.0, 4.0, start_cursor=cursor.id)
    window.add_segment(segment)
    window.project.results = [
        FormulaResult("energy", "Battery energy", segment.id, segment.name, 0.01, "kWh")
    ]

    window._sync_cursor(cursor.id, 1.5)

    assert cursor.time == pytest.approx(1.5)
    assert segment.start == pytest.approx(1.5)
    assert segment.end == pytest.approx(4.0)
    assert not window.project.results


def test_formula_dialog_preserves_explicit_stage_assignments(app, store):
    urban = Segment("Urban", 0.0, 2.0)
    hill = Segment("Hill", 2.0, 5.0)
    original = Formula(
        "Battery energy",
        "integral(U * I) / 3600000",
        {"U": "voltage", "I": "current"},
        unit="kWh",
        segment_ids=[hill.id],
    )
    dialog = FormulaDialog(store, [urban, hill], original)
    try:
        result = dialog.formula_value()
        assert result.name == original.name
        assert result.expression == original.expression
        assert result.bindings == original.bindings
        assert result.unit == "kWh"
        assert result.segment_ids == [hill.id]

        _item_with_key(dialog.segment_list, urban.id).setCheckState(QtCore.Qt.CheckState.Checked)
        result = dialog.formula_value()
        assert set(result.segment_ids) == {urban.id, hill.id}

        for index in range(dialog.segment_list.count()):
            dialog.segment_list.item(index).setCheckState(QtCore.Qt.CheckState.Unchecked)
        # No checkboxes means no assignment; it must never mean "all stages".
        assert dialog.formula_value().segment_ids == []
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


@pytest.mark.parametrize("expression", ["__import__('os').system('echo unsafe')", "U.__class__", "unknown + 1"])
def test_formula_dialog_rejects_unsafe_or_unbound_expressions(app, store, expression):
    segment = Segment("Urban", 0.0, 5.0)
    formula = Formula("Energy", "integral(U)", {"U": "voltage"}, segment_ids=[segment.id])
    dialog = FormulaDialog(store, [segment], formula)
    try:
        dialog.expression_edit.setText(expression)
        with pytest.raises(ValueError):
            dialog.formula_value()
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


def _wait_until(app, condition, timeout=5.0):
    import time
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()
    assert condition(), "Qt worker did not finish before the timeout"


def test_large_plot_preview_uses_background_and_cursor_reuses_cache(window, app, monkeypatch):
    import threading
    gui_thread = threading.get_ident()
    calls = []
    original = window.store.plot_data

    def observed(key, *args, **kwargs):
        if key == "voltage":
            calls.append(threading.get_ident())
        return original(key, *args, **kwargs)

    # Trigger the large-channel path without manufacturing a large on-disk log.
    window.store.signals["voltage"].count = 100_001
    monkeypatch.setattr(window.store, "plot_data", observed)
    window._preview_cache.clear()
    window._update_curves()
    _wait_until(app, lambda: window._preview_thread is None)
    assert calls
    assert all(thread_id != gui_thread for thread_id in calls)
    previous_calls = len(calls)
    cursor = window.project.cursors[0]
    window._sync_cursor(cursor.id, 1.25)
    app.processEvents()
    assert len(calls) == previous_calls


def test_background_job_result_is_delivered_on_gui_thread(window, app):
    import threading
    gui_thread = threading.get_ident()
    observations = []

    def work(progress, token):
        assert threading.get_ident() != gui_thread
        progress(0.5, "Working")
        token.check()
        return 42

    def finished(result):
        observations.append((result, threading.get_ident()))

    window._run_task("Test", work, finished)
    _wait_until(app, lambda: window._worker is None)
    assert observations == [(42, gui_thread)]
    assert not window.progress_bar.isVisible()


def test_export_subrange_requires_explicit_segment_choice(app, store, monkeypatch):
    from vehiclelog.gui import ExportDialog
    from vehiclelog.models import Project
    segment = Segment("Urban", 0, 5)
    dialog = ExportDialog(store, Project(selected_signals=["voltage"], segments=[segment]))
    notifications = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", lambda *args: notifications.append(args[1]))
    try:
        dialog.whole_check.setChecked(False)
        dialog.accept()
        assert dialog.result() != QtWidgets.QDialog.DialogCode.Accepted
        assert "Chưa chọn giai đoạn" in notifications
        dialog.segment_list.item(0).setCheckState(QtCore.Qt.CheckState.Checked)
        dialog.accept()
        assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted
        assert dialog.selected_segments() == [segment]
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


def test_formula_preview_bounds_memory_preserves_peaks_and_gap(monkeypatch):
    from vehiclelog import formulas
    from vehiclelog.gui import trace_preview
    segment = Segment("Long stage", 0, 100)
    formula = Formula("Power", "x", {"x": "voltage"}, segment_ids=[segment.id])
    times = np.linspace(0, 100, 100_001)
    values = np.ones(len(times))
    values[100] = 1000
    values[90_000] = -500
    values[50_000:51_000] = np.nan

    def chunks(*args, **kwargs):
        for start in range(0, len(times), 10_000):
            yield times[start:start+10_000], values[start:start+10_000]

    monkeypatch.setattr(formulas, "iter_evaluate_trace", chunks)
    display_times, display_values = trace_preview(None, formula, segment)
    assert len(display_times) <= 4000
    assert np.all(display_times[1:] >= display_times[:-1])
    assert np.nanmax(display_values) == 1000
    assert np.nanmin(display_values) == -500
    assert np.any(np.isnan(display_values))
