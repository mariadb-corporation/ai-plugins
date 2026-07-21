---
description: Save a compressed summary of this session so a future session can resume. Usage: /checkpoint
---

# Checkpoint Command

Review this conversation and the current state of files, then write (overwrite) `.claude/PROJECT_CONTEXT.md` with a compressed summary structured as:

## Project

One-paragraph description of what this project is and its goal.

## Architecture / key decisions

Bullet list of non-obvious design choices and why.

## Current state

- What's implemented and working
- What's in progress
- What's broken/known issues

## Files that matter

Path -> one-line purpose, for files central to this work.

## Next steps

Concrete, ordered list of what to do next.

## Gotchas / things not to repeat

Dead ends already tried and why they failed.

Keep it dense — favor bullet points over prose, omit anything derivable by reading the code.

1. Run `git -C status --short` and `git -C branch --show-current`, append under a "Git state" heading.
2. Confirm back to the user the exact path you wrote to.
