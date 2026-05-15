from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FormatAdapter(Protocol):
    format_id: str

    def detect(self, topic: str, payload: dict) -> bool: ...

    def parse(self, topic: str, payload: dict) -> Any: ...

    def build_command_topic(
        self, product_key: str, device_key: str, service_name: str
    ) -> str: ...

    def build_command_payload(
        self, service_name: str, params: dict, message_id: str | None = None
    ) -> dict: ...