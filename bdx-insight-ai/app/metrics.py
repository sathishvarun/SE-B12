"""Measures what each question costs: wall time, CPU time and memory of the API process."""
from __future__ import annotations

import time
from contextlib import contextmanager

import psutil

_proc = psutil.Process()


class Usage:
    latency_ms = 0
    cpu_ms = 0
    mem_mb = 0.0


@contextmanager
def measure():
    u = Usage()
    t0 = time.perf_counter()
    c0 = _proc.cpu_times()
    try:
        yield u
    finally:
        c1 = _proc.cpu_times()
        u.latency_ms = int((time.perf_counter() - t0) * 1000)
        u.cpu_ms = int(((c1.user - c0.user) + (c1.system - c0.system)) * 1000)
        u.mem_mb = round(_proc.memory_info().rss / 1_048_576, 1)


def server_snapshot() -> dict:
    vm = psutil.virtual_memory()
    du = psutil.disk_usage("/")
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "ram_used_gb": round(vm.used / 1e9, 2), "ram_total_gb": round(vm.total / 1e9, 2),
        "ram_percent": vm.percent,
        "disk_percent": du.percent,
        "api_process_mb": round(_proc.memory_info().rss / 1_048_576, 1),
    }
