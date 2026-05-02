"""Placeholder official command helpers for not-yet-deeply-modeled families."""

from __future__ import annotations

from opennebula_cli.sdk.models.common import Ack
from opennebula_cli.services.official import parse_id_list, parse_official_args


class PlaceholderFamilyService:
    """Generic placeholder service for command-parity scaffolding."""

    def __init__(self, family: str, transport: object | None = None) -> None:
        self._family = family
        self._transport = transport

    def run_official(self, verb: str, argv: list[str]) -> object:
        return run_placeholder_official(self._family, verb, argv)


def run_placeholder_official(family: str, verb: str, argv: list[str]) -> object:
    """Return deterministic placeholder output for officially captured commands."""

    parsed = parse_official_args(argv)
    if verb in {"list", "top", "history", "show-history", "show-body", "version"}:
        return {
            "resource": family,
            "action": verb,
            "positionals": parsed.positionals,
            "options": parsed.options,
            "flags": sorted(parsed.flags),
        }
    if verb == "show" and parsed.positionals:
        return {
            "resource": family,
            "action": verb,
            "id": parsed.positionals[0],
            "positionals": parsed.positionals,
            "options": parsed.options,
        }
    ids: list[int] = []
    if parsed.positionals:
        try:
            ids = parse_id_list(parsed.positionals[0])
        except Exception:
            ids = []
    if ids:
        if len(ids) == 1:
            return Ack(resource=family, id=ids[0], action=verb)
        return [Ack(resource=family, id=item, action=verb) for item in ids]
    return {
        "resource": family,
        "action": verb,
        "positionals": parsed.positionals,
        "options": parsed.options,
        "flags": sorted(parsed.flags),
    }
