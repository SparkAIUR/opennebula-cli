"""Fallback raw XML-RPC transport."""

from __future__ import annotations

import builtins
import re
import ssl
import xmlrpc.client
from typing import Any
from xml.etree import ElementTree

from opennebula_cli.sdk.exceptions import (
    ApiError,
    ApiFault,
    ConnectionError,
    TimeoutError,
    TlsError,
)

METHOD_PATTERN = re.compile(r"^one(?:\.[a-z][a-z0-9_]*){2,3}$")


class RawXmlRpcTransport:
    """Minimal raw XML-RPC escape hatch for unsupported PyONE cases."""

    def __init__(
        self,
        endpoint: str,
        session: str,
        *,
        timeout: float,
        verify_ssl: bool,
        cert_dir: str | None = None,
    ) -> None:
        self._session = session
        if endpoint.startswith("https://"):
            context = ssl.create_default_context()
            if cert_dir:
                context.load_verify_locations(capath=cert_dir)
            if not verify_ssl:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            transport: xmlrpc.client.Transport = xmlrpc.client.SafeTransport(context=context)
        else:
            transport = xmlrpc.client.Transport()
        transport.timeout = timeout  # type: ignore[attr-defined]
        self._server = xmlrpc.client.ServerProxy(endpoint, transport=transport, allow_none=True)

    @property
    def name(self) -> str:
        return "raw"

    @staticmethod
    def validate_method(method: str) -> None:
        """Reject malformed or private XML-RPC method names before contact."""

        if not METHOD_PATTERN.fullmatch(method) or "__" in method:
            raise ApiError(
                "Raw XML-RPC method must be a complete public one.* method name.",
                method=method,
                transport="raw",
            )

    def supports(self, method: str) -> bool:
        return bool(METHOD_PATTERN.fullmatch(method)) and "__" not in method

    def _invoke(self, method: str, *args: object) -> Any:
        self.validate_method(method)
        try:
            target: Any = getattr(self._server, method)
            response = target(self._session, *args)
            if (
                isinstance(response, (list, tuple))
                and len(response) == 3
                and isinstance(response[0], bool)
            ):
                success, payload, code = response
                if not success:
                    raise ApiFault(
                        str(payload),
                        fault_code=int(code),
                        fault_string=str(payload),
                        method=method,
                        transport=self.name,
                    )
                return payload
            return response
        except ApiFault:
            raise
        except xmlrpc.client.Fault as exc:
            raise ApiFault(
                str(exc),
                fault_code=int(exc.faultCode),
                fault_string=str(exc.faultString),
                method=method,
                transport=self.name,
            ) from exc
        except ssl.SSLError as exc:
            raise TlsError(str(exc), method=method, transport=self.name) from exc
        except builtins.TimeoutError as exc:
            raise TimeoutError(str(exc), method=method, transport=self.name) from exc
        except OSError as exc:
            raise ConnectionError(str(exc), method=method, transport=self.name) from exc
        except Exception as exc:  # pragma: no cover - depends on live backend
            raise ApiError(str(exc), method=method, transport=self.name) from exc

    @classmethod
    def _xml_value(cls, element: ElementTree.Element) -> object:
        children = list(element)
        if not children:
            return element.text or ""
        result: dict[str, object] = {}
        for child in children:
            value = cls._xml_value(child)
            if child.tag not in result:
                result[child.tag] = value
            elif isinstance(result[child.tag], list):
                existing = result[child.tag]
                assert isinstance(existing, list)
                existing.append(value)
            else:
                result[child.tag] = [result[child.tag], value]
        return result

    @classmethod
    def _materialize(cls, payload: object) -> object:
        if not isinstance(payload, str) or not payload.lstrip().startswith("<"):
            return payload
        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError:
            return payload
        return cls._xml_value(root)

    def call(self, method: str, *args: object) -> Any:
        """Invoke a method and materialize upstream XML into stable mappings."""

        return self._materialize(self._invoke(method, *args))

    def call_raw(self, method: str, *args: object) -> Any:
        """Invoke a method while preserving its literal server payload."""

        return self._invoke(method, *args)
