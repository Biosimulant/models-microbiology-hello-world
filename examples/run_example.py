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
    scripts_dir = path.resolve().parents[2] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from simple_yaml import load_yaml_file

    return load_yaml_file(path)


def _load_config(config_path: Path) -> dict[str, Any]:
    loaded = _load_yaml_file(config_path)
    if not isinstance(loaded, dict):
        raise ValueError(f"expected mapping config in {config_path}")
    return loaded


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


def _print_human(payload: dict[str, Any]) -> None:
    parameters = payload["parameters"]
    history = payload["history"]
    outputs = payload["outputs"]
    colony = outputs["colony_state"]["value"]
    lesson = outputs["lesson_summary"]["value"]
    max_cells = max(parameters["space_limit"], max(point["cells"] for point in history))

    print("Biosimulant microbiology hello world")
    print("=" * 40)
    print("Story: cells eat food, make more cells, then slow down when food or space runs low.")
    print(
        "Setup: "
        f"{parameters['initial_cells']:.1f} cells, "
        f"{parameters['available_food']:.1f} food units, "
        f"{parameters['growth_rate']:.2f}/hour growth, "
        f"{parameters['space_limit']:.1f} cell space limit"
    )
    print("")
    print("Timeline")
    print("hour     cells  food left  colony")
    for point in _select_timeline_points(history):
        bar = _ascii_bar(float(point["cells"]), max_cells)
        print(
            f"{float(point['t']):>4.1f}  "
            f"{float(point['cells']):>8.1f}  "
            f"{float(point['food_remaining']):>9.1f}  "
            f"[{bar}]"
        )
    print("")
    print("Result")
    print(f"- {lesson['headline']}")
    print(f"- {lesson['takeaway']}")
    print(f"- Main limit: {colony['limiting_factor']}")
    print(f"- Food used: {colony['food_used']:.1f} of {parameters['available_food']:.1f} units")
    print(f"- Space used: {colony['space_used_percent']:.1f}%")


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
    config = _load_config(config_path)
    model_cfg = config["model"]
    model_path = model_cfg.get("path")
    if not isinstance(model_path, str) or not model_path.strip():
        raise ValueError("model.path is required")
    model_root = (config_path.parent / Path(model_path)).resolve()
    if str(model_root) not in sys.path:
        sys.path.insert(0, str(model_root))

    module_name, class_name = model_cfg["class"].split(":", 1)
    module_cls = getattr(importlib.import_module(module_name), class_name)

    parameters = dict(model_cfg.get("parameters") or {})
    if args.initial_cells is not None:
        parameters["initial_cells"] = args.initial_cells
    if args.food is not None:
        parameters["available_food"] = args.food
    if args.growth_rate is not None:
        parameters["growth_rate"] = args.growth_rate
    if args.space_limit is not None:
        parameters["space_limit"] = args.space_limit

    runtime = config.get("runtime") if isinstance(config.get("runtime"), dict) else {}
    hours = float(args.hours if args.hours is not None else runtime.get("hours", 12.0))

    module = module_cls(**parameters)
    module.advance_window(0.0, hours)

    outputs = {name: _signal_to_dict(signal) for name, signal in module.get_outputs().items()}
    visuals = module.visualize() or []
    payload = {
        "example": config.get("example_name", args.example),
        "config_path": str(config_path),
        "duration_hours": hours,
        "parameters": parameters,
        "outputs": outputs,
        "history": module.history,
        "visuals": visuals,
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
