# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository ("T") is in its initial state — no source code exists yet. The license is GNU General Public License v3.0.

## Intended Project Type

The `.gitignore` is configured for an **ActionScript / Adobe Flash / AIR** project targeting Eclipse or Flash Builder:

- Ignored build output: `bin-debug/`, `bin-release/`, `obj/`, `bin/`
- Ignored executables: `*.swf` (Flash), `*.air` (Adobe AIR), `*.ipa` (iOS), `*.apk` (Android)
- Ignored IDE settings: `.settings/`
- Retained project metadata: `.project`, `.actionScriptProperties`, `.flexProperties` (Eclipse/Flash Builder compiler settings)

When source code is added, expect ActionScript (`.as`) or MXML (`.mxml`) files, with compilation targeting SWF or AIR runtimes.

## Development Commands

No build scripts or tooling are configured yet. Update this file once the project structure and build system are established.
