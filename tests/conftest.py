"""Shared test configuration."""
import asyncio
import gc
import pytest


@pytest.fixture(autouse=True)
def _cleanup_asyncio_fixture():
    """Yield, then force explicit cleanup of async state between tests.

    This works around the Python 3.11 bpo-46358 bug where asyncio.Event
    objects created by third-party libraries (anyio, httpx ASGI transport)
    are garbage-collected with pending waiters, emitting a RuntimeWarning.
    By cancelling pending tasks, closing the loop, and collecting garbage
    *before* pytest moves on, we prevent the accumulated warnings.
    """
    yield
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_closed() and not loop.is_running():
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.close()
    except RuntimeError:
        pass
    gc.collect()
