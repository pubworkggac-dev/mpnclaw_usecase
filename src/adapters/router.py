from src.adapters.base import FormatAdapter


class FormatRouter:
    def __init__(self):
        self._adapters: list[FormatAdapter] = []

    def register(self, adapter: FormatAdapter) -> None:
        self._adapters.append(adapter)

    def detect(self, topic: str, payload: dict) -> FormatAdapter | None:
        for adapter in self._adapters:
            if adapter.detect(topic, payload):
                return adapter
        return None

    def parse(self, topic: str, payload: dict):
        adapter = self.detect(topic, payload)
        if adapter:
            return adapter.parse(topic, payload)
        return None