"""Builtin plugin metadata."""

from __future__ import annotations

from opennebula_cli.plugins.api import PluginSpec


class BuiltinPlugin:
    """Builtin core plugin placeholder."""

    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="builtin",
            commands=["vm", "host", "image", "template"],
        )

    def register(self) -> dict[str, object]:
        return {}


def plugin() -> BuiltinPlugin:
    """Return the builtin plugin instance."""

    return BuiltinPlugin()
