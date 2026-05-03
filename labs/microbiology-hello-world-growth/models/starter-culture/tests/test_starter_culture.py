from __future__ import annotations


def test_starter_setup_emits_growth_setup_from_defaults():
    from src.starter_culture import StarterCultureSetup

    module = StarterCultureSetup()
    assert set(module.inputs()) == {"initial_cells", "available_food", "growth_rate", "space_limit"}
    assert set(module.outputs()) == {"growth_setup", "setup_summary", "run_metadata"}

    module.advance_window(0.0, 0.25)
    outputs = module.get_outputs()
    setup = outputs["growth_setup"].value

    assert outputs["run_metadata"].value["status"] == "ok"
    assert setup["initial_cells"] == 10.0
    assert setup["available_food"] == 80.0
    assert setup["growth_rate"] == 0.8
    assert setup["space_limit"] == 200.0
    assert module.visualize()["render"] == "table"


def test_starter_setup_accepts_scalar_overrides():
    from biosim.signals import ScalarSignal, SignalSpec
    from src.starter_culture import StarterCultureSetup

    module = StarterCultureSetup()
    scalar = SignalSpec.scalar(dtype="float64")
    module.set_inputs(
        {
            "initial_cells": ScalarSignal("test", "initial_cells", 25.0, 0.0, spec=scalar),
            "available_food": ScalarSignal("test", "available_food", 120.0, 0.0, spec=scalar),
            "growth_rate": ScalarSignal("test", "growth_rate", 0.5, 0.0, spec=scalar),
            "space_limit": ScalarSignal("test", "space_limit", 150.0, 0.0, spec=scalar),
        }
    )
    module.advance_window(0.0, 0.25)
    setup = module.get_outputs()["growth_setup"].value

    assert setup["initial_cells"] == 25.0
    assert setup["available_food"] == 120.0
    assert setup["growth_rate"] == 0.5
    assert setup["space_limit"] == 150.0
