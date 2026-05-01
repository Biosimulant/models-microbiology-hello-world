from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


def test_default_construction_and_ports(biosim):
    from src.microbial_growth import MicrobialGrowthHelloWorld

    module = MicrobialGrowthHelloWorld()
    assert set(module.inputs()) == {"initial_cells", "available_food", "growth_rate", "space_limit"}
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


def test_no_growth_without_food(biosim):
    from src.microbial_growth import MicrobialGrowthHelloWorld

    module = MicrobialGrowthHelloWorld(initial_cells=10.0, available_food=0.0, growth_rate=0.8, space_limit=200.0)
    module.advance_window(0.0, 6.0)
    colony = module.get_outputs()["colony_state"].value

    assert colony["cells"] == pytest.approx(10.0)
    assert colony["food_remaining"] == pytest.approx(0.0)
    assert colony["limiting_factor"] == "food"


def test_food_and_space_bounds_are_preserved(biosim):
    from src.microbial_growth import MicrobialGrowthHelloWorld

    module = MicrobialGrowthHelloWorld(initial_cells=50.0, available_food=25.0, growth_rate=5.0, space_limit=60.0)
    module.advance_window(0.0, 24.0)
    colony = module.get_outputs()["colony_state"].value

    assert colony["food_remaining"] >= 0.0
    assert colony["cells"] <= 60.0 + 1e-9
    assert colony["cells"] >= 50.0


def test_visuals_return_expected_render_types(biosim):
    from src.microbial_growth import MicrobialGrowthHelloWorld

    module = MicrobialGrowthHelloWorld()
    module.advance_window(0.0, 4.0)
    visuals = module.visualize()

    assert isinstance(visuals, list)
    assert [visual["render"] for visual in visuals] == ["timeseries", "timeseries", "table"]
    assert visuals[2]["data"]["columns"] == ["Question", "Answer"]


def test_input_overrides_before_first_step(biosim):
    from biosim.signals import ScalarSignal, SignalSpec
    from src.microbial_growth import MicrobialGrowthHelloWorld

    module = MicrobialGrowthHelloWorld()
    scalar = SignalSpec.scalar(dtype="float64")
    module.set_inputs(
        {
            "initial_cells": ScalarSignal("test", "initial_cells", 5.0, 0.0, spec=scalar),
            "available_food": ScalarSignal("test", "available_food", 10.0, 0.0, spec=scalar),
            "space_limit": ScalarSignal("test", "space_limit", 20.0, 0.0, spec=scalar),
        }
    )
    module.advance_window(0.0, 1.0)
    colony = module.get_outputs()["colony_state"].value

    assert colony["cells"] >= 5.0
    assert colony["cells"] <= 20.0
    assert colony["food_remaining"] <= 10.0


def test_cli_human_output_runs():
    repo_root = Path(__file__).resolve().parents[4]
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


def test_cli_json_output_runs():
    repo_root = Path(__file__).resolve().parents[4]
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
    assert "colony_state" in payload["outputs"]
    assert payload["history"]
