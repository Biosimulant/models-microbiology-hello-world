# models-microbiology-hello-world

> Storage-only repo: the runnable wrapper lab lives in
> `labs/microbiology-hello-world-growth/`, with the embedded model kept inside
> `labs/microbiology-hello-world-growth/model/`.

Beginner-friendly **microbial growth hello world** model for the **biosim**
platform.

This repository ships one pure-Python `biosim.BioModule`:
`microbiology-hello-world-growth`, a small simulation where cells consume food,
multiply, and slow down as food or space becomes limiting.

## What's Inside

| Lab | Description |
|---|---|
| `microbiology-hello-world-growth` | Educational microbial colony growth model with plain-language outputs and simple visuals. |

## Why This Exists

The model is intentionally small. It is meant to show the core Biosimulant
model contract without requiring a GPU, external data, SBML runtime, or domain
expertise.

It demonstrates:

- how a `BioModule` declares inputs and outputs
- how parameters change a run
- how structured signals carry results
- how a model can produce visual summaries for users
- how a CLI can make the model understandable outside a notebook

## Quick Start

Run the friendly local example:

```bash
python3 examples/run_example.py microbial-growth
```

Try a different scenario:

```bash
python3 examples/run_example.py microbial-growth --hours 10 --initial-cells 20 --food 120 --space-limit 250
```

Emit machine-readable output:

```bash
python3 examples/run_example.py microbial-growth --json
```

## Model Story

The simulation tracks a small colony:

- cells start with a beginning population
- food lets cells make more cells
- the colony slows down when food runs low
- the colony also slows down when it gets close to the available space limit

The output intentionally avoids specialist language. A non-technical user
should be able to read the CLI result and understand what changed.

## Validation

```bash
python3 scripts/validate_manifests.py
python3 scripts/check_entrypoints.py
bash scripts/check_public_boundary.sh
python3 -m pytest -q labs/microbiology-hello-world-growth/model/tests
```

## License

Dual-licensed: Apache-2.0 for code, CC BY 4.0 for content.
