from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


def test_default_construction_and_ports(biosim):
    from src.microbial_growth import MicrobialGrowthHelloWorld

    module = MicrobialGrowthHelloWorld()
    assert set(module.inputs()) == {"growth_setup"}
    assert set(module.outputs()) == {"colony_state", "lesson_summary"}
    assert module.outputs()["colony_state"].emitted_unit == "cells"


def test_growth_with_food_and_space(biosim):
    from src.microbial_growth import MicrobialGrowthHelloWorld

    module = MicrobialGrowthHelloWorld(initial_cells=10.0, available_food=80.0, growth_rate=0.8, space_limit=200.0)
    module.advance_window(0.0, 6.0)
    colony = module.get_outputs()["colony_state"].value

    assert colony["cells"] > 10.0
    assert colony["food_remaining"] < 80.0
    assert colony["limiting_factor"] in {"none yet", "food", "space"}


def test_starvation_decline_without_food(biosim):
    from src.microbial_growth import MicrobialGrowthHelloWorld

    module = MicrobialGrowthHelloWorld(initial_cells=10.0, available_food=0.0, growth_rate=0.8, space_limit=200.0)
    module.advance_window(0.0, 6.0)
    colony = module.get_outputs()["colony_state"].value

    assert colony["cells"] < 10.0
    assert colony["food_remaining"] <= 1e-6
    assert colony["death_this_step"] > 0.0
    assert colony["limiting_factor"] == "starvation"


def test_food_and_space_bounds_are_preserved(biosim):
    from src.microbial_growth import MicrobialGrowthHelloWorld

    module = MicrobialGrowthHelloWorld(initial_cells=50.0, available_food=25.0, growth_rate=5.0, space_limit=60.0)
    module.advance_window(0.0, 24.0)
    colony = module.get_outputs()["colony_state"].value

    assert colony["food_remaining"] >= 0.0
    assert colony["cells"] <= 60.0 + 1e-9
    assert colony["cells"] >= 0.0
    assert colony["peak_cells"] <= 60.0 + 1e-9


def test_viable_cells_decline_after_food_is_exhausted(biosim):
    from src.microbial_growth import MicrobialGrowthHelloWorld

    module = MicrobialGrowthHelloWorld(initial_cells=10.0, available_food=80.0, growth_rate=0.8, space_limit=200.0)
    module.advance_window(0.0, 50.0)
    colony = module.get_outputs()["colony_state"].value
    peak_cells = max(point["cells"] for point in module.history)

    assert colony["food_remaining"] <= 1e-6
    assert colony["limiting_factor"] == "starvation"
    assert peak_cells > colony["cells"]
    assert colony["peak_cells"] == pytest.approx(peak_cells)


def test_visuals_return_expected_render_types(biosim):
    from src.microbial_growth import MicrobialGrowthHelloWorld

    module = MicrobialGrowthHelloWorld()
    module.advance_window(0.0, 4.0)
    visuals = module.visualize()

    assert isinstance(visuals, list)
    assert [visual["render"] for visual in visuals] == ["timeseries", "timeseries", "table"]
    assert visuals[0]["data"]["series"][0]["name"] == "Viable cells"
    assert visuals[2]["data"]["columns"] == ["Question", "Answer"]


def test_input_overrides_before_first_step(biosim):
    from biosim.signals import RecordSignal, SignalSpec
    from src.microbial_growth import MicrobialGrowthHelloWorld

    module = MicrobialGrowthHelloWorld()
    setup = {
        "initial_cells": 5.0,
        "available_food": 10.0,
        "growth_rate": 0.8,
        "space_limit": 20.0,
        "food_per_new_cell": 1.0,
        "setup_label": "test plate",
    }
    setup_spec = SignalSpec.record(schema=module.inputs()["growth_setup"].schema)
    module.set_inputs(
        {
            "growth_setup": RecordSignal(
                source="test",
                name="growth_setup",
                value=setup,
                emitted_at=0.0,
                spec=setup_spec,
            ),
        }
    )
    module.advance_window(0.0, 1.0)
    colony = module.get_outputs()["colony_state"].value

    assert colony["cells"] >= 5.0
    assert colony["cells"] <= 20.0
    assert colony["food_remaining"] <= 10.0


def test_cli_human_output_runs():
    repo_root = Path(__file__).resolve().parents[5]
    runner = repo_root / "examples" / "run_example.py"
    completed = subprocess.run(
        [sys.executable, str(runner), "microbial-growth", "--hours", "2"],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "Biosimulant microbiology hello world" in completed.stdout
    assert "Timeline" in completed.stdout
    assert "Result" in completed.stdout
    assert "Try next" in completed.stdout


def test_cli_json_output_runs():
    repo_root = Path(__file__).resolve().parents[5]
    runner = repo_root / "examples" / "run_example.py"
    completed = subprocess.run(
        [sys.executable, str(runner), "microbial-growth", "--hours", "2", "--json"],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["example"] == "microbial-growth"
    assert payload["duration_hours"] == 2.0
    assert "starter_setup" in payload["outputs"]
    assert "colony_state" in payload["outputs"]["microbial_growth"]
    assert "hello_world_story" in payload["outputs"]["story_reporter"]
    assert payload["history"]
    assert payload["visuals"]
