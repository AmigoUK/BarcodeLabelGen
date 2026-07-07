"""Single source of the app version for runtime reporting.

Keep in sync with pyproject.toml `[project] version` on every release —
the Docker image installs dependencies with `--no-install-project`, so
importlib.metadata can't see the package there.
"""

APP_VERSION = "0.23.0"
