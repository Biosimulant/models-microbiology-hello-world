# SPDX-FileCopyrightText: 2026-present Biosimulant Team
#
# SPDX-License-Identifier: Apache-2.0
"""Beginner-friendly microbial growth hello world model."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from biosim import BioModule
from biosim.signals import AcceptedSignalProfile, BioSignal, RecordSignal, SignalSpec

if TYPE_CHECKING:  # pragma: no cover - typing only
    from biosim.visuals import VisualSpec


def _signal_value(signal: BioSignal) -> Any:
    value = getattr(signal, "value", None)
    if isinstance(value, dict) and set(value.keys()) == {"payload"}:
        return value["payload"]
    return value


class MicrobialGrowthHelloWorld(BioModule):
    """Small colony model for explaining inputs, outputs, and visual summaries."""

    def __init__(
        self,
        initial_cells: float = 10.0,
        available_food: float = 80.0,
        growth_rate: float = 0.8,
        space_limit: float = 200.0,
        integration_step: float = 0.05,
        food_per_new_cell: float = 1.0,
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

        self.initial_cells = min(float(initial_cells), float(space_limit))
        self.available_food = float(available_food)
        self.growth_rate = float(growth_rate)
        self.space_limit = float(space_limit)
        self.integration_step = float(integration_step)
        self.food_per_new_cell = float(food_per_new_cell)

        self._epsilon = 1e-9
        self._input_overrides: Dict[str, BioSignal] = {}
        self._time = 0.0
        self._cells = self.initial_cells
        self._food = self.available_food
        self._last_growth = 0.0
        self._history: List[Dict[str, float | str]] = []
        self._outputs: Dict[str, BioSignal] = {}

    def inputs(self) -> dict[str, SignalSpec]:
        return {
            "initial_cells": self._scalar_input_spec("cells", "Starting number of cells."),
            "available_food": self._scalar_input_spec("food_unit", "Food units available at the start."),
            "growth_rate": self._scalar_input_spec(
                "1/hour", "Maximum fractional growth rate when food and space are available."
            ),
            "space_limit": self._scalar_input_spec("cells", "Approximate maximum cell count the space can hold."),
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
                    "phase": "str",
                    "limiting_factor": "str",
                    "space_used_percent": "float",
                },
                emitted_unit="cells",
                description="Current colony size, food level, and limiting factor.",
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

    @staticmethod
    def _scalar_input_spec(unit: str, description: str) -> SignalSpec:
        return SignalSpec.scalar(
            dtype="float64",
            accepted_profiles=(
                AcceptedSignalProfile(
                    signal_type="scalar",
                    dtype="float64",
                    accepted_units=(unit,),
                    description=description,
                ),
                AcceptedSignalProfile(signal_type="record", schema={"payload": "json"}, description=description),
            ),
            description=description,
        )

    @property
    def history(self) -> list[dict[str, float | str]]:
        return [dict(point) for point in self._history]

    def setup(self, config: Optional[dict[str, Any]] = None) -> None:
        self.reset()

    def reset(self) -> None:
        self._time = 0.0
        self._cells = min(self.initial_cells, self.space_limit)
        self._food = self.available_food
        self._last_growth = 0.0
        self._history = []
        self._outputs = {}

    def set_inputs(self, inputs: dict[str, BioSignal]) -> None:
        self._input_overrides = dict(inputs or {})
        self._apply_input_overrides(reset_initial_state=self._time <= 0.0 and not self._history)

    def advance_window(
        self,
        start: float | None = None,
        end: float | None = None,
        inputs: dict[str, BioSignal] | None = None,
    ) -> dict[str, BioSignal]:
        if inputs:
            self.set_inputs(inputs)
        else:
            self._apply_input_overrides(reset_initial_state=False)

        if not self._history:
            self._record_state(0.0, growth_this_step=0.0)

        if end is None:
            end = self._time + float(getattr(self, "communication_step", self.integration_step) or self.integration_step)
        target = float(end)
        if target <= self._time:
            self._publish_outputs(self._time)
            return dict(self._outputs)

        current = self._time
        while current < target - 1e-12:
            h = min(self.integration_step, target - current)
            growth = self._step(h)
            current += h
            self._record_state(current, growth_this_step=growth)

        self._time = current
        self._publish_outputs(self._time)
        return dict(self._outputs)

    def get_outputs(self) -> dict[str, BioSignal]:
        return dict(self._outputs)

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
                "description": "Cell count over time.",
                "data": {
                    "title": "Colony Growth",
                    "x_unit": "hour",
                    "y_unit": "cells",
                    "series": [
                        {"name": "Cells", "points": [[point["t"], point["cells"]] for point in self._history]},
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
                        ["Why did it slow down?", self._takeaway()],
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
            return None
        value = _signal_value(signal)
        if isinstance(value, dict):
            for key in ("value", "count", "payload"):
                if key in value:
                    value = value[key]
                    break
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

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

    def _step(self, h: float) -> float:
        if self._cells <= self._epsilon or self._food <= self._epsilon or self.growth_rate <= self._epsilon:
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
        return growth

    def _record_state(self, t: float, *, growth_this_step: float) -> None:
        self._history.append(
            {
                "t": float(t),
                "cells": float(self._cells),
                "food_remaining": float(self._food),
                "food_used": float(self.available_food - self._food),
                "growth_this_step": float(growth_this_step),
                "space_used_percent": float(self._space_used_percent()),
                "phase": self._phase(),
                "limiting_factor": self._limiting_factor(),
            }
        )

    def _publish_outputs(self, t: float) -> None:
        source_name = getattr(self, "_world_name", self.__class__.__name__)
        outputs = self.outputs()
        self._outputs = {
            "colony_state": RecordSignal(
                source=source_name,
                name="colony_state",
                value={
                    "t": float(t),
                    "cells": float(self._cells),
                    "food_remaining": float(self._food),
                    "food_used": float(self.available_food - self._food),
                    "growth_this_step": float(self._last_growth),
                    "phase": self._phase(),
                    "limiting_factor": self._limiting_factor(),
                    "space_used_percent": float(self._space_used_percent()),
                },
                emitted_at=float(t),
                spec=outputs["colony_state"],
            ),
            "lesson_summary": RecordSignal(
                source=source_name,
                name="lesson_summary",
                value={
                    "headline": self._headline(),
                    "takeaway": self._takeaway(),
                    "limiting_factor": self._limiting_factor(),
                    "starting_cells": float(self.initial_cells),
                    "final_cells": float(self._cells),
                    "cell_change": float(self._cells - self.initial_cells),
                    "food_used": float(self.available_food - self._food),
                    "hours": float(t),
                },
                emitted_at=float(t),
                spec=outputs["lesson_summary"],
            ),
        }

    def _phase(self) -> str:
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
        if self._cells <= self.initial_cells + self._epsilon:
            return "The colony did not grow."
        return f"The colony grew from {self.initial_cells:.1f} to {self._cells:.1f} cells."

    def _takeaway(self) -> str:
        limiting_factor = self._limiting_factor()
        if limiting_factor == "food":
            return "Cells multiplied until food became the main bottleneck."
        if limiting_factor == "space":
            return "Cells multiplied until the space limit became the main bottleneck."
        if limiting_factor == "growth rate is zero":
            return "Growth stayed flat because the growth rate was set to zero."
        return "Food and space are still available, so the colony is still in an easy-growth phase."
