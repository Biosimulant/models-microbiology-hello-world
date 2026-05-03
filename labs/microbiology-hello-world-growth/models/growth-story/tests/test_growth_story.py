from __future__ import annotations


def _record(source: str, name: str, value: dict, spec):
    from biosim.signals import RecordSignal

    return RecordSignal(source=source, name=name, value=value, emitted_at=0.0, spec=spec)


def test_story_reporter_emits_story_and_next_steps():
    from src.growth_story import GrowthStoryReporter

    module = GrowthStoryReporter()
    specs = module.inputs()
    module.set_inputs(
        {
            "growth_setup": _record("setup", "growth_setup", dict(module.DEFAULT_SETUP), specs["growth_setup"]),
            "colony_state": _record(
                "growth",
                "colony_state",
                {
                    "t": 12.0,
                    "cells": 120.0,
                    "food_remaining": 0.0,
                    "food_used": 80.0,
                    "growth_this_step": 0.0,
                    "death_this_step": 0.2,
                    "peak_cells": 150.0,
                    "phase": "starvation decline",
                    "limiting_factor": "starvation",
                    "space_used_percent": 60.0,
                },
                specs["colony_state"],
            ),
            "lesson_summary": _record(
                "growth",
                "lesson_summary",
                {
                    "headline": "The colony grew from 10.0 to 120.0 cells.",
                    "takeaway": "Cells multiplied until food became the main bottleneck.",
                    "limiting_factor": "food",
                    "starting_cells": 10.0,
                    "final_cells": 120.0,
                    "cell_change": 110.0,
                    "food_used": 80.0,
                    "hours": 12.0,
                },
                specs["lesson_summary"],
            ),
        }
    )
    module.advance_window(0.0, 12.0)
    outputs = module.get_outputs()

    assert set(module.inputs()) == {"growth_setup", "colony_state", "lesson_summary"}
    assert set(module.outputs()) == {"hello_world_story", "next_steps", "run_metadata"}
    assert outputs["run_metadata"].value["status"] == "ok"
    assert "After 12.0 hours" in outputs["hello_world_story"].value["result"]
    assert "peaked at 150.0 viable cells" in outputs["hello_world_story"].value["result"]
    assert outputs["next_steps"].value["headline"] == "Try adding food before starvation starts."
    assert [visual["render"] for visual in module.visualize()] == ["table", "table"]
