"""Plugin discovery."""

from __future__ import annotations

from importlib.metadata import entry_points

from opennebula_cli.plugins.api import PluginSpec
from opennebula_cli.sdk.exceptions import PluginError


def load_plugins() -> list[PluginSpec]:
    """Load installed plugins and return their specs."""

    specs: list[PluginSpec] = []
    for entry_point in entry_points(group="opennebula_cli.plugins"):
        try:
            plugin_factory = entry_point.load()
            plugin = plugin_factory()
            specs.append(plugin.spec())
        except Exception as exc:  # pragma: no cover - import-time failures are environment-specific
            raise PluginError(f"Failed to load plugin '{entry_point.name}': {exc}") from exc
    return specs
