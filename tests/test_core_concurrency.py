"""Basic concurrent safety smoke tests."""

import threading

from factorise.core import factorise


class ThreadNotJoinedError(Exception):
    """Raised when a worker thread fails to join within the timeout period."""


def test_core_thread_safety() -> None:
    def worker() -> None:
        for i in range(100, 200):
            res = factorise(i)
            assert res.original == i

    threads = [threading.Thread(target=worker, name=f"Worker-{i}") for i in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10.0)
        if thread.is_alive():
            raise ThreadNotJoinedError(f"Thread {thread.name} failed to complete within timeout.")
