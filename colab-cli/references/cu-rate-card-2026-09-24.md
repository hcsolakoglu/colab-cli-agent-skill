# Compute-Unit Rate Card - 2026-09-24

Dated snapshot of measured Colab compute-unit (CU) consumption per backend.
Account/region/tier-specific: measured on a pay-as-you-go CU account
(`cansolakoglu130@gmail.com` via gcloud ADC) in region `asia-east1` with
`google-colab-cli` 0.7.2. Rates and provisioned hardware vary by region,
demand, tier, and over time. Do not hardcode these as universal truth;
re-measure with `colab usage` for current numbers.

## Method

One short-lived session per backend config. While exactly one assignment was
active, the account-level hourly burn rate was read from `colab usage`
(`GET /tun/m/ccu-info`), then the session was stopped immediately (~1-2 min
each). Total sweep cost: 0.14 CU. Hardware verified per backend with
`colab run` executing an inventory script (lscpu, /proc/cpuinfo, /proc/meminfo,
df, nvidia-smi, jax devices). Safe fields only: no hostname, IPs, MACs,
usernames, or env vars. All backends: Ubuntu 24.04, Python 3.13.15, GPU
driver 580.82.07.

## Rates (CU/hour) + provisioned hardware

| Backend | Flags | CU/hr | Accelerator | VRAM | CPU | MHz | vCPU | RAM | Disk |
|---|---|---|---|---|---|---|---|---|---|
| CPU | std | 0.08 | - | - | Intel Xeon @ 2.20GHz | 2200 | 2 | 13G | 226G |
| CPU | `--high-mem` | 0.26 | - | - | AMD EPYC 7B12 | 2250 | 8 | 51G | 226G |
| T4 | `--gpu T4` | 1.07 | Tesla T4 | 16G | Intel Xeon @ 2.00GHz | 2000 | 2 | 13G | 236G |
| T4 | `--gpu T4 --high-mem` | 1.27 | Tesla T4 | 16G | Intel Xeon @ 2.00GHz | 2000 | 8 | 53G | 236G |
| L4 | `--gpu L4` | 1.54 | NVIDIA L4 | 22.5G | Intel Xeon @ 2.20GHz | 2200 | 12 | 53G | 236G |
| L4 | `--gpu L4 --high-mem` | 1.54 | NVIDIA L4 | 22.5G | (same) | 2200 | 12 | 53G | 236G |
| G4 | `--gpu G4` | 8.90 | RTX PRO 6000 Blackwell SE | 96G | AMD EPYC 9B45 | 2700-4150 boost | 48 | 185G | 236G |
| G4 | `--gpu G4 --high-mem` | n/a | no high-RAM G4 shape exists; backend rejects shape=hm deliberately |
| A100 | `--gpu A100` | 5.30 | A100-SXM4-**40GB** | 40G | Intel Xeon @ 2.20GHz | 2200 | 12 | 87G | 236G |
| A100 | `--gpu A100 --high-mem` | 6.77 | A100-SXM4-**80GB** | 80G | Intel Xeon @ 2.20GHz | 2200 | 12 | 175G | 236G |
| H100 | `--gpu H100` | n/a | 503 Service Unavailable on 3 attempts; in Pro+ catalog but effectively unallocatable on this account |
| TPU v5e1 | `--tpu v5e1` (+ `--high-mem`: n/a, single shape) | 2.92 | TPU v5 lite x1 (jax) | - | AMD EPYC 7B13 | 2450 | 24 | 49G | 226G |
| TPU v6e1 | `--tpu v6e1` (+ `--high-mem`: n/a, single shape) | 4.08 | TPU v6 lite x1 (jax) | - | AMD EPYC 9B14 | 2600 | 44 | 172G | 226G |

Hours per 100 CU: CPU 1250, CPU-hm 385, T4 93, T4-hm 79, L4 65, G4 11,
A100 19, A100-hm 15, v5e1 34, v6e1 25.

## Notes

- A100 standard provisions the **40GB** variant; `--high-mem` provisions the
  **80GB** variant. Colab auto-selects the variant; the 5.30 rate was measured
  on 40GB.
- L4, TPU v5e1, and TPU v6e1 exist in a **single machine shape only**
  (`HIGH_MEM_ONLY_ACCELERATORS` in google-colab-cli 0.7.2 source): the CLI
  drops `--high-mem` client-side with a warning, so there is no separate
  high-mem combination for them.
- G4 high-mem: no high-RAM G4 shape exists at all. The backend rejects it
  deliberately ("Backend rejected accelerator 'G4'. You may not have quota or
  entitlement for this accelerator on your account."); the standard G4 VM is
  already 185GB RAM / 48 vCPU.
- H100: exists in the Pro+ catalog (third-party refs list it ~18 CU/hr) but
  the assign endpoint returns 503 Service Unavailable. Three failed attempts
  on 2026-09-24; 41 failed attempts were also recorded on 2026-06-06 on this
  account. Capacity/entitlement scarcity, effectively persistent here.
- TPU `new` can hit the CLI's 120s read timeout while the assignment still
  materializes server-side, leaving an orphan that burns CU until unassigned.
