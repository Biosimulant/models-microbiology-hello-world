from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_yaml(path: Path) -> dict:
    scripts_dir = _repo_root() / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from simple_yaml import load_yaml_file

    loaded = load_yaml_file(path)
    assert isinstance(loaded, dict)
    return loaded


def test_lab_public_io_and_wiring_contract():
    lab = _load_yaml(Path(__file__).resolve().parents[1] / "lab.yaml")

    assert [model["alias"] for model in lab["models"]] == ["starter_setup", "microbial_growth", "story_reporter"]
    assert [item["name"] for item in lab["io"]["inputs"]] == [
        "initial_cells",
        "available_food",
        "growth_rate",
        "space_limit",
    ]
    assert [item["name"] for item in lab["io"]["outputs"]] == [
        "colony_state",
        "lesson_summary",
        "hello_world_story",
        "next_steps",
    ]
    assert lab["wiring"] == [
        {
            "from": "starter_setup.growth_setup",
            "to": ["microbial_growth.growth_setup", "story_reporter.growth_setup"],
        },
        {"from": "microbial_growth.colony_state", "to": ["story_reporter.colony_state"]},
        {"from": "microbial_growth.lesson_summary", "to": ["story_reporter.lesson_summary"]},
    ]


def test_multi_model_world_runs_and_produces_visuals():
    repo_root = _repo_root()
    examples_dir = repo_root / "examples"
    if str(examples_dir) not in sys.path:
        sys.path.insert(0, str(examples_dir))
    from run_example import _load_lab_world, _refresh_final_story

    lab_dir = repo_root / "labs" / "microbiology-hello-world-growth"
    world, modules, duration = _load_lab_world(
        lab_dir,
        input_overrides={
            "initial_cells": 10.0,
            "available_food": 80.0,
            "growth_rate": 0.8,
            "space_limit": 200.0,
        },
        hours=12.0,
    )
    world.run(duration=duration)
    _refresh_final_story(modules, duration)

    assert sorted(modules) == ["microbial_growth", "starter_setup", "story_reporter"]
    starter_outputs = modules["starter_setup"].get_outputs()
    growth_outputs = modules["microbial_growth"].get_outputs()
    story_outputs = modules["story_reporter"].get_outputs()

    assert starter_outputs["run_metadata"].value["status"] == "ok"
    assert growth_outputs["colony_state"].value["cells"] > 10.0
    assert "lesson_summary" in growth_outputs
    assert "hello_world_story" in story_outputs
    assert story_outputs["hello_world_story"].value["hours"] == duration
    assert "next_steps" in story_outputs

    visuals = world.collect_visuals()
    render_types = {visual["render"] for group in visuals for visual in group["visuals"]}
    assert "timeseries" in render_types
    assert "table" in render_types
