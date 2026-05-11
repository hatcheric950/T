# CLAUDE.md

This file provides guidance for AI assistants (Claude and others) working in this repository.

## Repository Overview

**Name:** T  
**Owner:** hatcheric950  
**License:** GNU General Public License v3.0  
**Status:** Early-stage / bootstrapped — minimal code exists yet.

The `.gitignore` is configured for an ActionScript / Adobe AIR mobile project (Flash `.swf`, Adobe AIR `.air`, iOS `.ipa`, Android `.apk` artifacts, Eclipse/Flash Builder `.settings/`, and compiled output directories `bin-debug/`, `bin-release/`, `[Oo]bj/`, `[Bb]in/`). The project may expand to other languages over time.

## Repository Structure

```
T/
├── CLAUDE.md       # This file
├── README.md       # Project overview (stub)
├── LICENSE         # GNU GPL v3
└── .gitignore      # ActionScript/mobile build artifacts
```

No source code has been committed yet. As the project grows, update this file to reflect the actual structure.

## Git Workflow

- **Default branch:** `main`
- **Feature branches:** use descriptive names, e.g. `feature/<short-description>` or `claude/<task-slug>`
- **Commits:** write clear, imperative-mood messages ("Add X", "Fix Y", "Remove Z")
- **Pull requests:** always target `main`; open as draft until ready for review

```bash
# Start a new feature
git checkout -b feature/my-feature

# Push and open a draft PR
git push -u origin feature/my-feature
```

## Development Conventions

Since no tech stack is locked in yet, follow these general principles:

- **No comments by default.** Only comment when the *why* is non-obvious (hidden constraint, subtle invariant, workaround for a specific bug).
- **No speculative abstractions.** Build only what the current task requires; avoid premature helpers, feature flags, or backward-compat shims.
- **No error handling for impossible cases.** Only validate at system boundaries (user input, external APIs).
- **Prefer editing existing files** over creating new ones.
- **No emojis in code or docs** unless explicitly requested.

## Updating This File

When the codebase gains structure (source directories, a build system, tests, CI), update the sections below accordingly:

- **Build & Run** — commands to install dependencies, compile, and start the project
- **Testing** — how to run the test suite and what coverage is expected
- **Code Style** — linter/formatter config and any project-specific conventions
- **Architecture** — key modules, data flow, notable design decisions
- **Environment** — required env vars, secrets management, local vs. production differences
