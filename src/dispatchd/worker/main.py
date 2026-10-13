"""Worker entrypoint. Currently a stub loop; delivery logic arrives in milestone 1."""

import logging
import signal
import threading

from dispatchd.core.config import get_settings
from dispatchd.core.logging import configure_logging

logger = logging.getLogger(__name__)


def run(stop: threading.Event, poll_interval_seconds: float) -> int:
    """Run the worker loop until `stop` is set. Returns the number of iterations."""
    iterations = 0
    logger.info("worker started")
    while not stop.is_set():
        iterations += 1
        logger.debug("worker tick %d", iterations)
        stop.wait(poll_interval_seconds)
    logger.info("worker stopped")
    return iterations


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    stop = threading.Event()

    def handle_signal(signum: int, _frame: object) -> None:
        logger.info("received signal %d, shutting down", signum)
        stop.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    run(stop, settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    main()
