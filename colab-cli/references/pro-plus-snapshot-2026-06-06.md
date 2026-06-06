# Colab Pro+ Runtime Snapshot - 2026-06-06

This is an observed snapshot from one Colab Pro+ account using
`google-colab-cli==0.5.9` on 2026-06-06. It is not a guarantee. Colab resources,
availability, runtime lifetime, idle timeout, and compute-unit consumption vary
by account, subscription tier, current demand, region, and hardware choice.

The CLI-supported selectors at the time were:

- CPU: no accelerator flag
- GPU: `T4`, `L4`, `G4`, `H100`, `A100`
- TPU: `v5e1`, `v6e1`

## CLI Shape / High-Memory Limitation

The Colab web UI has high-memory choices, but `google-colab-cli==0.5.9` did not
expose a high-memory selector. In the installed source, `client.py` defines
`Shape.STANDARD` and `Shape.HIGH_RAM` for listed assignments, but assignment
creation only sends `variant` and `accelerator`; `commands/session.py` and
`commands/run.py` expose only `--gpu` and `--tpu`.

Observed UI behavior on this account:

- CPU-only: standard and high-memory choices available.
- T4: standard and high-memory choices available.
- A100: high-memory choice available.
- L4, TPU v5e-1, TPU v6e-1: appeared to use fixed high-memory shapes.

If a task specifically needs high-memory CPU/T4/A100, the agent should not use a
fake CLI flag. Ask the user to create the runtime in the web UI, attach/use it
from Colab, or first verify that a newer CLI release added shape support.

## Observed Allocations

| Selector | Allocation result | CPU | vCPU | RAM GiB | Disk GB | Disk write MB/s | Disk read MB/s | RAM copy GB/s | Accelerator / HBM | Speedtest down/up Mbps | Ping ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| CPU | allocated | Intel Xeon @ 2.20GHz | 2 | 12.7 | 225.83 | 158.39 | 5218.17 | 2.17 | none | 1643.9 / 453.5 | 32.9 |
| T4 | allocated | Intel Xeon @ 2.00GHz | 2 | 12.7 | 235.68 | 237.10 | 6582.86 | 2.72 | Tesla T4, 15360 MiB | 2951.8 / 799.2 | 13.4 |
| L4 | allocated | Intel Xeon @ 2.20GHz | 12 | 53.0 | 235.68 | 263.09 | 6372.52 | 2.73 | NVIDIA L4, 23034 MiB | 2733.0 / 940.3 | 3.2 |
| G4 | allocated on attempt 7 | AMD EPYC 9B45 | 48 | 176.9 | 235.68 | 295.45 | 28640.56 | 11.93 | NVIDIA RTX PRO 6000 Blackwell Server Edition, 97887 MiB | 1376.8 / 317.0 | 42.5 |
| A100 | allocated on attempt 6 | Intel Xeon @ 2.20GHz | 12 | 83.5 | 235.68 | 264.74 | 6712.55 | 2.77 | NVIDIA A100-SXM4-40GB, 40960 MiB | speedtest unavailable | - |
| A100 high-memory | user observed via web UI | - | - | high-memory | - | - | - | - | NVIDIA A100-SXM4-80GB, 81920 MiB | - | - |
| TPU v5e1 | allocated | AMD EPYC 7B13 | 24 | 47.0 | 225.33 | 112.12 | 15499.22 | 8.19 | TPU v5 lite, ~16.9 GB HBM limit | 622.7 / 215.2 | 39.6 |
| TPU v6e1 | allocated | AMD EPYC 9B14 | 44 | 172.9 | 225.33 | 409.06 | 17111.27 | 7.70 | TPU v6 lite, ~33.6 GB HBM limit | 769.9 / 187.8 | 40.9 |
| H100 | stopped after 41 failed attempts | - | - | - | - | - | - | - | not allocated through CLI during retry run | - | - |

## Approximate Compute Throughput

These are short dense matmul probes from the bundled benchmark script. They are
not full hardware benchmarks and should be used only for rough comparison.

| Selector | FP32 TFLOPS | FP16 TFLOPS | BF16 TFLOPS | Notes |
|---|---:|---:|---:|---|
| CPU standard | 0.067 | - | - | NumPy FP32 matmul, 2048x2048 |
| T4 | 3.40 | 49.59 | 2.36 | PyTorch matmul, 4096x4096, CUDA capability 7.5 |
| L4 | 12.64 | 83.57 | 85.37 | PyTorch matmul, 6144x6144, CUDA capability 8.9 |
| G4 | 73.85 | 290.06 | 372.87 | PyTorch matmul, 4096x4096, CUDA capability 12.0 |
| A100-SXM4-40GB | 19.03 | 293.05 | 295.24 | PyTorch matmul, 8192x8192, CUDA capability 8.0 |
| TPU v5e1 | 140.09 | 144.17 | 149.02 | JAX matmul, 4096x4096, device kind `TPU v5 lite` |
| TPU v6e1 | 381.40 | 359.72 | 383.21 | JAX matmul, 4096x4096, device kind `TPU v6 lite` |
| A100-SXM4-80GB | not measured with compute script | not measured | not measured | user observed allocation via web UI |
| H100 | not measured | not measured | not measured | stopped after 41 failed CLI allocation attempts |

## Compute-Unit Rate Handling And Observed Rates

Do not treat this file as a permanent price table. The CLI run did not expose
hourly compute-unit rates, and Google's public FAQ describes Colab resources and
limits as variable rather than guaranteed. These rates were observed in the
Colab UI by the user on 2026-06-06:

| Runtime / shape | UI-observed CU/hour |
|---|---:|
| CPU standard | ~0.08 |
| CPU high-memory | ~0.26 |
| T4 | ~1.27 |
| L4 | ~1.54 |
| TPU v5e-1 | ~2.92 |
| TPU v6e-1 | ~4.08 |
| A100-SXM4-80GB high-memory | ~6.77 |

Additional community reports found on 2026-06-06 conflicted with each other:

- H100 80GB was reported around ~18.05 CU/hour in a December 2025 Reddit
  thread, and users in the same thread reported frequent fallback/unavailability.
- G4 / RTX PRO 6000 Blackwell Server Edition was reported around ~6.71 CU/hour
  in a February 2026 Reddit thread.
- A100 40GB was reported around ~5.37 CU/hour in a December 2025 Reddit thread.
- Some newer comments claimed the most expensive Colab GPUs were closer to
  ~7 CU/hour. Because these are community reports and Colab rates can change,
  prefer the active runtime's UI value over any cached table.

For a live job, inspect the Colab UI resource/account panel for the active
runtime's current CU/hour value and record that task-local value before long
runs.

If an agent cannot read the UI, it should say the CU/hour value is not
CLI-discoverable, choose the lowest adequate runtime, and stop the session
promptly after the job.

## Reproduce

From the repository root after installing `google-colab-cli`:

```bash
mkdir -p benchmark-results
colab run --session codex-bench-cpu --timeout 600 \
  colab-cli/scripts/benchmark-runtime.py cpu > benchmark-results/cpu.json
colab run --session codex-bench-t4 --gpu T4 --timeout 600 \
  colab-cli/scripts/benchmark-runtime.py T4 > benchmark-results/T4.json
colab run --session codex-bench-l4 --gpu L4 --timeout 600 \
  colab-cli/scripts/benchmark-runtime.py L4 > benchmark-results/L4.json
colab run --session codex-bench-v5e1 --tpu v5e1 --timeout 600 \
  colab-cli/scripts/benchmark-runtime.py v5e1 > benchmark-results/v5e1.json
colab run --session codex-bench-v6e1 --tpu v6e1 --timeout 600 \
  colab-cli/scripts/benchmark-runtime.py v6e1 > benchmark-results/v6e1.json
colab sessions
```

`colab run` stops the session automatically unless `--keep` is passed. Still run
`colab sessions` afterward to verify cleanup.
