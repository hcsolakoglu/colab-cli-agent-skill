---
name: colab-cli
description: Use Google Colab CLI from a terminal agent to provision CPU, GPU, or TPU Colab runtimes, run local Python scripts and notebooks remotely, install packages, move files, export logs, and clean up sessions. Trigger when the user asks for Colab runtimes, remote GPU/TPU execution, QLoRA/fine-tuning on Colab, notebook execution on Colab, or `colab` CLI help.
metadata:
  short-description: Operate Google Colab runtimes from the CLI
---

# Colab CLI

Use the `colab` command to run local Python work on remote Google Colab runtimes.
Prefer this skill when the user wants Colab compute, GPUs, TPUs, notebook logs,
remote execution, or agent-driven ML jobs.

## Install And Verify

Check the local tool first:

```bash
colab version
colab --help
```

If missing, install it with `uv`:

```bash
uv tool install google-colab-cli
```

If already installed but stale:

```bash
colab update --install
```

The package supports Linux and macOS. It is not currently a Windows-native CLI.
The CLI stores session state under `~/.config/colab-cli/` by default.

## Mental Model

- A session is a live Jupyter kernel on a rented Colab VM. `colab new` allocates
  compute; `colab stop` releases it.
- Kernel state persists across `colab exec` and piped `colab repl` calls in the
  same session. Imports, variables, and functions remain until
  `colab restart-kernel` or `colab stop`.
- Execution starts in `/content`. Prefer absolute `/content/...` paths for
  remote files so later `ls`, `download`, and cleanup commands are unambiguous.
- Each CLI command authenticates, performs one operation, and exits. The
  keep-alive process is managed by the CLI after allocation.

## Agent Rules

- Always make a lifecycle plan before allocating compute: session name, hardware,
  commands to run, artifacts to retrieve, and cleanup command.
- Always use a session name with `-s <name>` for allocated sessions. Auto-named
  sessions are harder to clean up and report on.
- Prefer `colab run` for one-shot jobs because it provisions, executes, and stops
  the runtime automatically.
- Use a named session for multi-step work: `colab new -s <name>`, then
  `colab install`, `colab exec`, `colab download`, `colab log`, `colab stop`.
- Do not leave paid resources running. Run `colab stop -s <name>` when done, then
  verify with `colab sessions`.
- Never start unpiped `colab repl` or `colab console` from a non-interactive
  agent shell. They are TTY-oriented. Use `colab exec`, `colab run`, or pipe
  stdin into the interactive command.
- Treat unpiped `colab repl`, unpiped `colab console`, `colab auth`, and
  `colab drivemount` as user-interactive. Piped `repl`/`console` can be used
  non-interactively; `auth`/`drivemount` generally need a human at a terminal.
- Do not edit `~/.config/colab-cli/sessions.json` by hand. Use CLI commands.
- For live probes, remember that `colab new` and `colab run` can allocate real
  compute units. Clean up even after failed jobs.
- For parallel agents or risky probes, isolate session state with
  `--config /tmp/<name>.json`.

## Authentication

The global `--auth` option chooses how the CLI authenticates to the Colab control
plane:

```bash
colab --auth oauth2 sessions
colab --auth adc sessions
```

`oauth2` is the default in the installed CLI. First use may open a browser
consent flow using the client config at `~/.colab-cli-oauth-config.json`.

`adc` uses Google Application Default Credentials and is usually better for
headless agent workflows once configured. If ADC user credentials fail with scope
errors, re-authenticate with:

```bash
gcloud auth application-default login --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/colaboratory
```

Do not confuse CLI control-plane auth with `colab auth`. The `colab auth`
subcommand pushes credentials into the remote VM for notebook code that needs
GCP services such as BigQuery or Cloud Storage.

Debug control-plane identity and scopes with:

```bash
colab whoami
colab --auth adc whoami
```

If `colab.pa.googleapis.com` returns 403, first check for a missing
`colaboratory` scope with `colab whoami`. Do not retry allocations blindly.

## One-Shot Jobs

Use `colab run` when the user wants a script run on temporary hardware:

```bash
colab run --gpu T4 train.py --epochs 1
```

Useful options:

```bash
colab run --gpu T4 script.py
colab run --gpu L4 --timeout 600 script.py
colab run --tpu v5e1 script.py
colab run --keep -s inspect-job script.py
```

Use `--keep` only when you need to inspect the runtime afterward. If you use it,
stop the session explicitly:

```bash
colab stop -s inspect-job
```

For executable scripts, a shebang can request Colab hardware:

```python
#!/usr/bin/env -S colab run --gpu T4
print("running remotely")
```

Operational details:

- `colab run` forwards script arguments and sets `__name__ == "__main__"` like
  local `python script.py`.
- Script exit codes propagate. An exception or `sys.exit(1)` makes `colab run`
  return non-zero.
- CLI status chatter goes to stderr; the script's stdout stays on stdout. This
  makes `colab run job.py > out.txt` capture only the script output.
- A missing script path fails before VM allocation.

## Multi-Step Sessions

Use a named session for setup, multiple runs, file transfer, or log export:

```bash
colab new -s trainer --gpu T4
colab status -s trainer
colab install -s trainer torch transformers datasets peft trl accelerate
colab exec -s trainer -f train.py --timeout 1800
colab download -s trainer /content/outputs/adapter.safetensors ./adapter.safetensors
colab log -s trainer -o trainer-log.ipynb
colab stop -s trainer
colab sessions
```

Available accelerators reported by the CLI:

- GPU: `T4`, `L4`, `G4`, `H100`, `A100`
- TPU: `v5e1`, `v6e1`

Availability depends on the user's Colab subscription and remaining compute
units. If a high-end GPU fails, retry with a cheaper option such as `T4` only
after explaining the tradeoff.

If an accelerator request returns a quota or entitlement error, fall back to
`--gpu T4` or CPU only after checking the user's goal. Do not assume GPU/TPU
allocation will succeed on every account.

## Execution

Run local Python code on an existing session:

```bash
colab exec -s analysis -f script.py --timeout 300
```

Pipe short code through stdin:

```bash
printf '%s\n' "import torch; print(torch.cuda.is_available())" | colab exec -s analysis
```

Run a notebook against the remote kernel:

```bash
colab exec -s analysis -f notebook.ipynb --timeout 900
colab log -s analysis -o analysis-log.ipynb
```

Notebook execution writes an output notebook next to the input, and
`colab log -o` can export the session history separately.

For plots, pass `--output-image <path>` to `exec` or `repl` when you need a
deterministic local image path.

For batch shell commands, prefer Python through `exec` when possible. If a real
shell is required:

```bash
printf '%s\n' "pwd; ls -la /content" | colab console -s analysis
```

`console` uses a terminal shell, so captured output can contain control bytes.

## Files And Environment

Remote filesystem commands:

```bash
colab ls -s analysis /content
colab upload -s analysis ./local.txt /content/local.txt
colab download -s analysis /content/result.json ./result.json
colab rm -s analysis /content/temp.txt
colab edit -s analysis /content/config.py
```

Install packages on the VM:

```bash
colab install -s analysis numpy pandas
colab install -s analysis -r requirements.txt
```

Mount Drive or authenticate the VM only when the task requires it:

```bash
colab drivemount -s analysis
colab auth -s analysis
```

These commands can prompt the user, so do not run them blindly in a
non-interactive agent environment.

## Logs And Reporting

Inspect and save execution history:

```bash
colab log -s analysis -n 20
colab log -s analysis -t execution
colab log -s analysis -o analysis-log.ipynb
colab log -s analysis -o analysis-log.md
colab log -s analysis -o analysis-log.jsonl
```

When reporting completion, include the session name, hardware, files retrieved,
log file path if exported, and confirmation that cleanup ran.

## Recovery

- `Session not found`: run `colab sessions`; recreate the session if the backend
  pruned it.
- Kernel stuck or timeout: run `colab restart-kernel -s <name>` once, then retry.
  If still stuck, stop and recreate the session.
- Unexpected stale behavior: check `which colab` and `colab version`.
- Auth failure: inspect whether the command used `oauth2` or `adc`, then run
  `colab whoami`; do not use `colab auth` to fix control-plane credential
  problems.
- Cleanup uncertainty: run `colab sessions` and stop any named sessions created
  for the current task.

## Fast Command Reference

```bash
colab new -s NAME [--gpu T4|L4|G4|H100|A100] [--tpu v5e1|v6e1]
colab sessions
colab status -s NAME
colab run [--gpu GPU|--tpu TPU] [--keep] SCRIPT [ARGS...]
colab exec -s NAME -f FILE [--timeout SECONDS]
colab install -s NAME PKG...
colab install -s NAME -r requirements.txt
colab upload -s NAME LOCAL REMOTE
colab download -s NAME REMOTE LOCAL
colab log -s NAME [-n N|-o FILE]
colab restart-kernel -s NAME
colab url -s NAME [--open]
colab stop -s NAME
colab whoami
colab version
```

For upstream details, consult:

- Google Developers Blog announcement:
  `https://developers.googleblog.com/introducing-the-google-colab-cli/`
- Google Colab CLI repository:
  `https://github.com/googlecolab/google-colab-cli`
