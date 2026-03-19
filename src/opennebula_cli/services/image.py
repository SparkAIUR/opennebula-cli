"""Image service."""

from __future__ import annotations

from opennebula_cli.sdk.models.common import Ack, ensure_list, object_get
from opennebula_cli.sdk.models.image import Image
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

    def delete(self, image_id: int) -> Ack:
        self._transport.call("one.image.delete", image_id)
        return Ack(resource="image", id=image_id, action="delete")
