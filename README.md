# Colab CLI Agent Skill

Portable agent skill for using the Google Colab CLI to provision Colab CPU,
GPU, and TPU runtimes from a terminal agent.

## Install the CLI

```bash
uv tool install google-colab-cli
colab version
```

## Install the skill globally

Preferred route: use the Skills CLI, because it installs the skill into the
global locations for Codex, OpenCode, Hermes Agent, Claude Code, Cursor, Gemini
CLI, and other supported coding agents in one command.

```bash
npx skills add hcsolakoglu/colab-cli-agent-skill -g --agent '*' --skill colab-cli -y --copy
```

Check the global install:

```bash
npx skills list -g --json
```

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

## Repository structure

```text
colab-cli/
  SKILL.md
  agents/openai.yaml
  references/official-sources.md
scripts/
  install-local.sh
```

The root repo intentionally stays small. `colab-cli/` is the actual portable
skill package, `agents/openai.yaml` provides UI metadata for agents that read it,
and `scripts/install-local.sh` is only for direct local copying.
