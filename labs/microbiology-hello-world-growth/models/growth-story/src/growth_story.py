# SPDX-FileCopyrightText: 2026-present Biosimulant Team
#
# SPDX-License-Identifier: Apache-2.0
"""Plain-language story reporter for the microbiology hello-world lab."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional, TYPE_CHECKING

from biosim import BioModule
from biosim.signals import BioSignal, RecordSignal, SignalSpec

if TYPE_CHECKING:  # pragma: no cover - typing only
    from biosim.visuals import VisualSpec


def _signal_value(signal: BioSignal | None) -> Any:
    if signal is None:
        return None
    value = getattr(signal, "value", None)
    if isinstance(value, dict) and set(value.keys()) == {"payload"}:
        return value["payload"]
    return value


def _record_spec(schema: dict[str, str], description: str) -> SignalSpec:
    return SignalSpec.record(schema=schema, description=description)


class GrowthStoryReporter(BioModule):
    """Combine setup and growth outputs into a friendly explanation."""

    DEFAULT_SETUP: dict[str, Any] = {
        "initial_cells": 10.0,
        "available_food": 80.0,
        "growth_rate": 0.8,
        "space_limit": 200.0,
        "food_per_new_cell": 1.0,
        "setup_label": "small starter plate",
    }
    DEFAULT_COLONY: dict[str, Any] = {
        "t": 12.0,
        "cells": 10.0,
        "food_remaining": 80.0,
        "food_used": 0.0,
        "death_this_step": 0.0,
        "peak_cells": 10.0,
        "phase": "growing",
        "limiting_factor": "none yet",
        "space_used_percent": 5.0,
    }
    DEFAULT_LESSON: dict[str, Any] = {
        "headline": "The colony is ready to grow.",
        "takeaway": "Food and space are available.",
        "limiting_factor": "none yet",
        "starting_cells": 10.0,
        "final_cells": 10.0,
        "cell_change": 0.0,
        "food_used": 0.0,
        "hours": 0.0,
    }

    def __init__(self, integration_step: float = 0.25) -> None:
        if integration_step <= 0:
            raise ValueError("integration_step must be positive")
        self.integration_step = float(integration_step)
        self._inputs: dict[str, BioSignal] = {}
        self._outputs: dict[str, RecordSignal] = {}
        self._story: dict[str, Any] = {}
        self._next_steps: dict[str, Any] = {}
        self._time = 0.0

    def inputs(self) -> dict[str, SignalSpec]:
        return {
            "growth_setup": _record_spec(
                {
                    "initial_cells": "float",
                    "available_food": "float",
                    "growth_rate": "float",
                    "space_limit": "float",
                    "food_per_new_cell": "float",
                    "setup_label": "str",
                },
                "Starting setup from the starter-culture model.",
            ),
            "colony_state": _record_spec(
                {
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
                "Current colony state from the growth model.",
            ),
            "lesson_summary": _record_spec(
                {
                    "headline": "str",
                    "takeaway": "str",
                    "limiting_factor": "str",
                    "starting_cells": "float",
                    "final_cells": "float",
                    "cell_change": "float",
                    "food_used": "float",
                    "hours": "float",
                },
                "Plain-language growth summary from the growth model.",
            ),
        }

    def outputs(self) -> dict[str, SignalSpec]:
        return {
            "hello_world_story": _record_spec(
                {
                    "title": "str",
                    "opening": "str",
                    "result": "str",
                    "why_it_matters": "str",
                    "hours": "float",
                },
                "Beginner-friendly story for the full hello-world run.",
            ),
            "next_steps": _record_spec(
                {
                    "headline": "str",
                    "suggestions": "list",
                },
                "Simple suggestions for changing the next run.",
            ),
            "run_metadata": _record_spec(
                {"status": "str", "message": "str"},
                "Story reporter status.",
            ),
        }

    def setup(self, config: Optional[dict[str, Any]] = None) -> None:
        self.reset()

    def reset(self) -> None:
        self._inputs = {}
        self._outputs = {}
        self._story = {}
        self._next_steps = {}
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
        self._refresh_from_inputs(self._time)
        return dict(self._outputs)

    def get_outputs(self) -> dict[str, RecordSignal]:
        if self._inputs:
            self._refresh_from_inputs(self._time)
        return dict(self._outputs)

    def visualize(self) -> Optional["VisualSpec" | list["VisualSpec"]]:
        if self._inputs:
            self._refresh_from_inputs(self._time)
        if not self._story or not self._next_steps:
            return None
        return [
            {
                "render": "table",
                "description": "Plain-language story for the run.",
                "data": {
                    "title": "Hello World Story",
                    "columns": ["Part", "Meaning"],
                    "rows": [
                        ["Start", self._story["opening"]],
                        ["Result", self._story["result"]],
                        ["Why it matters", self._story["why_it_matters"]],
                    ],
                },
            },
            {
                "render": "table",
                "description": "Simple ideas for the next run.",
                "data": {
                    "title": "Try Next",
                    "columns": ["Idea"],
                    "rows": [[item] for item in self._next_steps["suggestions"]],
                },
            },
        ]

    def _refresh_from_inputs(self, emitted_at: float) -> None:
        setup = self._coerce_record("growth_setup", self.DEFAULT_SETUP)
        colony = self._coerce_record("colony_state", self.DEFAULT_COLONY)
        lesson = self._coerce_record("lesson_summary", self.DEFAULT_LESSON)
        self._story = self._build_story(setup, colony, lesson)
        self._next_steps = self._build_next_steps(setup, colony, lesson)
        self._publish(emitted_at)

    def _coerce_record(self, name: str, default: dict[str, Any]) -> dict[str, Any]:
        value = _signal_value(self._inputs.get(name))
        if not isinstance(value, dict):
            return deepcopy(default)
        merged = deepcopy(default)
        merged.update(value)
        return merged

    def _build_story(self, setup: dict[str, Any], colony: dict[str, Any], lesson: dict[str, Any]) -> dict[str, Any]:
        start = float(setup.get("initial_cells", 0.0))
        final = float(colony.get("cells", lesson.get("final_cells", start)))
        peak = float(colony.get("peak_cells", max(start, final)))
        hours = float(colony.get("t", lesson.get("hours", self._time)))
        limiting = str(colony.get("limiting_factor", lesson.get("limiting_factor", "none yet")))
        gained = max(0.0, peak - start)
        if peak > final + 0.5:
            result = (
                f"After {hours:.1f} hours, the colony peaked at {peak:.1f} viable cells "
                f"and ended at {final:.1f}."
            )
        else:
            result = f"After {hours:.1f} hours, the colony reached {final:.1f} viable cells and gained {gained:.1f}."
        if limiting == "starvation":
            why_it_matters = (
                "Food ran out, so viable cells declined under starvation. "
                "This shows how Biosimulant can pass a setup through growth, resource use, and explanation."
            )
        else:
            why_it_matters = (
                f"The main limit is {limiting}. "
                "This shows how Biosimulant can pass a setup through a simulation and into an explanation."
            )
        return {
            "title": "Microbiology Hello World",
            "opening": (
                f"You started with {start:.1f} cells, {setup.get('available_food', 0.0):.1f} "
                f"food units, and room for {setup.get('space_limit', 0.0):.1f} cells."
            ),
            "result": result,
            "why_it_matters": why_it_matters,
            "hours": hours,
        }

    def _build_next_steps(
        self,
        setup: dict[str, Any],
        colony: dict[str, Any],
        lesson: dict[str, Any],
    ) -> dict[str, Any]:
        limiting = str(colony.get("limiting_factor", lesson.get("limiting_factor", "none yet")))
        suggestions = [
            "Increase food to see whether the colony grows longer.",
            "Lower the space limit to see crowding happen sooner.",
            "Set growth rate to zero to see a no-growth control.",
        ]
        if limiting == "starvation":
            headline = "Try adding food before starvation starts."
        elif limiting == "food":
            headline = "Try adding food next."
        elif limiting == "space":
            headline = "Try giving the colony more room next."
        elif limiting == "growth rate is zero":
            headline = "Try turning growth back on next."
        else:
            headline = "Try changing one knob and compare the story."
        return {"headline": headline, "suggestions": suggestions}

    def _publish(self, emitted_at: float) -> None:
        source_name = getattr(self, "_world_name", "story_reporter")
        specs = self.outputs()
        self._outputs = {
            "hello_world_story": RecordSignal(
                source=source_name,
                name="hello_world_story",
                value=dict(self._story),
                emitted_at=emitted_at,
                spec=specs["hello_world_story"],
            ),
            "next_steps": RecordSignal(
                source=source_name,
                name="next_steps",
                value=dict(self._next_steps),
                emitted_at=emitted_at,
                spec=specs["next_steps"],
            ),
            "run_metadata": RecordSignal(
                source=source_name,
                name="run_metadata",
                value={"status": "ok", "message": "Wrote the hello-world story."},
                emitted_at=emitted_at,
                spec=specs["run_metadata"],
            ),
        }
