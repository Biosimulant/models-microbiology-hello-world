# Microbiology Hello World Growth

`MicrobialGrowthHelloWorld` is a small `biosim.BioModule` for learning the
model contract.

It uses a simple rule:

```text
more food + more space = faster growth
less food or less space = slower growth
```

This is not a publication-grade microbiology model. It is a clear first model
that shows how inputs, parameters, outputs, and visuals fit together.

## Parameters

- `initial_cells`: starting colony size
- `available_food`: initial food supply
- `growth_rate`: fastest possible fractional growth per hour
- `space_limit`: approximate maximum number of cells the environment can hold

## Outputs

- `colony_state`: current numbers and the main limiting factor
- `lesson_summary`: a sentence-level explanation of what happened

## Local Test

```bash
python3 -m pytest -q tests
```
