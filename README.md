# Colab CLI Agent Skill

Portable agent skill for using the Google Colab CLI to provision Colab CPU,
GPU, and TPU runtimes from a terminal agent.

Install the CLI:

```bash
uv tool install google-colab-cli
colab version
```

Install the skill locally from this repo:

```bash
./scripts/install-local.sh
```

Manual install paths:

```bash
cp -a colab-cli ~/.codex/skills/colab-cli
cp -a colab-cli ~/.agents/skills/colab-cli
cp -a colab-cli ~/.config/opencode/skills/colab-cli
cp -a colab-cli ~/.hermes/skills/data-science/colab-cli
```

When installed, ask an agent to use `$colab-cli` for Colab runtime work.
