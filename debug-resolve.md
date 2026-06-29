# Debug Resolve Notes

## 2026-06-29 - Codex CLI update appeared not to work

Problem:
- Running the normal Codex CLI update did not appear to change the active `codex` version.
- `codex --version` still reported `codex-cli 0.141.0`.

Observed state:
- Latest npm package: `@openai/codex@0.142.3`.
- Global npm install already had `@openai/codex@0.142.3`.
- Direct npm-managed binary reported `codex-cli 0.142.3`.
- Shell resolved `codex` to a user-local launcher under `~/.local/bin/codex`, which was stale.

Root cause:
- The update worked at the npm package level, but `PATH` picked the user-local launcher before the npm-managed binary.
- That stale launcher kept exposing the old `0.141.0` CLI.

Fix applied:
- Backed up old launcher to `/tmp/codex-local-bin-before-0.142.3`.
- Replaced the user-local `codex` launcher with a symlink to the npm-managed Codex binary:

```bash
ln -sf ~/.nvm/versions/node/<node-version>/bin/codex ~/.local/bin/codex
```

Verification:

```bash
codex --version
# codex-cli 0.142.3
```

Future diagnostic flow:

```bash
npm install -g @openai/codex@latest
npm view @openai/codex version
npm list -g --depth=0
which codex
codex --version
```

If npm shows a newer package but `codex --version` is old, check for a stale launcher earlier in `PATH`.
