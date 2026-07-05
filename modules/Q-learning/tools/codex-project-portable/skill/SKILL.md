---
name: codex-project-portable
description: Use this skill when a project contains codex-project-portable and you need to start Codex with toolkit-local state under mycodex/sessions, inspect local sessions, choose a profile from mycodex/configs, or manage the toolkit runtime.
---

# Codex Project Portable

This toolkit is for projects that want Codex state to live inside the toolkit directory instead of only under machine-wide `~/.codex`.

## When to use it

Use this toolkit when the project contains `codex-project-portable/` and you need any of these:

- start Codex with state stored under `codex-project-portable/mycodex/sessions`
- install or update the toolkit-local `node` / `codex` runtime
- resume a known session id from the toolkit-local state
- inspect which local sessions already exist
- inspect which config profiles under `mycodex/configs` are valid
- verify which profile, project root, and local state directories are being used

## Primary commands

Start Codex:

```bash
./bin/codex-project start
```

Start with an explicit profile:

```bash
./bin/codex-project start --profile zys
```

Start with an explicit workspace directory:

```bash
./bin/codex-project start --profile zys -C /tmp
```

List available profiles:

```bash
./bin/codex-project profiles
```

Resume a specific session id:

```bash
./bin/codex-project resume --profile zys <session-id>
```

List local sessions:

```bash
./bin/codex-project sessions
```

Inspect resolved paths:

```bash
./bin/codex-project where
```

Run diagnostics:

```bash
./bin/codex-project doctor
```

Run a non-interactive round:

```bash
./bin/codex-project exec --profile zys "检查当前项目结构"
```

Manage the toolkit runtime:

```bash
./bin/codex-project runtime
```

## How it works

- Profiles live under `mycodex/configs/<profile>/`.
- A valid profile must contain both `auth.json` and `config.toml`.
- Runtime state lives under `mycodex/sessions/`, which is used as `CODEX_HOME`.
- Bundled runtime lives under `runtime/`, and launch defaults to `runtime/bin/node` plus the local Codex package.
- By default the workspace directory equals the inferred project root, but `-C` / `--workspace-dir` can override it for one launch.
- The inferred project root now prefers the enclosing `Yansongs_Mickey_Mouse_Clubhouse` directory.
- The launcher copies `auth.json` and `config.toml` from the selected profile into the runtime home before launch.
- It appends the current project root to the copied `config.toml` as a trusted project if needed.
- It keeps `sessions/`, sqlite files, shell snapshots, and memories in the toolkit-local runtime home.
- If `mycodex/sessions/` is empty and a legacy `state/codex-home/` exists, it copies the legacy state into the new location first.
- By default it deletes the copied runtime `auth.json` and `config.toml` after Codex exits, while preserving session data.

## Environment knobs

- `CODEX_PORTABLE_PROFILE`: force a specific profile name
- `CODEX_PORTABLE_CONFIGS_ROOT`: override the profile root
- `CODEX_PORTABLE_HOME`: override the runtime `CODEX_HOME`
- `CODEX_PORTABLE_PROJECT_ROOT`: force a specific project root
- `CODEX_PORTABLE_WORKSPACE_DIR`: override the launch workspace directory
- `CODEX_PORTABLE_KEEP_SOURCE_FILES=1`: keep copied runtime `auth.json` / `config.toml` after exit
- `CODEX_PORTABLE_NO_PROFILE_PROMPT=1`: skip interactive profile selection and use the default
- `CODEX_PORTABLE_WORKSPACE_ROOT_NAME`: override the default workspace root directory name

## Read next only if needed

- For user-oriented quickstart and aliases, read `../README.md`.
