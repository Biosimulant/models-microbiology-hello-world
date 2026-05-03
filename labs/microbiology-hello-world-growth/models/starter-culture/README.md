# Starter Culture Setup

This model is the first step in the hello-world lab. It turns four simple controls into one setup record that downstream models can use.

## Inputs

- `initial_cells`: starting number of cells.
- `available_food`: food available at the start.
- `growth_rate`: how quickly cells can multiply.
- `space_limit`: how many cells the space can hold.

## Outputs

- `growth_setup`: structured setup for the growth model.
- `setup_summary`: short plain-language setup summary.
- `run_metadata`: status for the setup step.
