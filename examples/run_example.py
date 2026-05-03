#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any


def _load_biosim_repo_paths(root: Path) -> None:
    for parent in [root, *root.parents]:
        for candidate in (parent / "biosim" / "src", parent / "bsim-active" / "biosim" / "src"):
            if (candidate / "biosim").is_dir() and str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
                return


def _load_yaml_file(path: Path) -> dict[str, Any]:
    for parent in [path.resolve().parent, *path.resolve().parents]:
        scripts_dir = parent / "scripts"
        if (scripts_dir / "simple_yaml.py").is_file():
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            break
    from simple_yaml import load_yaml_file

    loaded = load_yaml_file(path)
    if not isinstance(loaded, dict):
        raise ValueError(f"expected mapping config in {path}")
    return loaded


def _split_entrypoint(entrypoint: str) -> tuple[str, str]:
    if ":" in entrypoint:
        return tuple(entrypoint.split(":", 1))  # type: ignore[return-value]
    return tuple(entrypoint.rsplit(".", 1))  # type: ignore[return-value]


def _import_entrypoint(model_dir: Path, entrypoint: str) -> type:
    if str(model_dir) not in sys.path:
        sys.path.insert(0, str(model_dir))
    module_name, class_name = _split_entrypoint(entrypoint)
    return getattr(importlib.import_module(module_name), class_name)


def _signal_to_dict(signal: Any) -> dict[str, Any]:
    if hasattr(signal, "to_dict"):
        return signal.to_dict()
    return {
        "name": getattr(signal, "name", None),
        "source": getattr(signal, "source", None),
        "emitted_at": getattr(signal, "emitted_at", None),
        "value": getattr(signal, "value", None),
    }


def _ascii_bar(value: float, maximum: float, *, width: int = 24) -> str:
    if maximum <= 0:
        filled = 0
    else:
        filled = max(0, min(width, round((value / maximum) * width)))
    return "#" * filled + "." * (width - filled)


def _select_timeline_points(history: list[dict[str, Any]], count: int = 7) -> list[dict[str, Any]]:
    if len(history) <= count:
        return history
    indexes = sorted({round(i * (len(history) - 1) / (count - 1)) for i in range(count)})
    return [history[index] for index in indexes]


def _load_lab_world(lab_dir: Path, *, input_overrides: dict[str, float], hours: float | None = None):
    from biosim import BioWorld
    from biosim.signals import ScalarSignal, SignalSpec
    from biosim.wiring import WiringBuilder

    lab = _load_yaml_file(lab_dir / "lab.yaml")
    runtime = lab.get("runtime") if isinstance(lab.get("runtime"), dict) else {}
    communication_step = float(runtime.get("communication_step", 0.25))
    duration = float(hours if hours is not None else runtime.get("duration", 12.0))

    world = BioWorld(communication_step=communication_step)
    builder = WiringBuilder(world)
    modules: dict[str, Any] = {}

    for model_entry in lab.get("models", []) or []:
        alias = str(model_entry["alias"])
        model_dir = (lab_dir / model_entry["path"]).resolve()
        manifest = _load_yaml_file(model_dir / "model.yaml")
        biosim = manifest.get("biosim") if isinstance(manifest.get("biosim"), dict) else {}
        model_cls = _import_entrypoint(model_dir, str(biosim["entrypoint"]))
        module = model_cls(**dict(model_entry.get("parameters") or {}))
        builder.add(alias, module)
        modules[alias] = module

    for wire in lab.get("wiring", []) or []:
        builder.connect(str(wire["from"]), [str(target) for target in wire.get("to", [])])

    builder.apply()
    world.setup({})

    signals_by_alias: dict[str, dict[str, Any]] = {}
    scalar_spec = SignalSpec.scalar(dtype="float64")
    io_block = lab.get("io") if isinstance(lab.get("io"), dict) else {}
    for item in io_block.get("inputs", []) or []:
        public_name = item.get("name") if isinstance(item, dict) else None
        maps_to = item.get("maps_to") if isinstance(item, dict) else None
        if public_name not in input_overrides or not isinstance(maps_to, str):
            continue
        alias, port = maps_to.split(".", 1)
        signals_by_alias.setdefault(alias, {})[port] = ScalarSignal(
            "example",
            port,
            float(input_overrides[public_name]),
            0.0,
            spec=scalar_spec,
        )

    for alias, signals in signals_by_alias.items():
        modules[alias].set_inputs(signals)

    return world, modules, duration


def _refresh_final_story(modules: dict[str, Any], duration: float) -> None:
    try:
        setup_outputs = modules["starter_setup"].get_outputs()
        growth_outputs = modules["microbial_growth"].get_outputs()
        story_reporter = modules["story_reporter"]
    except KeyError:
        return

    final_inputs = {
        "growth_setup": setup_outputs.get("growth_setup"),
        "colony_state": growth_outputs.get("colony_state"),
        "lesson_summary": growth_outputs.get("lesson_summary"),
    }
    final_inputs = {name: signal for name, signal in final_inputs.items() if signal is not None}
    if not final_inputs:
        return
    story_reporter.set_inputs(final_inputs)
    story_reporter.advance_window(start=duration, end=duration, inputs=final_inputs)


def _print_human(payload: dict[str, Any]) -> None:
    setup = payload["outputs"]["starter_setup"]["growth_setup"]["value"]
    colony = payload["outputs"]["microbial_growth"]["colony_state"]["value"]
    lesson = payload["outputs"]["microbial_growth"]["lesson_summary"]["value"]
    story = payload["outputs"]["story_reporter"]["hello_world_story"]["value"]
    next_steps = payload["outputs"]["story_reporter"]["next_steps"]["value"]
    history = payload["history"]
    max_cells = max(setup["space_limit"], max(point["cells"] for point in history))

    print("Biosimulant microbiology hello world")
    print("=" * 40)
    print("Story: choose a starting plate, watch viable cells grow, then read what happened.")
    print(
        "Setup: "
        f"{setup['initial_cells']:.1f} cells, "
        f"{setup['available_food']:.1f} food units, "
        f"{setup['growth_rate']:.2f}/hour growth, "
        f"{setup['space_limit']:.1f} cell space limit"
    )
    print("")
    print("Timeline")
    print("hour  viable cells  food left  colony")
    for point in _select_timeline_points(history):
        bar = _ascii_bar(float(point["cells"]), max_cells)
        print(
            f"{float(point['t']):>4.1f}  "
            f"{float(point['cells']):>12.1f}  "
            f"{float(point['food_remaining']):>9.1f}  "
            f"[{bar}]"
        )
    print("")
    print("Result")
    print(f"- {lesson['headline']}")
    print(f"- {lesson['takeaway']}")
    print(f"- {story['why_it_matters']}")
    print(f"- Main limit: {colony['limiting_factor']}")
    print(f"- Food used: {colony['food_used']:.1f} of {setup['available_food']:.1f} units")
    print(f"- Space used: {colony['space_used_percent']:.1f}%")
    print("")
    print("Try next")
    print(f"- {next_steps['headline']}")
    for suggestion in next_steps["suggestions"]:
        print(f"- {suggestion}")


def main() -> int:
    root = Path(__file__).resolve().parent
    _load_biosim_repo_paths(root)

    parser = argparse.ArgumentParser(description="Run the Biosimulant microbiology hello-world example.")
    parser.add_argument(
        "example",
        nargs="?",
        default="microbial-growth",
        choices=["microbial-growth"],
        help="Example folder to run.",
    )
    parser.add_argument("--config", type=Path, help="Explicit config path. Overrides example selection.")
    parser.add_argument("--hours", type=float, help="Run duration in hours.")
    parser.add_argument("--initial-cells", type=float, help="Starting number of cells.")
    parser.add_argument("--food", type=float, help="Starting food units.")
    parser.add_argument("--growth-rate", type=float, help="Maximum growth rate per hour.")
    parser.add_argument("--space-limit", type=float, help="Approximate maximum number of cells the space can hold.")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Print machine-readable JSON only.")
    parser.add_argument("--output-json", type=Path, help="Optional path to write the final payload as JSON.")
    args = parser.parse_args()

    config_path = args.config.resolve() if args.config else (root / args.example / "config.yaml")
    config = _load_yaml_file(config_path)
    lab_cfg = config.get("lab") if isinstance(config.get("lab"), dict) else {}
    lab_path = lab_cfg.get("path")
    if not isinstance(lab_path, str) or not lab_path.strip():
        raise ValueError("lab.path is required")
    lab_dir = (config_path.parent / Path(lab_path)).resolve()

    input_overrides = dict(config.get("inputs") or {})
    if args.initial_cells is not None:
        input_overrides["initial_cells"] = args.initial_cells
    if args.food is not None:
        input_overrides["available_food"] = args.food
    if args.growth_rate is not None:
        input_overrides["growth_rate"] = args.growth_rate
    if args.space_limit is not None:
        input_overrides["space_limit"] = args.space_limit

    runtime = config.get("runtime") if isinstance(config.get("runtime"), dict) else {}
    hours = float(args.hours if args.hours is not None else runtime.get("hours", 12.0))

    world, modules, duration = _load_lab_world(lab_dir, input_overrides=input_overrides, hours=hours)
    world.run(duration=duration)
    _refresh_final_story(modules, duration)

    outputs = {
        alias: {name: _signal_to_dict(signal) for name, signal in module.get_outputs().items()}
        for alias, module in modules.items()
    }
    payload = {
        "example": config.get("example_name", args.example),
        "config_path": str(config_path),
        "lab": str(lab_dir),
        "duration_hours": duration,
        "inputs": input_overrides,
        "outputs": outputs,
        "history": modules["microbial_growth"].history,
        "visuals": world.collect_visuals(),
    }

    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.json_output:
        print(json.dumps(payload, indent=2))
    else:
        _print_human(payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
