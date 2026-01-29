# Skills for BERDL-ENIGMA-CORAL

This directory contains three Codex skills:

- `berdl-mcp`: BERDL MCP API discovery and querying workflow.
- `enigma-berdl-query`: ENIGMA/CORAL queries constrained to the published schema.
- `enigma-object-relationships`: Object lineage and provenance workflows using a bundled CLI.

## Install for Codex

Copy the skill folders into your Codex skills directory. By default this is
`$CODEX_HOME/skills` (or `~/.codex/skills` if `CODEX_HOME` is not set).

```bash
mkdir -p ~/.codex/skills
cp -R skills/berdl-mcp ~/.codex/skills/
cp -R skills/enigma-berdl-query ~/.codex/skills/
cp -R skills/enigma-object-relationships ~/.codex/skills/
```

Restart Codex so it picks up the new skills.

Note: `enigma-object-relationships` includes its own `tools/` directory, and `berdl-mcp` /
`enigma-berdl-query` include local `references/` to keep the skills self-contained.

## Use with ChatGPT

ChatGPT does not load Codex skills directly. To use these workflows, paste the
relevant `SKILL.md` contents into your ChatGPT project instructions or a custom
GPT's system instructions. You can also upload the `SKILL.md` files as reference
documents.

## Use with Claude Code

Claude Code does not auto-load Codex skills. Add the `SKILL.md` content to your
project or session instructions (for example in a repo-level `CLAUDE.md` file,
if you use that workflow), or paste the text at the start of a session.
