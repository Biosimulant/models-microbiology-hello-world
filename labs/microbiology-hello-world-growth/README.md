# Microbiology Hello World Growth Lab

This lab wraps one embedded model: `MicrobialGrowthHelloWorld`.

It is a plain-language microbial growth example for new Biosimulant users. The
model tracks a colony over time and shows why growth starts quickly, then slows
when food or space becomes limiting.

## Inputs

| Input | Meaning |
|---|---|
| `initial_cells` | Starting number of cells. |
| `available_food` | Food units available at the start. |
| `growth_rate` | How quickly cells can multiply when food and space are available. |
| `space_limit` | Approximate maximum colony size. |

## Outputs

| Output | Meaning |
|---|---|
| `colony_state` | Current cell count, food remaining, and limiting phase. |
| `lesson_summary` | Plain-language explanation of what happened. |
