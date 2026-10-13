import threading

from dispatchd.worker.main import run


def test_run_exits_immediately_when_already_stopped() -> None:
    stop = threading.Event()
    stop.set()

    assert run(stop, poll_interval_seconds=0) == 0


def test_run_stops_when_event_is_set() -> None:
    stop = threading.Event()
    timer = threading.Timer(0.05, stop.set)
    timer.start()

    iterations = run(stop, poll_interval_seconds=0.01)

    timer.join()
    assert iterations >= 1
