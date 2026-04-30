"""Image service."""

from __future__ import annotations

import builtins
from typing import Any

from opennebula_cli.sdk.models.common import Ack, ensure_list, normalize_mapping, object_get
from opennebula_cli.sdk.models.image import Image, ImageOwnerSummary
from opennebula_cli.transports.base import OpenNebulaTransport


class ImageService:
    """Typed image operations."""

    def __init__(self, transport: OpenNebulaTransport) -> None:
        self._transport = transport

    def list(self) -> list[Image]:
        raw = self._transport.call("one.imagepool.info", -2, -1, -1)
        items = ensure_list(object_get(raw, "IMAGE"))
        return [Image.from_raw(item) for item in items]

    def show(self, image_id: int) -> Image:
        raw = self._transport.call("one.image.info", image_id)
        return Image.from_raw(raw)

    def show_full(self, image_id: int) -> dict[str, Any]:
        """Return normalized raw image data without dropping OpenNebula fields."""

        raw = self._transport.call("one.image.info", image_id)
        return normalize_mapping(raw)

    @staticmethod
    def _int_list(value: object) -> builtins.list[int]:
        items: builtins.list[int] = []
        for item in ensure_list(value):
            if item in (None, ""):
                continue
            try:
                items.append(int(str(item)))
            except (TypeError, ValueError):
                continue
        return items

    def owner(self, image_id: int) -> ImageOwnerSummary:
        """Summarize image ownership and VM references."""

        raw = self.show_full(image_id)
        image = Image.from_raw(raw)
        return ImageOwnerSummary(
            id=image.id,
            name=image.name,
            state=image.state,
            datastore_id=image.datastore_id,
            source=str(raw["SOURCE"]) if raw.get("SOURCE") not in (None, "") else None,
            path=str(raw["PATH"]) if raw.get("PATH") not in (None, "") else None,
            running_vms=self._int_list(raw.get("RUNNING_VMS")),
            vms=self._int_list(raw.get("VMS")),
            template=image.template,
        )

    def delete(self, image_id: int) -> Ack:
        self._transport.call("one.image.delete", image_id)
        return Ack(resource="image", id=image_id, action="delete")
