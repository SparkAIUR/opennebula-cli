"""Secret redaction helpers."""

from collections.abc import Mapping


def redact_secret(value: str | None) -> str:
    """Return a stable redacted representation of a secret value."""

    if not value:
        return "<empty>"
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}***{value[-2:]}"


def redact_session(value: str | None) -> str:
    """Redact an OpenNebula session string."""

    if not value:
        return "<unset>"
    user, _, secret = value.partition(":")
    return f"{user}:{redact_secret(secret)}"


def redact_mapping(data: Mapping[str, object]) -> dict[str, object]:
    """Redact obvious secret-looking keys in a mapping."""

    result: dict[str, object] = {}
    for key, value in data.items():
        lowered = key.lower()
        if any(token in lowered for token in ("password", "secret", "token", "session", "auth")):
            result[key] = redact_secret(str(value) if value is not None else None)
        else:
            result[key] = value
    return result
