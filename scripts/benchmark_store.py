"""Synthetic store/formula benchmark; this is not a 3 GB BLF qualification.

Run: .venv/bin/python scripts/benchmark_store.py --samples 1000001 --chunk 100000
Peak RSS includes NumPy, working buffers and resident memory-mapped file pages.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from vehiclelog.formulas import evaluate_formula
from vehiclelog.models import Formula, Segment, SignalInfo
from vehiclelog.store import StoreWriter


def peak_rss_mib():
    try:
        import resource
    except ImportError:
        return None
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 * 1024 if sys.platform == "darwin" else 1024)


def benchmark(samples=1_000_001, chunk=100_000):
    if samples < 2 or chunk < 1:
        raise ValueError("samples must be >=2; chunk must be >=1")
    initial_rss = peak_rss_mib()
    dt = 0.01
    expected_integral = 0.0
    with tempfile.TemporaryDirectory(prefix="vehiclelog-benchmark-") as directory:
        started = time.perf_counter()
        with StoreWriter(Path(directory) / "store", {"source": "synthetic benchmark"}) as writer:
            writer.add_signal(SignalInfo("U", "Voltage", "V"))
            writer.add_signal(SignalInfo("I", "Current", "A"))
            for offset in range(0, samples, chunk):
                stop = min(samples, offset + chunk)
                indices = np.arange(offset, stop, dtype=np.int64)
                timestamps = indices.astype(np.float64) * dt
                voltage = np.full(len(indices), 400.0)
                # 100 s discharge / regeneration blocks, using integer indices.
                current = np.where((indices // 10_000) % 2 == 0, 50.0, -10.0)
                writer.append("U", timestamps, voltage)
                writer.append("I", timestamps, current)
                expected_integral += float(np.sum(current[indices < samples - 1])) * 400.0 * dt
            store = writer.finish()
        write_seconds = time.perf_counter() - started
        written_rss = peak_rss_mib()
        segment = Segment("Entire measurement", 0, (samples - 1) * dt)
        formula = Formula("Net energy", "integral(U * I) / 3600000",
                          {"U": "U", "I": "I"}, "kWh", [segment.id], max_gap=0.02)
        started = time.perf_counter()
        result = evaluate_formula(store, formula, segment)
        compute_seconds = time.perf_counter() - started
        if result.status != "ok" or not np.isclose(result.value, expected_integral / 3_600_000,
                                                     atol=1e-8, rtol=1e-9):
            raise AssertionError(f"Incorrect result: {result}")
        return {
            "samples_per_signal": samples, "signals": 2,
            "decoded_values_total": samples * 2, "write_chunk": chunk,
            "disk_bytes": sum(p.stat().st_size for p in store.path.iterdir()),
            "write_seconds": round(write_seconds, 4),
            "formula_seconds": round(compute_seconds, 4),
            "baseline_peak_rss_mib": initial_rss,
            "after_write_peak_rss_mib": written_rss,
            "after_formula_peak_rss_mib": peak_rss_mib(),
            "energy_kwh": result.value,
            "expected_energy_kwh": expected_integral / 3_600_000,
            "status": result.status,
            "note": "Synthetic disk-store test only; RSS includes resident mmap pages. Not a 3GB BLF benchmark.",
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=1_000_001)
    parser.add_argument("--chunk", type=int, default=100_000)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.samples, args.chunk), indent=2))
