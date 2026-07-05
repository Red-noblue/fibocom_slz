# env-bootstrap

`env-bootstrap` is a small project-local tool for rebuilding a Python environment
under a repository path such as `./.conda-env` without requiring a preinstalled
Conda distribution.

The first target in this workspace is `modules/uav`, which contains two Python
packages:

- `uav-weather-energy-predictor`
- `uav-gis-replay-studio`

## Design

- Prefer `micromamba` over `miniconda` for a smaller bootstrap footprint.
- Keep the environment itself as a local build artifact.
- Keep the environment definition and bootstrap logic in versioned files.

The current implementation supports:

- Downloading or reusing a `micromamba` binary.
- Creating or updating a prefix environment from `environment.yml`.
- Installing local packages into that environment with editable `pip install`.
- Running commands inside that environment.
- Listing managed and orphan shared environments under `._envs/`.
- Pruning orphan shared environments under `._envs/`.
- Exporting an explicit package lock for the current platform.

## Layout

```text
tools/env-bootstrap/
  bin/env-bootstrap
  manifests/uav-modules.env.sh
  runtime/                 # ignored local cache
._envs/
  uav-modules-py310/       # ignored local env prefix
modules/uav/
  environment.yml
```

## Usage

Inspect the manifest:

```bash
./tools/env-bootstrap/bin/env-bootstrap doctor \
  ./tools/env-bootstrap/manifests/uav-modules.env.sh
```

Create or update the UAV environment:

```bash
./tools/env-bootstrap/bin/env-bootstrap sync \
  ./tools/env-bootstrap/manifests/uav-modules.env.sh
```

Run a command inside the environment:

```bash
./tools/env-bootstrap/bin/env-bootstrap run \
  ./tools/env-bootstrap/manifests/uav-modules.env.sh -- \
  python --version
```

Export an explicit lock file after the environment is built:

```bash
./tools/env-bootstrap/bin/env-bootstrap freeze-explicit \
  ./tools/env-bootstrap/manifests/uav-modules.env.sh \
  ./modules/uav/conda-linux-aarch64.lock
```

## Docs

- `tools/env-bootstrap/docs/README.md`
- `tools/env-bootstrap/docs/命令参考.md`
- `tools/env-bootstrap/docs/共享环境管理.md`

## Notes

- `tools/env-bootstrap/runtime/` is local cache and package state for
  `micromamba`; it is ignored by git and can be rebuilt if removed.
