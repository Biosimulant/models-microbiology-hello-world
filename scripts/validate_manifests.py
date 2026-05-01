#!/usr/bin/env python3
"""Validate model.yaml and lab.yaml manifests in labs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from simple_yaml import load_yaml_file


ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> dict[str, Any]:
    return load_yaml_file(path)


def _resolve_embedded_path(manifest_path: Path, raw_path: Any) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    target = (manifest_path.parent / raw_path.strip()).resolve()
    if ROOT not in target.parents and target != ROOT:
        return None
    return target


def _validate_model_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        manifest = _load_yaml(path)
    except Exception as exc:  # noqa: BLE001
        return [f"{path}: {exc}"]

    for key in ("schema_version", "title", "description", "standard"):
        value = manifest.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{path}: missing required '{key}'")

    biosim = manifest.get("biosim") if isinstance(manifest.get("biosim"), dict) else {}
    entrypoint = biosim.get("entrypoint") or manifest.get("entrypoint")
    if not isinstance(entrypoint, str) or not entrypoint.strip():
        errors.append(f"{path}: missing required 'biosim.entrypoint'")

    communication_step = biosim.get("communication_step")
    if communication_step is None:
        errors.append(f"{path}: missing required 'biosim.communication_step'")
    else:
        try:
            if float(communication_step) <= 0.0:
                errors.append(f"{path}: biosim.communication_step must be positive")
        except (TypeError, ValueError):
            errors.append(f"{path}: biosim.communication_step must be numeric")

    runtime = manifest.get("runtime") if isinstance(manifest.get("runtime"), dict) else {}
    deps = runtime.get("dependencies") if isinstance(runtime.get("dependencies"), dict) else {}
    packages = deps.get("packages") if isinstance(deps.get("packages"), list) else []
    for spec in packages:
        if not isinstance(spec, str) or "==" not in spec:
            errors.append(f"{path}: dependency package '{spec}' must be pinned with '=='")

    return errors


def _validate_lab_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        manifest = _load_yaml(path)
    except Exception as exc:  # noqa: BLE001
        return [f"{path}: {exc}"]

    models = manifest.get("models")
    if not isinstance(models, list) or not models:
        return [f"{path}: missing non-empty 'models' list"]

    runtime = manifest.get("runtime") if isinstance(manifest.get("runtime"), dict) else {}
    if runtime.get("duration") is None:
        errors.append(f"{path}: missing runtime.duration")
    if runtime.get("communication_step") is None:
        errors.append(f"{path}: missing runtime.communication_step")

    for idx, entry in enumerate(models):
        if not isinstance(entry, dict):
            errors.append(f"{path}: models[{idx}] must be a mapping")
            continue
        alias = entry.get("alias")
        if not isinstance(alias, str) or not alias.strip():
            errors.append(f"{path}: models[{idx}] missing required alias")

        local_path = entry.get("path")
        if not isinstance(local_path, str) or not local_path.strip():
            errors.append(f"{path}: models[{idx}] must define a non-empty path")
            continue

        target = _resolve_embedded_path(path, local_path)
        if target is None:
            errors.append(f"{path}: models[{idx}].path must stay within the repository: {local_path}")
        elif not target.exists():
            errors.append(f"{path}: models[{idx}].path does not exist: {local_path}")
        elif target.is_dir() and not any((target / name).exists() for name in ("model.yaml", "model.yml")):
            errors.append(f"{path}: models[{idx}].path is missing model.yaml/model.yml: {local_path}")

        if entry.get("package") is not None or entry.get("version") is not None:
            errors.append(f"{path}: models[{idx}] must not use package/version; use path only")

    return errors


def main() -> int:
    errors: list[str] = []

    model_manifests = sorted(ROOT.rglob("model.yaml"))
    lab_manifests = sorted(ROOT.rglob("lab.yaml"))

    for path in model_manifests:
        errors.extend(_validate_model_manifest(path))
    for path in lab_manifests:
        errors.extend(_validate_lab_manifest(path))

    if errors:
        print("Manifest validation failed:")
        for err in errors:
            print(f" - {err}")
        return 1

    print(f"Validated {len(model_manifests)} model manifest(s) and {len(lab_manifests)} lab manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
