---
name: OpenCode Config Sync
description: Use when syncing this device's OpenCode global configuration with the config-sync Git repository, including pulling changes from another device, pushing local changes, bootstrapping a new device, or troubleshooting config that did not take effect.
---

# OpenCode Config Sync

The OpenCode global config directory is itself a Git repository:

- Windows: `%USERPROFILE%\.config\opencode`
- macOS / Linux: `~/.config/opencode`

Run every Git command from that directory.

## Pull changes from another device

1. Check state first: `git status --short`. If there are local modifications, show
   them and ask the user whether to commit, stash, or discard before pulling.
2. Pull with rebase: `git pull --rebase`.
3. If `package-lock.json` or `package.json` changed, restore dependencies with
   `npm ci`.
4. Restart the background service so `opencode.jsonc` is reloaded:
   `opencode service restart`.
5. Verify with `opencode api get /api/info`.

If a rebase stops on conflicts, show the conflicted files and the conflicting
hunks, then ask the user which side to keep. Never discard the other device's
changes silently. Never force-push.

## Push local changes

1. Review what changed: `git status --short` and `git diff`.
2. Scan the staged diff for secrets before committing:
   `git add -A` then
   `git diff --cached | grep -Ei 'sk-|api[_-]?key|token|secret|password'`.
   If anything sensitive appears, stop and replace it with `{env:VAR}` or
   `{file:~/.secrets/...}` before committing.
3. Commit with a short descriptive message, for example
   `git commit -m "config: rebind session tabs"`.
4. `git pull --rebase` to absorb the other device's commits, then `git push`.

## Bootstrap a new device

Follow the "新设备初始化" section of the repository `README.md`, in order:

1. `opencode --version` succeeds.
2. `opencode service stop`.
3. Move any existing config directory aside (`opencode.bak`).
4. Clone the repository into the config directory.
5. `npm ci` when `package.json` exists.
6. `opencode service restart` then `opencode api get /api/info`.
7. Credentials are **not** in the repository: run `/connect` per provider and
   `/mcps` for OAuth MCP servers. Do not attempt to copy credential stores,
   tokens, or `auth.json` between devices.

## Never sync

- `service.json` (machine-specific service registration, ignored by `.gitignore`)
- `~/.local/share/opencode/` — `opencode.db`, `log/`, `snapshot/`, `tool-output/`
- `~/.local/state/opencode/` — `model.json`, `prompt-history.jsonl`, `frecency.jsonl`
- `node_modules/`

Migrating session history is a separate, deliberate operation: stop the service
before copying `opencode.db` and its `-wal`/`-shm` files. Never copy them while
the service is running.

## Troubleshooting

- Config ignored: verify the file lives directly in the config directory and is
  not overridden by a nearer project-level `opencode.jsonc` or
  `.opencode/opencode.jsonc`.
- TUI settings not applied: `cli.json` hot-reloads; an invalid value is rejected,
  so check the file against `https://opencode.ai/v2/cli.json`.
- Service unhealthy: `opencode service status`, then `opencode service restart`;
  compare with `opencode --standalone` to isolate shared-service problems.
