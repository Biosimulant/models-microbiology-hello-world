# SPDX-FileCopyrightText: 2026-present Biosimulant Team
#
# SPDX-License-Identifier: Apache-2.0
"""Beginner-friendly microbial growth hello world model."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from biosim import StatefulBioModule
from biosim.signals import BioSignal, SignalSpec, coerce_float, unwrap_payload

if TYPE_CHECKING:  # pragma: no cover - typing only
    from biosim.visuals import VisualSpec


class MicrobialGrowthHelloWorld(StatefulBioModule):
    """Small colony model for explaining inputs, outputs, and visual summaries."""

    def __init__(
        self,
        initial_cells: float = 10.0,
        available_food: float = 80.0,
        growth_rate: float = 0.8,
        space_limit: float = 200.0,
        integration_step: float = 0.05,
        food_per_new_cell: float = 1.0,
        starvation_death_rate: float = 0.04,
    ) -> None:
        for name, value in {
            "initial_cells": initial_cells,
            "available_food": available_food,
            "growth_rate": growth_rate,
        }.items():
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if space_limit <= 0:
            raise ValueError("space_limit must be positive")
        if integration_step <= 0:
            raise ValueError("integration_step must be positive")
        if food_per_new_cell <= 0:
            raise ValueError("food_per_new_cell must be positive")
        if starvation_death_rate < 0:
            raise ValueError("starvation_death_rate must be non-negative")

        super().__init__(integration_step=integration_step, record_initial_state=True)
        self.initial_cells = min(float(initial_cells), float(space_limit))
        self.available_food = float(available_food)
        self.growth_rate = float(growth_rate)
        self.space_limit = float(space_limit)
        self.integration_step = float(integration_step)
        self.food_per_new_cell = float(food_per_new_cell)
        self.starvation_death_rate = float(starvation_death_rate)

        self._epsilon = 1e-9
        self._cells = self.initial_cells
        self._food = self.available_food
        self._last_growth = 0.0
        self._last_death = 0.0
        self._peak_cells = self.initial_cells

    def inputs(self) -> dict[str, SignalSpec]:
        return {
            "growth_setup": SignalSpec.record(
                schema={
                    "initial_cells": "float",
                    "available_food": "float",
                    "growth_rate": "float",
                    "space_limit": "float",
                    "food_per_new_cell": "float",
                    "setup_label": "str",
                },
                description="Starting setup record from the starter-culture model.",
            ),
        }

    def outputs(self) -> dict[str, SignalSpec]:
        return {
            "colony_state": SignalSpec.record(
                schema={
                    "t": "float",
                    "cells": "float",
                    "food_remaining": "float",
                    "food_used": "float",
                    "growth_this_step": "float",
                    "death_this_step": "float",
                    "peak_cells": "float",
                    "phase": "str",
                    "limiting_factor": "str",
                    "space_used_percent": "float",
                },
                emitted_unit="cells",
                description="Current viable colony size, food level, starvation loss, and limiting factor.",
            ),
            "lesson_summary": SignalSpec.record(
                schema={
                    "headline": "str",
                    "takeaway": "str",
                    "limiting_factor": "str",
                    "starting_cells": "float",
                    "final_cells": "float",
                    "cell_change": "float",
                    "food_used": "float",
                    "hours": "float",
                },
                description="Plain-language explanation of the model run.",
            ),
        }

    @property
    def history(self) -> list[dict[str, float | str]]:
        return [dict(point) for point in self._history]

    def reset_state(self) -> None:
        self._cells = min(self.initial_cells, self.space_limit)
        self._food = self.available_food
        self._last_growth = 0.0
        self._last_death = 0.0
        self._peak_cells = self.initial_cells

    def apply_overrides(self, *, reset_initial_state: bool) -> None:
        self._apply_input_overrides(reset_initial_state=reset_initial_state)

    def step(self, h: float) -> None:
        self._step(h)

    def record_state(self, t: float) -> None:
        self._record_state(t, growth_this_step=self._last_growth)

    def get_state(self) -> dict[str, float | str]:
        return {
            "time": self._time,
            "cells": self._cells,
            "food_remaining": self._food,
            "phase": self._phase(),
            "limiting_factor": self._limiting_factor(),
        }

    def visualize(self) -> Optional["VisualSpec" | list["VisualSpec"]]:
        if not self._history:
            return None

        return [
            {
                "render": "timeseries",
                "description": "Viable cell count over time.",
                "data": {
                    "title": "Viable Colony Cells",
                    "x_unit": "hour",
                    "y_unit": "cells",
                    "series": [
                        {"name": "Viable cells", "points": [[point["t"], point["cells"]] for point in self._history]},
                    ],
                },
            },
            {
                "render": "timeseries",
                "description": "Food remaining over time.",
                "data": {
                    "title": "Food Supply",
                    "x_unit": "hour",
                    "y_unit": "food_unit",
                    "series": [
                        {
                            "name": "Food remaining",
                            "points": [[point["t"], point["food_remaining"]] for point in self._history],
                        },
                    ],
                },
            },
            {
                "render": "table",
                "description": "Plain-language explanation of the run.",
                "data": {
                    "title": "What Happened",
                    "columns": ["Question", "Answer"],
                    "rows": [
                        ["What changed?", self._headline()],
                        ["Why did it change?", self._takeaway()],
                        ["Main limit", self._limiting_factor()],
                        ["Food used", f"{self.available_food - self._food:.2f} food units"],
                        ["Space used", f"{self._space_used_percent():.1f}%"],
                    ],
                },
            },
        ]

    def _input_number(self, name: str) -> float | None:
        signal = self._input_overrides.get(name)
        if signal is None:
            setup_signal = self._input_overrides.get("growth_setup")
            setup_value = unwrap_payload(setup_signal) if setup_signal is not None else None
            if isinstance(setup_value, dict) and name in setup_value:
                try:
                    return float(setup_value[name])
                except (TypeError, ValueError):
                    return None
            return None
        return coerce_float(signal)

    def _apply_input_overrides(self, *, reset_initial_state: bool) -> None:
        growth_rate = self._input_number("growth_rate")
        if growth_rate is not None and growth_rate >= 0.0:
            self.growth_rate = growth_rate

        space_limit = self._input_number("space_limit")
        if space_limit is not None and space_limit > 0.0:
            self.space_limit = space_limit
            if reset_initial_state:
                self._cells = min(self._cells, self.space_limit)

        initial_cells = self._input_number("initial_cells")
        if initial_cells is not None and initial_cells >= 0.0:
            self.initial_cells = min(initial_cells, self.space_limit)
            if reset_initial_state:
                self._cells = self.initial_cells

        available_food = self._input_number("available_food")
        if available_food is not None and available_food >= 0.0:
            self.available_food = available_food
            if reset_initial_state:
                self._food = available_food

        food_per_new_cell = self._input_number("food_per_new_cell")
        if food_per_new_cell is not None and food_per_new_cell > 0.0:
            self.food_per_new_cell = food_per_new_cell

        starvation_death_rate = self._input_number("starvation_death_rate")
        if starvation_death_rate is not None and starvation_death_rate >= 0.0:
            self.starvation_death_rate = starvation_death_rate

    def _step(self, h: float) -> float:
        self._last_growth = 0.0
        self._last_death = 0.0

        if self._cells <= self._epsilon:
            self._last_growth = 0.0
            return 0.0

        if self._food <= self._epsilon:
            if self.starvation_death_rate <= self._epsilon:
                return 0.0
            death = self._cells * (1.0 - math.exp(-self.starvation_death_rate * h))
            death = min(self._cells, max(0.0, death))
            self._cells = max(0.0, self._cells - death)
            self._last_death = death
            return -death

        if self.growth_rate <= self._epsilon:
            self._last_growth = 0.0
            return 0.0

        remaining_space = max(0.0, self.space_limit - self._cells)
        if remaining_space <= self._epsilon:
            self._last_growth = 0.0
            return 0.0

        food_half_saturation = max(1.0, 0.1 * max(self.available_food, 1.0))
        food_factor = self._food / (self._food + food_half_saturation)
        space_factor = max(0.0, 1.0 - (self._cells / max(self.space_limit, self._epsilon)))
        potential_growth = self.growth_rate * self._cells * food_factor * space_factor * h

        food_limited_growth = self._food / self.food_per_new_cell
        growth = min(max(0.0, potential_growth), food_limited_growth, remaining_space)

        self._cells += growth
        self._food = max(0.0, self._food - growth * self.food_per_new_cell)
        self._last_growth = growth
        self._peak_cells = max(self._peak_cells, self._cells)
        return growth

    def _record_state(self, t: float, *, growth_this_step: float) -> None:
        self._peak_cells = max(self._peak_cells, self._cells)
        self._history.append(
            {
                "t": float(t),
                "cells": float(self._cells),
                "food_remaining": float(self._food),
                "food_used": float(self.available_food - self._food),
                "growth_this_step": float(growth_this_step),
                "death_this_step": float(self._last_death),
                "peak_cells": float(self._peak_cells),
                "space_used_percent": float(self._space_used_percent()),
                "phase": self._phase(),
                "limiting_factor": self._limiting_factor(),
            }
        )

    def output_payload(self, t: float) -> dict[str, Any]:
        return {
            "colony_state": self._colony_state_payload(t),
            "lesson_summary": self._lesson_summary_payload(t),
        }

    def _colony_state_payload(self, t: float) -> dict[str, Any]:
        return {
            "t": float(t),
            "cells": float(self._cells),
            "food_remaining": float(self._food),
            "food_used": float(self.available_food - self._food),
            "growth_this_step": float(self._last_growth),
            "death_this_step": float(self._last_death),
            "peak_cells": float(self._peak_cells),
            "phase": self._phase(),
            "limiting_factor": self._limiting_factor(),
            "space_used_percent": float(self._space_used_percent()),
        }

    def _lesson_summary_payload(self, t: float) -> dict[str, Any]:
        return {
            "headline": self._headline(),
            "takeaway": self._takeaway(),
            "limiting_factor": self._limiting_factor(),
            "starting_cells": float(self.initial_cells),
            "final_cells": float(self._cells),
            "cell_change": float(self._cells - self.initial_cells),
            "food_used": float(self.available_food - self._food),
            "hours": float(t),
        }

    def _phase(self) -> str:
        if self._cells <= self._epsilon:
            return "no viable cells"
        if self._food <= self._epsilon and self._last_death > self._epsilon:
            return "starvation decline"
        if self._food <= self._epsilon:
            return "out of food"
        if self._cells >= self.space_limit - self._epsilon:
            return "space full"
        if self._last_growth <= self._epsilon and self._time > 0.0:
            return "paused"
        if self._space_used_percent() >= 85.0:
            return "slowing near space limit"
        if self._food <= max(2.0, 0.15 * max(self.available_food, 1.0)):
            return "slowing as food runs low"
        return "growing"

    def _limiting_factor(self) -> str:
        if self._food <= self._epsilon and self.starvation_death_rate > self._epsilon:
            return "starvation"
        if self.growth_rate <= self._epsilon:
            return "growth rate is zero"
        if self._food <= self._epsilon:
            return "food"
        if self._cells >= self.space_limit - self._epsilon:
            return "space"
        food_pressure = self._food / max(self.available_food, self._epsilon)
        space_pressure = 1.0 - (self._cells / max(self.space_limit, self._epsilon))
        if food_pressure < 0.2:
            return "food"
        if space_pressure < 0.2:
            return "space"
        return "none yet"

    def _space_used_percent(self) -> float:
        return 100.0 * self._cells / max(self.space_limit, self._epsilon)

    def _headline(self) -> str:
        if self._cells <= self._epsilon:
            return "The viable colony died out."
        if self._peak_cells > self._cells + self._epsilon and self._peak_cells > self.initial_cells + self._epsilon:
            return (
                f"The colony grew from {self.initial_cells:.1f} to a peak of {self._peak_cells:.1f} "
                f"viable cells, then ended at {self._cells:.1f}."
            )
        if self._cells <= self.initial_cells + self._epsilon:
            return "The viable colony did not grow."
        return f"The colony grew from {self.initial_cells:.1f} to {self._cells:.1f} viable cells."

    def _takeaway(self) -> str:
        limiting_factor = self._limiting_factor()
        if limiting_factor == "starvation":
            return "Cells multiplied until food ran out; after that, the viable population declined from starvation."
        if limiting_factor == "food":
            return "Cells multiplied until food became the main bottleneck."
        if limiting_factor == "space":
            return "Cells multiplied until the space limit became the main bottleneck."
        if limiting_factor == "growth rate is zero":
            return "Growth stayed flat because the growth rate was set to zero."
        return "Food and space are still available, so the colony is still in an easy-growth phase."
