from __future__ import annotations

import sys
from pathlib import Path

import pytest


_MODEL_DIR = Path(__file__).resolve().parents[1]


def _find_biosim_src(start: Path) -> Path | None:
    for parent in [start, *start.parents]:
        for candidate in (parent / "biosim" / "src", parent / "bsim-active" / "biosim" / "src"):
            if (candidate / "biosim").is_dir():
                return candidate
    return None


def _ensure_test_paths() -> None:
    if str(_MODEL_DIR) not in sys.path:
        sys.path.insert(0, str(_MODEL_DIR))
    biosim_src = _find_biosim_src(_MODEL_DIR)
    if biosim_src is not None and str(biosim_src) not in sys.path:
        sys.path.insert(0, str(biosim_src))


_ensure_test_paths()


@pytest.fixture(scope="session", autouse=True)
def _paths():
    _ensure_test_paths()
