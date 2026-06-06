#!/usr/bin/env python3
"""Collect a compact Colab runtime profile.

Designed to run inside a Colab VM through:
  colab run [--gpu T4|--tpu v5e1] colab-cli/scripts/benchmark-runtime.py
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def run(cmd: list[str], timeout: int = 20) -> dict:
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": repr(exc)}


def read_text(path: str) -> str | None:
    try:
        return Path(path).read_text().strip()
    except Exception:
        return None


def cpu_info() -> dict:
    lscpu = run(["lscpu"])
    cpu_model = None
    if lscpu.get("ok"):
        for line in lscpu["stdout"].splitlines():
            if line.startswith("Model name:"):
                cpu_model = line.split(":", 1)[1].strip()
                break
    return {
        "machine": platform.machine(),
        "processor": platform.processor(),
        "model": cpu_model,
        "logical_cpus": os.cpu_count(),
        "lscpu": lscpu.get("stdout") if lscpu.get("ok") else None,
    }


def memory_info() -> dict:
    meminfo = read_text("/proc/meminfo") or ""
    parsed = {}
    for line in meminfo.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            parsed[key] = value.strip()
    return {
        "mem_total": parsed.get("MemTotal"),
        "mem_available": parsed.get("MemAvailable"),
        "swap_total": parsed.get("SwapTotal"),
    }


def disk_info() -> dict:
    usage = shutil.disk_usage("/content" if Path("/content").exists() else "/")
    return {
        "path": "/content" if Path("/content").exists() else "/",
        "total_gb": round(usage.total / 1024**3, 2),
        "free_gb": round(usage.free / 1024**3, 2),
        "df_h": run(["df", "-h"]).get("stdout"),
        "lsblk": run(["lsblk", "-o", "NAME,TYPE,SIZE,MODEL,MOUNTPOINT"]).get("stdout"),
    }


def disk_speed(size_mb: int = 512) -> dict:
    base = Path("/content") if Path("/content").exists() else Path(tempfile.gettempdir())
    path = base / f"colab_cli_disk_test_{os.getpid()}.bin"
    block = b"\0" * (4 * 1024 * 1024)
    blocks = max(1, size_mb // 4)
    try:
        start = time.perf_counter()
        with path.open("wb") as f:
            for _ in range(blocks):
                f.write(block)
            f.flush()
            os.fsync(f.fileno())
        write_s = time.perf_counter() - start
        start = time.perf_counter()
        with path.open("rb") as f:
            while f.read(4 * 1024 * 1024):
                pass
        read_s = time.perf_counter() - start
        actual_mb = blocks * 4
        return {
            "size_mb": actual_mb,
            "write_mb_s": round(actual_mb / write_s, 2),
            "read_mb_s": round(actual_mb / read_s, 2),
        }
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def ram_speed(size_mb: int = 512) -> dict:
    try:
        import numpy as np

        n = (size_mb * 1024 * 1024) // 8
        a = np.ones(n, dtype=np.float64)
        b = np.empty_like(a)
        start = time.perf_counter()
        np.copyto(b, a)
        copy_s = time.perf_counter() - start
        start = time.perf_counter()
        total = float(np.dot(a[: min(n, 20_000_000)], b[: min(n, 20_000_000)]))
        dot_s = time.perf_counter() - start
        return {
            "method": "numpy",
            "copy_size_mb": size_mb,
            "copy_gb_s": round((size_mb / 1024) / copy_s, 2),
            "dot_seconds": round(dot_s, 4),
            "dot_sample": total,
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc)}


def gpu_info() -> dict:
    nvidia_smi = run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version,compute_cap,pci.bus_id",
            "--format=csv,noheader",
        ]
    )
    torch_info = {}
    try:
        import torch

        torch_info = {
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count(),
            "devices": [
                {
                    "name": torch.cuda.get_device_name(i),
                    "capability": torch.cuda.get_device_capability(i),
                    "memory_gb": round(
                        torch.cuda.get_device_properties(i).total_memory / 1024**3, 2
                    ),
                }
                for i in range(torch.cuda.device_count())
            ],
        }
    except Exception as exc:  # noqa: BLE001
        torch_info = {"error": repr(exc)}
    return {"nvidia_smi": nvidia_smi, "torch": torch_info}


def gpu_compute_benchmark() -> dict:
    try:
        import torch

        if not torch.cuda.is_available():
            return {"available": False}
        device = torch.device("cuda")
        name = torch.cuda.get_device_name(0)
        capability = torch.cuda.get_device_capability(0)
        n = 4096
        if "A100" in name or "H100" in name:
            n = 8192
        elif "L4" in name:
            n = 6144
        results = {
            "available": True,
            "device": name,
            "cuda_capability": capability,
            "matrix_n": n,
            "note": "Approximate dense matmul throughput; task-specific kernels can differ.",
        }
        for label, dtype in (
            ("fp32", torch.float32),
            ("fp16", torch.float16),
            ("bf16", torch.bfloat16),
        ):
            try:
                a = torch.randn((n, n), device=device, dtype=dtype)
                b = torch.randn((n, n), device=device, dtype=dtype)
                for _ in range(2):
                    _ = a @ b
                torch.cuda.synchronize()
                start = torch.cuda.Event(enable_timing=True)
                end = torch.cuda.Event(enable_timing=True)
                iterations = 5
                start.record()
                for _ in range(iterations):
                    c = a @ b
                end.record()
                torch.cuda.synchronize()
                seconds = start.elapsed_time(end) / 1000.0 / iterations
                tflops = (2 * n**3) / seconds / 1e12
                results[label] = {
                    "seconds": round(seconds, 6),
                    "tflops": round(tflops, 2),
                    "output_sample": float(c.flatten()[0].detach().float().cpu()),
                }
                del a, b, c
                torch.cuda.empty_cache()
            except Exception as exc:  # noqa: BLE001
                results[label] = {"error": repr(exc)}
        return results
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "error": repr(exc)}


def tpu_info() -> dict:
    keys = [
        "COLAB_TPU_ADDR",
        "TPU_NAME",
        "TPU_WORKER_ID",
        "TPU_WORKER_HOSTNAMES",
        "TPU_WORKER_PORTS",
    ]
    info = {"env": {key: os.environ.get(key) for key in keys if os.environ.get(key)}}
    try:
        import jax

        devices = jax.devices()
        info["jax"] = {
            "version": jax.__version__,
            "default_backend": jax.default_backend(),
            "device_count": len(devices),
            "devices": [
                {
                    "id": getattr(device, "id", None),
                    "platform": getattr(device, "platform", None),
                    "device_kind": getattr(device, "device_kind", None),
                    "process_index": getattr(device, "process_index", None),
                }
                for device in devices
            ],
        }
        memory_stats = {}
        for i, device in enumerate(devices[:1]):
            try:
                memory_stats[f"device_{i}"] = device.memory_stats()
            except Exception as exc:  # noqa: BLE001
                memory_stats[f"device_{i}"] = {"error": repr(exc)}
        info["jax"]["memory_stats"] = memory_stats
    except Exception as exc:  # noqa: BLE001
        info["jax"] = {"error": repr(exc)}
    try:
        import tensorflow as tf

        info["tensorflow"] = {
            "version": tf.__version__,
            "logical_tpu_devices": [str(d) for d in tf.config.list_logical_devices("TPU")],
            "physical_tpu_devices": [str(d) for d in tf.config.list_physical_devices("TPU")],
        }
    except Exception as exc:  # noqa: BLE001
        info["tensorflow"] = {"error": repr(exc)}
    return info


def tpu_compute_benchmark() -> dict:
    try:
        import jax
        import jax.numpy as jnp

        if jax.default_backend() != "tpu":
            return {"available": False, "backend": jax.default_backend()}
        n = 4096
        results = {
            "available": True,
            "backend": jax.default_backend(),
            "matrix_n": n,
            "note": "Approximate single-host dense matmul throughput; topology and framework kernels can differ.",
        }

        def bench(dtype) -> dict:
            key = jax.random.PRNGKey(0)
            a = jax.random.normal(key, (n, n), dtype=dtype)
            b = jax.random.normal(key, (n, n), dtype=dtype)
            fn = jax.jit(lambda x, y: x @ y)
            fn(a, b).block_until_ready()
            iterations = 5
            start = time.perf_counter()
            out = None
            for _ in range(iterations):
                out = fn(a, b)
                out.block_until_ready()
            seconds = (time.perf_counter() - start) / iterations
            tflops = (2 * n**3) / seconds / 1e12
            return {
                "seconds": round(seconds, 6),
                "tflops": round(tflops, 2),
                "output_sample": float(out.reshape(-1)[0]),
            }

        for label, dtype in (
            ("fp32", jnp.float32),
            ("bf16", jnp.bfloat16),
            ("fp16", jnp.float16),
        ):
            try:
                results[label] = bench(dtype)
            except Exception as exc:  # noqa: BLE001
                results[label] = {"error": repr(exc)}
        return results
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "error": repr(exc)}


def cpu_compute_benchmark() -> dict:
    try:
        import numpy as np

        n = 2048
        a = np.random.randn(n, n).astype("float32")
        b = np.random.randn(n, n).astype("float32")
        start = time.perf_counter()
        c = a @ b
        seconds = time.perf_counter() - start
        tflops = (2 * n**3) / seconds / 1e12
        return {
            "matrix_n": n,
            "fp32": {
                "seconds": round(seconds, 6),
                "tflops": round(tflops, 3),
                "output_sample": float(c.reshape(-1)[0]),
            },
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc)}


def network_speed() -> dict:
    result = {"hostname": socket.gethostname()}
    speedtest = shutil.which("speedtest") or shutil.which("speedtest-cli")
    if not speedtest and os.environ.get("COLAB_CLI_INSTALL_SPEEDTEST", "1") != "0":
        install = run([sys.executable, "-m", "pip", "install", "-q", "speedtest-cli"], timeout=120)
        result["speedtest_cli_install"] = install
        speedtest = shutil.which("speedtest") or shutil.which("speedtest-cli")
    if speedtest:
        result["speedtest_cli"] = run([speedtest, "--json"], timeout=90)
    else:
        result["speedtest_cli"] = {"ok": False, "error": "speedtest-cli not installed"}

    # Lightweight fallback: download a fixed test file. This is not equivalent to
    # Speedtest.net, but catches obviously poor egress.
    url = "https://speed.cloudflare.com/__down?bytes=25000000"
    try:
        start = time.perf_counter()
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read()
        elapsed = time.perf_counter() - start
        result["cloudflare_download"] = {
            "bytes": len(data),
            "seconds": round(elapsed, 3),
            "mbps": round((len(data) * 8) / elapsed / 1_000_000, 2),
        }
    except Exception as exc:  # noqa: BLE001
        result["cloudflare_download"] = {"error": repr(exc)}
    return result


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("COLAB_CLI_BENCHMARK_LABEL", "")
    output = {
        "label": label,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version,
        "platform": platform.platform(),
        "cpu": cpu_info(),
        "memory": memory_info(),
        "disk": disk_info(),
        "disk_speed": disk_speed(),
        "ram_speed": ram_speed(),
        "gpu": gpu_info(),
        "gpu_compute": gpu_compute_benchmark(),
        "tpu": tpu_info(),
        "tpu_compute": tpu_compute_benchmark(),
        "cpu_compute": cpu_compute_benchmark(),
        "network": network_speed(),
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
