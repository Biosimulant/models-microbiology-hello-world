# AGENTS.md

Instructions for AI agents working in this repository.

This is a public tutorial model repo for the Biosimulant model fleet. Keep the
repository small, readable, and beginner-friendly.

## Structure

- `labs/microbiology-hello-world-growth/` contains the wrapper lab.
- `labs/microbiology-hello-world-growth/models/` contains all embedded lab models.
- `examples/` contains CLI examples for local runs.
- `scripts/` contains validation checks used by CI.

## Rules

- Preserve the direct multi-model lab layout.
- Keep the public inputs stable and simple for non-technical users.
- Do not add large data files, generated run output, or external runtime
  dependencies.
- Keep the CLI human-readable and deterministic.
- Run the checks listed in `STANDARDS.md` before committing.
