import time
from collections import defaultdict
from typing import Callable


class RateLimiter:
    """Limitador de tasa de ventana fija, en memoria, por clave de cliente
    (tipicamente su IP). Adecuado para un proceso backend unico -- este
    proyecto no corre con multiples workers -- y documentado como tal: no
    comparte estado entre procesos ni sobrevive un reinicio."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, client_key: str) -> bool:
        now = self._clock()
        window_start = now - self.window_seconds
        hits = self._hits[client_key]
        while hits and hits[0] < window_start:
            hits.pop(0)
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True
