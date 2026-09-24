# Colab CLI Agent Skill

Portable agent skill for using the Google Colab CLI to provision Colab CPU,
GPU, and TPU runtimes from a terminal agent.

Skill guidance verified against `google-colab-cli==0.7.2` on 2026-09-24.
Re-verify command surface with `colab --help` after upgrading the CLI.

## Install the CLI

```bash
uv tool install google-colab-cli
colab version
```

## Install the skill globally

Preferred route: [Vercel Labs' Skills CLI](https://github.com/vercel-labs/skills)
(`npx skills`), the open tool for installing agent skills across coding agents
and harnesses. With `--agent '*'`, one command targets all agent integrations
supported by the Skills CLI — Codex, Claude Code, OpenCode, Cursor, Gemini CLI,
and 70+ more. Agents that do not support global skills are skipped or reported
as unsupported. Browse the skills ecosystem and agent directory at
[skills.sh](https://skills.sh).

```bash
npx skills add hcsolakoglu/colab-cli-agent-skill -g --agent '*' --skill colab-cli -y
```

Check the global install:

```bash
npx skills list -g --json
```

Keep the skill updated as the repo evolves:

```bash
npx skills update colab-cli -g -y
```

### Why no `--copy`?

The Skills CLI defaults to symlinks, which keeps the skill as a single source
of truth: one real copy under `~/.agents/skills/colab-cli/`, with symlinks
into each supported agent's skills directory (agents that cannot host a
symlink, or that do not support global skills, are handled per-agent).
Pass `--copy` only if you
specifically need each agent to have an independent file copy (for example,
to edit one agent's copy in isolation). The symlink mode is what avoids
duplicate skill entries showing up in agents that auto-read both
`~/.agents/skills/` and the agent's own `skills/` folder (Codex, Hermes, and
several others fall into this category).

## Local development install

From a local clone, run:

```bash
./scripts/install-local.sh
```

This copies `colab-cli/` into common local agent skill directories, including
Codex, shared agent skills, OpenCode, and Hermes when present.

Manual fallback paths:

```bash
cp -a colab-cli ~/.codex/skills/colab-cli
cp -a colab-cli ~/.agents/skills/colab-cli
cp -a colab-cli ~/.config/opencode/skills/colab-cli
cp -a colab-cli ~/.hermes/skills/data-science/colab-cli
```

When installed, ask an agent to use `$colab-cli` for Colab runtime work.

## Runtime safety

The skill explicitly tells agents to stop Colab sessions they create and verify
cleanup with `colab sessions`, so runtimes are not left consuming compute units.
It also warns that runtime duration, idle timeout, accelerator access, and
credit usage vary by Colab subscription tier, account state, demand, and
hardware choice.

The package also includes `colab-cli/scripts/benchmark-runtime.py`, a compact
VPS-style profiler for CPU/RAM/disk/GPU/TPU/network checks and approximate
FP32/FP16/BF16 matmul probes, plus a dated Pro+ snapshot under
`colab-cli/references/`. The snapshot is intentionally marked as observed data,
not a guaranteed hardware or credit-rate table.

For scarce GPUs, `scripts/retry-gpu-benchmarks.sh` repeatedly tries named
`colab run` allocations, validates benchmark JSON, and checks for leftover
sessions between attempts.

## Repository structure

```text
colab-cli/
  SKILL.md
  agents/openai.yaml
  scripts/benchmark-runtime.py
  references/official-sources.md
  references/pro-plus-snapshot-2026-06-06.md
scripts/
  install-local.sh
  retry-gpu-benchmarks.sh
```

The root repo intentionally stays small. `colab-cli/` is the actual portable
skill package, `agents/openai.yaml` provides UI metadata for agents that read it,
and `scripts/install-local.sh` is only for direct local copying.
