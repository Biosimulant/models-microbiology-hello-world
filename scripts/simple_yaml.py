"""Small YAML fallback for this repository's simple manifests.

PyYAML is still preferred when available. This parser intentionally supports
only the subset used by this repo: mappings, lists, quoted strings, numbers,
booleans, `{}`, and inline scalar lists.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_yaml_file(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        data = loads(path.read_text(encoding="utf-8"))
    else:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a mapping")
    return data


def loads(text: str) -> Any:
    lines: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        lines.append((indent, stripped))
    if not lines:
        return {}
    value, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise ValueError(f"could not parse line: {lines[index][1]}")
    return value


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if lines[index][1].startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_list(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    while index < len(lines):
        line_indent, stripped = lines[index]
        if line_indent < indent:
            break
        if line_indent != indent or not stripped.startswith("- "):
            break

        item_text = stripped[2:].strip()
        index += 1
        if not item_text:
            if index < len(lines) and lines[index][0] > line_indent:
                child, index = _parse_block(lines, index, lines[index][0])
                items.append(child)
            else:
                items.append(None)
            continue

        if _looks_like_key_value(item_text):
            key, value_text = _split_key_value(item_text)
            item: dict[str, Any] = {key: _parse_scalar(value_text) if value_text else None}
            if index < len(lines) and lines[index][0] > line_indent:
                child, index = _parse_block(lines, index, lines[index][0])
                if not isinstance(child, dict):
                    raise ValueError("list item continuation must be a mapping")
                item.update(child)
            items.append(item)
            continue

        items.append(_parse_scalar(item_text))

    return items, index


def _parse_mapping(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    mapping: dict[str, Any] = {}
    while index < len(lines):
        line_indent, stripped = lines[index]
        if line_indent < indent:
            break
        if line_indent != indent or stripped.startswith("- "):
            break
        if not _looks_like_key_value(stripped):
            raise ValueError(f"expected key/value line: {stripped}")

        key, value_text = _split_key_value(stripped)
        index += 1
        if value_text:
            mapping[key] = _parse_scalar(value_text)
        elif index < len(lines) and lines[index][0] > line_indent:
            child, index = _parse_block(lines, index, lines[index][0])
            mapping[key] = child
        else:
            mapping[key] = None

    return mapping, index


def _looks_like_key_value(value: str) -> bool:
    return ":" in value and not value.startswith(("'", '"'))


def _split_key_value(value: str) -> tuple[str, str]:
    key, raw_value = value.split(":", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"empty key in line: {value}")
    return key, raw_value.strip()


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "{}":
        return {}
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    try:
        if any(char in value for char in (".", "e", "E")):
            return float(value)
        return int(value)
    except ValueError:
        return value
