# Colab Session Resilience and Legacy rclone Field Notes — verified 2026-10-01

Use this reference when a long-running or paid Colab session must survive CLI
updates, local state loss, auth changes, watchdog failures, or when an existing
job already uses the legacy rclone Drive mount.

These are field lessons from live Colab CLI jobs. They are not all upstream
contracts. Re-check behavior after CLI upgrades.

## 1. A missing local session does not prove the VM stopped

A live server-side assignment can outlive its entry in
`~/.config/colab-cli/sessions.json`. This was observed after a CLI
update/token-refresh path: the VM remained allocated and billable while every
`-s NAME` command returned `Session not found`.

Treat these together as an orphaned-session signal:

- `colab stop/exec/download -s NAME` says `Session not found`.
- Server inventory still shows an assignment, sometimes as an unnamed/`[?]`
  endpoint.
- Compute usage remains non-zero.

Do not allocate a replacement or assume cleanup succeeded until server-side
assignments are reconciled.

Mechanism seen in the fork's session lookup (`common.py`, e179094): when a
cached runtime token is near expiry, the CLI lists assignments and prunes the
local record if its endpoint is absent from that one listing, with no retry.
If that listing ever misses a live assignment (inferred, not reproduced), the
name is lost while the VM stays billable. Check for orphans after long idle
gaps and token refreshes, not only after upgrades.

### Safe recovery pattern

Before risky CLI work or immediately after `colab new`, record a private
name -> endpoint mapping. If the CLI forgets the name but the endpoint remains
assigned, rebuild local session state from the live assignment and fresh runtime
proxy info. Never restore a stale `sessions.json` backup: runtime proxy tokens
expire.

A last-resort cleanup path may release the known endpoint directly through the
CLI's control-plane client when named `colab stop` cannot reach it. Never
release an unknown assignment just because it lacks a local name.

## 2. Do not upgrade or replace Colab CLI underneath a valuable live job

Prefer this order:

1. Finish or checkpoint the current job.
2. Download/verify required outputs.
3. Stop and confirm the remote assignment is gone.
4. Upgrade/reinstall/switch fork.
5. Start the next session on the new CLI.

If an in-place upgrade is unavoidable, first snapshot live name -> endpoint
state and private auth configuration, then verify every assignment afterward.

Do not migrate an active job from rclone to persistent DriveFS, or vice versa,
mid-run merely because a newer transport exists. Keep the current mount until a
safe checkpoint/resume boundary unless the transport itself has failed.

## 3. Private auth backup rules

Useful private recovery inputs can include:

- `~/.config/colab-cli/token.json`
- `~/.config/colab-cli/settings.json`
- `~/.config/colab-cli/drive-mount-client.json`
- `~/.config/colab-cli/drive-mount-auth.json`
- legacy `~/.config/rclone/rclone.conf` when jobs still depend on it

Store recovery copies under a private directory (0700) with files 0600. Never
log or commit their contents. Do not overwrite a known-good backup with a
missing or zero-byte source file.

Do not back up/restore `sessions.json` as an auth artifact. Heal session state
from live assignments instead.

Permission tests can be misleading on NTFS or other filesystems that do not
honor POSIX mode bits. Validate 0600/0700 behavior on the actual Linux
filesystem used for `~/.config`, not an NTFS test temp directory.

## 4. Spend watchdog design for paid sessions

For long paid jobs, launch a watchdog detached from the agent process. It should
have independent limits for:

- job CU cap,
- account CU floor,
- wall-clock deadline,
- maximum consecutive failures to read usage.

Recommended control flow:

1. Snapshot session/endpoint state when watchdog starts.
2. Read `colab usage` with a bounded timeout.
3. Estimate spend conservatively from both balance drop and elapsed time x
   observed peak rate.
4. Heal known orphaned session state during each poll.
5. On stop trigger: named stop -> heal/retry -> known-endpoint release.
6. Exit after the stop path; verify server inventory separately.

Set `LC_ALL=C` for scripts that parse numeric CLI output with awk/printf. A
Turkish locale can render decimal commas and silently break numeric comparisons.

Fail safe when usage becomes unreadable for several polls rather than spending
unobserved indefinitely.

## 5. Polling and process-control pitfalls

- Bound every `colab exec`, `usage`, `stop`, and status probe with a
  timeout appropriate to the operation.
- A poller must recognize error/not-found states, not only success markers;
  otherwise it can loop forever after local session loss.
- For detached remote jobs, write a completion marker containing the exit code.
- Poll no faster than needed; once per minute is usually enough for long jobs.
- Kill local helper/watchdog processes by recorded PID. Avoid broad `pkill -f`
  or pattern/parent kills that can terminate the watchdog or calling agent.
- Preserve shell paths with spaces as one argv element. Do not turn an
  executable path into words with `read -a` or unquoted expansion.

## 6. Legacy rclone mount: keep for live jobs, prefer DriveFS for new ones

The legacy workaround copies the local rclone configuration to the Colab VM and
starts `rclone mount` there. Data flows Google Drive API <-> Colab VM directly;
the local PC is not a data proxy.

Field pitfalls:

- `colab upload` does not create the remote parent directory. Create
  `/root/.config/rclone` first.
- rclone mount needs `fusermount3`. Avoid replacing Colab's FUSE/DriveFS stack
  just to obtain it; install/extract only the required helper when possible.
- Do not rely on rclone `--daemon` under a bounded `colab exec`; child
  lifetime can be tied to the execution environment. Start the mount in a new
  process session and redirect stdio.
- The first root listing can take roughly a minute on a cold mount. Poll mount
  readiness and distinguish slow initialization from failure.
- For writeback mounts, check/drain pending VFS uploads before stopping the VM.
- Treat `rclone.conf` as a full Drive credential. Keep it 0600 and never print
  or commit it.
- Shared/default rclone OAuth clients are an external dependency and can change
  or be retired. Prefer the fork's user-owned persistent DriveFS client for new
  workflows after current rclone-based jobs finish.

## 7. Durability when Drive/FUSE is part of a pipeline

For stateful pipelines:

- Keep live SQLite DB/WAL/SHM on local scratch when practical.
- Persist consistent SQLite snapshots using SQLite's backup API; never copy only
  the main DB file while WAL may contain committed rows.
- Use immutable generation names plus hashes/receipts for durable artifacts.
- A readback from the same FUSE-mounted runtime can be satisfied from cache and
  is not strong evidence of fresh-runtime durability. For critical artifacts,
  verify size/hash from a fresh runtime or an independent path before declaring
  recovery proven.
