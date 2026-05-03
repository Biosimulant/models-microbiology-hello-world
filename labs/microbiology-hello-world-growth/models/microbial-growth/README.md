# Microbiology Hello World Growth

`MicrobialGrowthHelloWorld` is the middle model in the multi-model hello-world
lab. It reads a starter setup record, simulates viable colony growth and
starvation decline, and emits the numbers and explanation used by the final
story model.

It uses a simple rule:

```text
more food + more space = faster growth
less food or less space = slower growth
no food = viable cells decline from starvation
```

This is not a publication-grade microbiology model. It is a clear first model
that shows how inputs, parameters, outputs, and visuals fit together.

## Parameters

- `initial_cells`: default starting colony size
- `available_food`: default initial food supply
- `growth_rate`: default fastest possible fractional growth per hour
- `space_limit`: default maximum number of cells the environment can hold
- `food_per_new_cell`: food units spent for each new cell
- `starvation_death_rate`: viable-cell loss rate after food reaches zero

## Inputs

- `growth_setup`: setup record from the starter-culture model. If it is not
  wired, the constructor defaults are used.

## Outputs

- `colony_state`: current viable-cell count, food level, starvation loss, and the main limiting factor
- `lesson_summary`: a sentence-level explanation of what happened

## Local Test

```bash
python3 -m pytest -q tests
```
