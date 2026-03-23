from threading import Lock


class ProxyPool:
    def __init__(self, proxies: list[str] | None):
        self._proxies = proxies or []
        self._index = 0
        self._lock = Lock()

    def next_proxy(self) -> str | None:
        if not self._proxies:
            return None
        with self._lock:
            proxy = self._proxies[self._index % len(self._proxies)]
            self._index += 1
            return proxy
