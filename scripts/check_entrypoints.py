#!/usr/bin/env python3
"""Verify that model manifest entrypoints are importable."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

from simple_yaml import load_yaml_file


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True

for parent in [ROOT, *ROOT.parents]:
    for candidate in (parent / "biosim" / "src", parent / "bsim-active" / "biosim" / "src"):
        if (candidate / "biosim").is_dir():
            sys.path.insert(0, str(candidate))
            break
    else:
        continue
    break


def _load_yaml(path: Path) -> dict[str, Any]:
    return load_yaml_file(path)


def _split_entrypoint(entrypoint: str) -> tuple[str, str]:
    if ":" in entrypoint:
        module_name, attr = entrypoint.split(":", 1)
    else:
        module_name, attr = entrypoint.rsplit(".", 1)
    return module_name, attr


def _clear_module_cache(module_name: str) -> None:
    root = module_name.split(".", 1)[0]
    for key in [name for name in sys.modules if name == root or name.startswith(f"{root}.")]:
        sys.modules.pop(key, None)


def main() -> int:
    errors: list[str] = []
    manifests = sorted(ROOT.rglob("model.yaml"))
    for manifest_path in manifests:
        try:
            manifest = _load_yaml(manifest_path)
            biosim = manifest.get("biosim") if isinstance(manifest.get("biosim"), dict) else {}
            entrypoint = biosim.get("entrypoint") or manifest.get("entrypoint")
            if not isinstance(entrypoint, str) or not entrypoint.strip():
                errors.append(f"{manifest_path}: missing biosim.entrypoint")
                continue

            module_name, attr = _split_entrypoint(entrypoint)
            model_root = manifest_path.parent
            sys.path.insert(0, str(model_root))
            try:
                _clear_module_cache(module_name)
                importlib.invalidate_caches()
                module = importlib.import_module(module_name)
                if not hasattr(module, attr):
                    errors.append(f"{manifest_path}: entrypoint attribute not found: {entrypoint}")
                    continue
                target = getattr(module, attr)
                if not callable(target):
                    errors.append(f"{manifest_path}: entrypoint is not callable: {entrypoint}")
            finally:
                if sys.path and sys.path[0] == str(model_root):
                    sys.path.pop(0)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{manifest_path}: {exc}")

    if errors:
        print("Entrypoint check failed:")
        for err in errors:
            print(f" - {err}")
        return 1

    print(f"Validated entrypoints for {len(manifests)} model manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
