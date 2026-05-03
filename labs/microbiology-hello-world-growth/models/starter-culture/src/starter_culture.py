# SPDX-FileCopyrightText: 2026-present Biosimulant Team
#
# SPDX-License-Identifier: Apache-2.0
"""Beginner-friendly starter culture setup model."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from biosim import BioModule
from biosim.signals import AcceptedSignalProfile, BioSignal, RecordSignal, SignalSpec

if TYPE_CHECKING:  # pragma: no cover - typing only
    from biosim.visuals import VisualSpec


def _signal_value(signal: BioSignal) -> Any:
    value = getattr(signal, "value", None)
    if isinstance(value, dict) and set(value.keys()) == {"payload"}:
        return value["payload"]
    return value


class StarterCultureSetup(BioModule):
    """Turn simple user controls into a structured growth setup record."""

    def __init__(
        self,
        initial_cells: float = 10.0,
        available_food: float = 80.0,
        growth_rate: float = 0.8,
        space_limit: float = 200.0,
        integration_step: float = 0.25,
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

        self.initial_cells = float(initial_cells)
        self.available_food = float(available_food)
        self.growth_rate = float(growth_rate)
        self.space_limit = float(space_limit)
        self.integration_step = float(integration_step)
        self._inputs: dict[str, BioSignal] = {}
        self._outputs: dict[str, RecordSignal] = {}
        self._setup: dict[str, Any] = {}
        self._time = 0.0

    def inputs(self) -> dict[str, SignalSpec]:
        return {
            "initial_cells": self._scalar_input_spec("cells", "Starting number of cells."),
            "available_food": self._scalar_input_spec("food_unit", "Food units available at the start."),
            "growth_rate": self._scalar_input_spec("1/hour", "How quickly cells can multiply."),
            "space_limit": self._scalar_input_spec("cells", "Approximate maximum colony size."),
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

    def setup(self, config: Optional[dict[str, Any]] = None) -> None:
        self._publish(0.0)

    def reset(self) -> None:
        self._inputs = {}
        self._outputs = {}
        self._setup = {}
        self._time = 0.0

    def set_inputs(self, inputs: dict[str, BioSignal]) -> None:
        self._inputs = dict(inputs or {})

    def advance_window(
        self,
        start: float | None = None,
        end: float | None = None,
        inputs: dict[str, BioSignal] | None = None,
    ) -> dict[str, RecordSignal]:
        if inputs:
            self.set_inputs(inputs)
        self._time = float(end if end is not None else self._time + self.integration_step)
        self._publish(self._time)
        return dict(self._outputs)

    def get_outputs(self) -> dict[str, RecordSignal]:
        return dict(self._outputs)

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
        value = _signal_value(signal)
        if isinstance(value, dict):
            for key in ("value", "count", "payload"):
                if key in value:
                    value = value[key]
                    break
        try:
            number = float(value)
        except (TypeError, ValueError):
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
        source_name = getattr(self, "_world_name", "starter_setup")
        specs = self.outputs()
        self._outputs = {
            "growth_setup": RecordSignal(
                source=source_name,
                name="growth_setup",
                value=dict(self._setup),
                emitted_at=emitted_at,
                spec=specs["growth_setup"],
            ),
            "setup_summary": RecordSignal(
                source=source_name,
                name="setup_summary",
                value=summary,
                emitted_at=emitted_at,
                spec=specs["setup_summary"],
            ),
            "run_metadata": RecordSignal(
                source=source_name,
                name="run_metadata",
                value=metadata,
                emitted_at=emitted_at,
                spec=specs["run_metadata"],
            ),
        }
