# models-microbiology-hello-world

> Storage-only repo: the runnable wrapper lab lives in
> `labs/microbiology-hello-world-growth/`, with all embedded models kept inside
> `labs/microbiology-hello-world-growth/models/`.

Beginner-friendly **microbial growth hello world** model for the **biosim**
platform.

This repository ships a pure-Python multi-model hello-world lab:
`microbiology-hello-world-growth`, a small simulation where users choose a
starting plate, cells consume food and multiply, and a final story model explains
what happened, including the viable-cell decline after food runs out.

## What's Inside

| Lab | Description |
|---|---|
| `microbiology-hello-world-growth` | Educational three-model microbial colony growth lab with plain-language outputs and simple visuals. |

## Why This Exists

The model is intentionally small. It is meant to show the core Biosimulant
model contract without requiring a GPU, external data, SBML runtime, or domain
expertise.

It demonstrates:

- how multiple `BioModule` objects declare inputs and outputs
- how Biosimulant wiring passes a setup into a simulation and then into a story
- how parameters change a run
- how structured signals carry results
- how a model can produce visual summaries for users
- how a CLI can make the model understandable outside a notebook

For implementation details, see `docs/MULTI_MODEL_HELLO_WORLD.md`.

## Model Story

The simulation tracks a small colony:

- cells start with a beginning population
- food lets cells make more cells
- the colony slows down when food runs low
- viable cells decline once food is exhausted
- the colony also slows down when it gets close to the available space limit

The output intentionally avoids specialist language. A non-technical user
should be able to read the CLI result and understand what changed.

## Validation

```bash
python3 scripts/validate_manifests.py
python3 scripts/check_entrypoints.py
bash scripts/check_public_boundary.sh
python3 -m pytest -q labs/microbiology-hello-world-growth
```

## License

Dual-licensed: Apache-2.0 for code, CC BY 4.0 for content.
