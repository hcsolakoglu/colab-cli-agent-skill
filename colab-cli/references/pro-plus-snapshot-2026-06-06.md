# Colab Pro+ Runtime Snapshot - 2026-06-06

This is an observed snapshot from one Colab Pro+ account using
`google-colab-cli==0.5.9` on 2026-06-06. It is not a guarantee. Colab resources,
availability, runtime lifetime, idle timeout, and compute-unit consumption vary
by account, subscription tier, current demand, region, and hardware choice.

The CLI-supported selectors at the time were:

- CPU: no accelerator flag
- GPU: `T4`, `L4`, `G4`, `H100`, `A100`
- TPU: `v5e1`, `v6e1`

## Observed Allocations

| Selector | Allocation result | CPU | vCPU | RAM GiB | Disk GB | Disk write MB/s | Disk read MB/s | RAM copy GB/s | Accelerator | Speedtest down/up Mbps | Ping ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| CPU | allocated | Intel Xeon @ 2.20GHz | 2 | 12.7 | 225.83 | 158.39 | 5218.17 | 2.17 | none | 1643.9 / 453.5 | 32.9 |
| T4 | allocated | Intel Xeon @ 2.00GHz | 2 | 12.7 | 235.68 | 162.20 | 6033.75 | 2.60 | Tesla T4, 15360 MiB | 2709.6 / 534.3 | 13.9 |
| L4 | allocated | Intel Xeon @ 2.20GHz | 12 | 53.0 | 235.68 | 265.92 | 6615.97 | 2.74 | NVIDIA L4, 23034 MiB | 2632.4 / 923.7 | 3.2 |
| TPU v5e1 | allocated | AMD EPYC 7B13 | 24 | 47.0 | 225.33 | 112.12 | 15499.22 | 8.19 | TPU env present | 622.7 / 215.2 | 39.6 |
| TPU v6e1 | allocated | AMD EPYC 9B14 | 44 | 172.9 | 225.33 | 409.06 | 17111.27 | 7.70 | TPU env present | 769.9 / 187.8 | 40.9 |
| G4 | unavailable | - | - | - | - | - | - | - | request returned Service Unavailable | - | - |
| A100 | unavailable | - | - | - | - | - | - | - | request returned Service Unavailable | - | - |
| H100 | unavailable | - | - | - | - | - | - | - | request returned Service Unavailable | - | - |

## Compute-Unit Rate Handling

Do not treat this file as a CU/hour price table. The CLI run did not expose
hourly compute-unit rates, and Google's public FAQ describes Colab resources and
limits as variable rather than guaranteed. For a live job, inspect the Colab UI
resource/account panel for the active runtime's current CU/hour value and record
that task-local value before long runs.

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
