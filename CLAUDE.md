# CLAUDE.md

Guidance for AI assistants (Claude Code and similar) working in this repository.

## Overview

This repository (`T`) is **newly initialized and contains no source code yet.** Treat it as
a fresh scaffold. The only signal about the intended technology stack comes from
`.gitignore`, which is templated for an **ActionScript 3 / Apache Flex / Adobe AIR** project
using **Flash Builder / Eclipse** tooling (it ignores `bin-debug/`, `bin-release/`, `*.swf`,
`*.air`, `*.ipa`, `*.apk`, and preserves `.project` / `.actionScriptProperties` /
`.flexProperties` compiler settings).

This stack is **inferred, not confirmed.** Do not assume it is correct once real code lands —
update this file to match whatever is actually committed.

License: **GNU GPL v3.0** (see `LICENSE`).

## Current repository contents

| File | Purpose |
| --- | --- |
| `README.md` | Placeholder only (`# T` / `Gh`). |
| `LICENSE` | Full GNU GPL v3.0 text. |
| `.gitignore` | ActionScript/Flex/AIR build-artifact ignores. |

There is no source code, build configuration, dependency manifest, or test suite at this time.

## Build / test / run

**None configured yet.** There are no build scripts, package manifests, or tests to run.

> **TODO (update when real code is added):** Once an ActionScript/AIR project is committed,
> document the actual build and run commands here — e.g. `mxmlc` / `amxmlc` (compile),
> `adt` (AIR Developer Tool, for packaging `.air`/`.apk`/`.ipa`), and `adl` (AIR Debug
> Launcher). If a different stack is adopted, replace this section entirely with the real
> tooling.

## Git & branch workflow

- Default branch: `main`.
- Active development branch: `claude/claude-md-docs-lwaxuq`.
- Push with `git push -u origin <branch-name>`.
- Open pull requests as **drafts**.
- Do not commit build artifacts — respect `.gitignore` (no `bin/`, `bin-debug/`, `*.swf`,
  `*.air`, etc.).

## Conventions for AI assistants

- **Be honest about the empty state.** Do not invent architecture, commands, or dependencies
  that do not exist in the repo.
- **Keep this file current.** As soon as real source, build config, or tests are added,
  revise the Overview, Contents, and Build/test/run sections to match reality.
- Preserve `README.md` and `LICENSE` unless explicitly asked to change them.
- Keep changes scoped to what was requested.
