"""Regression checks for original timestamps on charts and the export screen."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6 import QtCore, QtWidgets

from vehiclelog.gui import ExportDialog, MainWindow
from vehiclelog.models import Project, Segment, SignalInfo
from vehiclelog.store import StoreWriter


@pytest.fixture(scope="session")
def native_app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def native_signals(tmp_path):
    # Different rates, offsets, gaps and fractional timestamps must remain independent.
    samples = {
        "voltage": (
            np.array([0.013, 0.024, 0.047, 0.103, 0.397, 1.1234567]),
            np.array([400, 401, 402, 399, 405, 410], dtype=float),
        ),
        "current": (
            np.array([0.037, 0.154, 0.271, 0.663, 1.1987654]),
            np.array([3, 7, -2, 12, 4], dtype=float),
        ),
    }
    with StoreWriter(tmp_path / "native-cache", {"duration": 1.2}) as writer:
        for key, (times, values) in samples.items():
            writer.add_signal(SignalInfo(key, key.title(), "V" if key == "voltage" else "A"))
            writer.append(key, times, values)
        store = writer.finish()
    return store, samples


@pytest.fixture
def native_window(native_app, native_signals):
    window = MainWindow()
    window.set_store(native_signals[0])
    yield window
    window._dirty = False
    window.close()
    window.deleteLater()
    native_app.processEvents()


def test_different_rates_remain_original_on_charts_after_zoom_and_fit(native_window, native_signals):
    _, originals = native_signals
    for key, (times, values) in originals.items():
        shown_times, shown_values = native_window.curves[key].getData()
        np.testing.assert_array_equal(shown_times, times)
        np.testing.assert_array_equal(shown_values, values)

    # Zooming clips each channel independently; it must not generate shared time rows.
    first_plot = next(iter(native_window.plots.values()))
    first_plot.setXRange(0.1, 0.7, padding=0)
    native_window._update_curves()
    for key, (times, values) in originals.items():
        selected = (times >= 0.1) & (times <= 0.7)
        shown_times, shown_values = native_window.curves[key].getData()
        np.testing.assert_array_equal(shown_times, times[selected])
        np.testing.assert_array_equal(shown_values, values[selected])

    native_window.fit_horizontal()
    for key, (times, values) in originals.items():
        shown_times, shown_values = native_window.curves[key].getData()
        np.testing.assert_array_equal(shown_times, times)
        np.testing.assert_array_equal(shown_values, values)


def test_reduced_plot_preview_uses_only_original_sample_times_and_values(tmp_path):
    increments = np.resize(np.array([0.0031, 0.0147, 0.0013, 0.0211]), 12_001)
    times = np.cumsum(increments)
    values = np.sin(np.arange(len(times)) / 13)
    values[103] = 1000
    values[10_009] = -500
    with StoreWriter(tmp_path / "preview-cache", {}) as writer:
        writer.add_signal(SignalInfo("x", "Irregular", "A"))
        writer.append("x", times, values)
        store = writer.finish()

    shown_times, shown_values = store.plot_data("x", max_points=80)
    assert 0 < len(shown_times) <= 80 < len(times)
    source_indexes = np.searchsorted(times, shown_times)
    np.testing.assert_array_equal(shown_times, times[source_indexes])
    np.testing.assert_array_equal(shown_values, values[source_indexes])
    assert shown_values.max() == 1000
    assert shown_values.min() == -500


def test_excel_dialog_removes_resampling_and_hides_mf4_options(native_app, native_signals):
    store, _ = native_signals
    project = Project(selected_signals=list(store.signals), source="source.blf")
    dialog = ExportDialog(store, project)
    try:
        dialog.show()
        native_app.processEvents()
        for removed in ("raster_check", "raster_spin", "interpolation", "max_gap"):
            assert not hasattr(dialog, removed)
        assert dialog.format_combo.currentData() == "excel"
        assert not dialog.zero_check.isVisible()
        assert not dialog.derived_check.isVisible()
        assert dialog.signal_list.isEnabled()

        dialog.format_combo.setCurrentIndex(dialog.format_combo.findData("mf4"))
        assert dialog.zero_check.isVisible()
        assert dialog.derived_check.isVisible()
        dialog.format_combo.setCurrentIndex(dialog.format_combo.findData("raw"))
        assert dialog.zero_check.isVisible()
        assert not dialog.derived_check.isVisible()
        assert not dialog.signal_list.isEnabled()

        dialog.format_combo.setCurrentIndex(dialog.format_combo.findData("excel"))
        assert not dialog.zero_check.isVisible()
        assert not dialog.derived_check.isVisible()
        assert dialog.signal_list.isEnabled()
    finally:
        dialog.close()
        dialog.deleteLater()
        native_app.processEvents()


def test_excel_controller_passes_selection_without_time_conversion_options(
    native_window, native_signals, tmp_path, monkeypatch
):
    from vehiclelog import exports
    from vehiclelog.ui.controllers import exports as controller

    store, _ = native_signals
    segment = Segment("Middle", 0.1, 0.7)
    project = native_window.project
    project.segments = [segment]
    destination = tmp_path / "native.xlsx"
    actual_dialog = ExportDialog

    class AcceptedDialog(actual_dialog):
        def exec(self):
            # Stale MF4 choices from switching formats must not affect Excel.
            self.zero_check.setChecked(True)
            self.derived_check.setChecked(True)
            self.whole_check.setChecked(False)
            self.segment_list.item(0).setCheckState(QtCore.Qt.CheckState.Checked)
            return QtWidgets.QDialog.DialogCode.Accepted

    observed = []

    def export_excel(store_arg, destination_arg, **kwargs):
        observed.append((store_arg, destination_arg, kwargs))
        return destination

    def run_immediately(description, work, complete):
        complete(work(lambda *_: None, None))

    monkeypatch.setattr(controller, "ExportDialog", AcceptedDialog)
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *_: (str(destination), ""))
    monkeypatch.setattr(exports, "export_excel", export_excel)
    monkeypatch.setattr(native_window, "_run_task", run_immediately)

    native_window.export_data()
    assert len(observed) == 1
    store_arg, destination_arg, options = observed[0]
    assert store_arg is store
    assert destination_arg == str(destination)
    assert options["keys"] == list(store.signals)
    assert options["segments"] == [segment]
    assert set(options) == {"keys", "segments", "formulas", "results", "progress", "token"}
