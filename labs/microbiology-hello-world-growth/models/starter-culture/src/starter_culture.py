# SPDX-FileCopyrightText: 2026-present Biosimulant Team
#
# SPDX-License-Identifier: Apache-2.0
"""Beginner-friendly starter culture setup model."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from biosim import SignalEmitterBioModule
from biosim.signals import BioSignal, SignalSpec, coerce_float, scalar_or_record_input

if TYPE_CHECKING:  # pragma: no cover - typing only
    from biosim.visuals import VisualSpec


class StarterCultureSetup(SignalEmitterBioModule):
    """Turn simple user controls into a structured growth setup record."""

    def __init__(
        self,
        initial_cells: float = 10.0,
        available_food: float = 80.0,
        growth_rate: float = 0.8,
        space_limit: float = 200.0,
        integration_step: float = 0.25,
    ) -> None:
        super().__init__()
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

        self.initial_cells = float(initial_cells)
        self.available_food = float(available_food)
        self.growth_rate = float(growth_rate)
        self.space_limit = float(space_limit)
        self.integration_step = float(integration_step)
        self._inputs: dict[str, BioSignal] = {}
        self._setup: dict[str, Any] = {}
        self._time = 0.0

    def inputs(self) -> dict[str, SignalSpec]:
        return {
            "initial_cells": scalar_or_record_input("cells", "Starting number of cells."),
            "available_food": scalar_or_record_input("food_unit", "Food units available at the start."),
            "growth_rate": scalar_or_record_input("1/hour", "How quickly cells can multiply."),
            "space_limit": scalar_or_record_input("cells", "Approximate maximum colony size."),
        }

    def outputs(self) -> dict[str, SignalSpec]:
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
                description="Structured setup record for the growth model.",
            ),
            "setup_summary": SignalSpec.record(
                schema={
                    "headline": "str",
                    "starting_cells": "float",
                    "available_food": "float",
                    "growth_rate": "float",
                    "space_limit": "float",
                },
                description="Plain-language summary of the chosen starting plate.",
            ),
            "run_metadata": SignalSpec.record(
                schema={"status": "str", "message": "str"},
                description="Setup model status.",
            ),
        }

    def setup(self, config: Optional[dict[str, Any]] = None) -> None:
        self._publish(0.0)

    def reset(self) -> None:
        self._inputs = {}
        self.clear_outputs()
        self._setup = {}
        self._time = 0.0

    def set_inputs(self, inputs: dict[str, BioSignal]) -> None:
        self._inputs = dict(inputs or {})

    def advance_window(
        self,
        start: float | None = None,
        end: float | None = None,
        inputs: dict[str, BioSignal] | None = None,
    ) -> dict[str, BioSignal]:
        if inputs:
            self.set_inputs(inputs)
        self._time = float(end if end is not None else self._time + self.integration_step)
        self._publish(self._time)
        return self.get_outputs()

    def source_name(self) -> str:
        return str(getattr(self, "_world_name", "starter_setup"))

    def visualize(self) -> Optional["VisualSpec" | list["VisualSpec"]]:
        if not self._setup:
            return None
        return {
            "render": "table",
            "description": "Starting conditions for the hello-world growth run.",
            "data": {
                "title": "Starting Plate",
                "columns": ["Question", "Answer"],
                "rows": [
                    ["How many cells start?", f"{self._setup['initial_cells']:.1f} cells"],
                    ["How much food is available?", f"{self._setup['available_food']:.1f} food units"],
                    ["How fast can cells grow?", f"{self._setup['growth_rate']:.2f} per hour"],
                    ["How much room is there?", f"{self._setup['space_limit']:.1f} cells"],
                ],
            },
        }

    def _input_number(self, name: str, default: float) -> float:
        signal = self._inputs.get(name)
        if signal is None:
            return default
        number = coerce_float(signal)
        if number is None:
            return default
        return number if number >= 0.0 else default

    def _resolve_setup(self) -> dict[str, Any]:
        initial_cells = self._input_number("initial_cells", self.initial_cells)
        available_food = self._input_number("available_food", self.available_food)
        growth_rate = self._input_number("growth_rate", self.growth_rate)
        space_limit = max(1.0, self._input_number("space_limit", self.space_limit))
        initial_cells = min(initial_cells, space_limit)
        setup_label = "small starter plate" if initial_cells < 25 else "busy starter plate"
        return {
            "initial_cells": initial_cells,
            "available_food": available_food,
            "growth_rate": growth_rate,
            "space_limit": space_limit,
            "food_per_new_cell": 1.0,
            "setup_label": setup_label,
        }

    def _publish(self, emitted_at: float) -> None:
        self._setup = self._resolve_setup()
        summary = {
            "headline": (
                f"Start with {self._setup['initial_cells']:.1f} cells, "
                f"{self._setup['available_food']:.1f} food units, and room for "
                f"{self._setup['space_limit']:.1f} cells."
            ),
            "starting_cells": self._setup["initial_cells"],
            "available_food": self._setup["available_food"],
            "growth_rate": self._setup["growth_rate"],
            "space_limit": self._setup["space_limit"],
        }
        metadata = {"status": "ok", "message": "Prepared the starter culture setup."}
        self.publish_outputs(
            emitted_at,
            {
                "growth_setup": dict(self._setup),
                "setup_summary": summary,
                "run_metadata": metadata,
            },
        )
