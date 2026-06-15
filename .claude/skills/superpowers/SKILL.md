---
name: superpowers
description: >-
  Meta-skill that gives Claude disciplined engineering "superpowers": discovering
  and applying the right workflow for a task. Use when starting any non-trivial
  coding task and you want a proven approach — brainstorming a design, planning
  before building, test-driven development, systematic debugging, or doing a
  rigorous code review. Invoke when the user says "use superpowers", asks for a
  structured/rigorous approach, or whenever a task is large enough that jumping
  straight to code would be risky.
---

# Superpowers

A toolkit of battle-tested engineering workflows. The point is not to do more
ceremony — it is to reach for the *right* discipline at the *right* moment so the
work is correct, reviewable, and doesn't have to be redone.

## How to use this skill

1. Identify which phase of work you're in (below).
2. Apply the matching workflow. Don't skip phases for non-trivial work.
3. Be honest about state: if something failed, say so; if a step was skipped,
   say that. Never report success you haven't verified.

When unsure which workflow applies, default to: **Brainstorm → Plan → TDD →
Review.**

## The workflows

### 1. Brainstorm (understand before deciding)

Use when the problem is fuzzy, has multiple viable approaches, or the
requirements aren't pinned down.

- Restate the problem in your own words and confirm the goal.
- Surface 2–3 genuinely different approaches with their trade-offs.
- Name the constraints (performance, compatibility, deadlines, existing
  patterns) that rule options in or out.
- Recommend one approach and say why. Don't survey endlessly — decide.

### 2. Plan (design before building)

Use before any change that touches more than a couple of files or introduces new
behavior.

- List the files you'll create or modify and what each change does.
- Sequence the steps so the code is runnable/testable between them.
- Call out risks, unknowns, and anything that needs the user's decision.
- Match the surrounding code: its naming, idioms, and comment density.

### 3. Test-Driven Development (prove it works as you go)

The core loop for implementing behavior:

1. **Red** — write the smallest failing test that captures the next bit of
   desired behavior. Run it; confirm it fails for the *right* reason.
2. **Green** — write the minimum code to make it pass. Run it; confirm it passes.
3. **Refactor** — clean up names, duplication, and structure with the test still
   green.

Rules:
- One behavior at a time. Don't write code with no failing test demanding it.
- Never edit tests just to make them pass — fix the code, or fix the test only
  if the test itself is wrong, and say which.
- Keep tests fast and deterministic.

### 4. Systematic debugging (find the cause, not a symptom)

Use when something is broken and the cause isn't obvious.

1. **Reproduce** reliably. If you can't reproduce it, you can't fix it.
2. **Isolate** — bisect, add logging, or shrink the input until the failure is
   cornered.
3. **Form a hypothesis** about the root cause and predict what you'd observe if
   it's true.
4. **Test the hypothesis** with one change at a time.
5. **Fix the cause**, then add a regression test so it can't come back.
6. Resist the urge to scatter speculative fixes — that hides the real bug.

### 5. Code review (verify before declaring done)

Use before committing significant work, or when reviewing a diff/PR.

- Read the diff as a hostile reviewer: what input breaks this?
- Check correctness first (edge cases, error paths, concurrency), then
  reuse/simplification, then efficiency.
- Confirm tests actually cover the new behavior and that they run.
- Verify the change does what it claims by running it, not by reading it.

## Operating principles

- **Smallest correct step.** Prefer the minimal change that satisfies the
  requirement over a speculative rewrite.
- **Verify, don't assume.** Run the test, run the app, read the file you're about
  to overwrite.
- **Faithful reporting.** State outcomes plainly — including failures and skips.
- **Read like the neighbors.** New code should be indistinguishable in style from
  the code around it.
- **Decide, then move.** Give a recommendation, not an exhaustive menu.
