"""Guard against version drift.

`app/version.py` holds the runtime `APP_VERSION` constant because the Docker
image installs deps with `--no-install-project` (so `importlib.metadata` can't
see the package version) and does not ship `pyproject.toml` into the runtime
image. That constant must stay in lock-step with `pyproject.toml [project]
version`, which build/release tooling reads. This test fails CI whenever the
two drift — which is exactly what silently happened between v0.16.0 and v0.20.0.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from app.version import APP_VERSION


def test_app_version_matches_pyproject() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    pyproject_version = data["project"]["version"]
    assert pyproject_version == APP_VERSION, (
        f"app/version.py APP_VERSION ({APP_VERSION}) != "
        f"pyproject.toml version ({pyproject_version}) — bump both together"
    )
