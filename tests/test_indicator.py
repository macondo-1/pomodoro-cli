import threading

import pytest

from pomodoro import indicator


class FakeIndicator:
    """Stands in for the menu bar or tray icon; records what it shows."""

    instances = []

    def __init__(self, on_stop):
        self.on_stop = on_stop
        self.updates = []
        self.closed = False
        FakeIndicator.instances.append(self)

    def update(self, title, status):
        self.updates.append((title, status))

    def process_events(self, timeout):
        threading.Event().wait(0.001)

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def reset_fake():
    FakeIndicator.instances.clear()


def run(timer):
    indicator.run_with_indicator(timer, FakeIndicator, refresh=0)
    return FakeIndicator.instances[-1]


# --- formatting -------------------------------------------------------------

def test_format_title():
    assert indicator.format_title("Work", 1453) == "🍅 Work 24:13"
    assert indicator.format_title("Rest", 59) == "🥫 Rest 00:59"
    assert indicator.format_title("Long rest", 900) == "💤 Long rest 15:00"
    assert indicator.format_title(None, 0) == "🍅 --:--"


def test_format_status():
    assert indicator.format_status("Work", 1, 4) == "Cycle 1/4 - Work"
    assert indicator.format_status(None, 0, 0) == "Starting…"


# --- run_with_indicator -----------------------------------------------------

def test_shows_timer_state_and_closes_when_done():
    ticked = threading.Event()
    seen = threading.Event()

    def timer(on_tick, sleep):
        on_tick("Work", 2, 3, 754)
        ticked.set()
        seen.wait(5)  # stay on this tick until the indicator has drawn it

    class Watcher(FakeIndicator):
        def update(self, title, status):
            super().update(title, status)
            if ticked.is_set():
                seen.set()

    indicator.run_with_indicator(timer, Watcher, refresh=0)
    bar = Watcher.instances[-1]
    assert ("🍅 Work 12:34", "Cycle 2/3 - Work") in bar.updates
    assert bar.closed


def test_completed_timer_returns_normally():
    bar = run(lambda on_tick, sleep: None)
    assert bar.closed


def test_stop_button_raises_keyboard_interrupt():
    def timer(on_tick, sleep):
        FakeIndicator.instances[-1].on_stop()  # user clicks "Stop"
        sleep(60)  # interrupted immediately instead of waiting

    with pytest.raises(KeyboardInterrupt):
        run(timer)
    assert FakeIndicator.instances[-1].closed


def test_ctrl_c_stops_timer_thread():
    stopped = threading.Event()

    def timer(on_tick, sleep):
        try:
            sleep(60)
        except indicator.TimerStopped:
            stopped.set()
            raise

    class CtrlC(FakeIndicator):
        def process_events(self, timeout):
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        indicator.run_with_indicator(timer, CtrlC, refresh=0)
    assert stopped.is_set()
    assert CtrlC.instances[-1].closed


def test_timer_errors_are_reraised():
    def timer(on_tick, sleep):
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        run(timer)


def test_timer_sleep_waits_when_not_stopped():
    def timer(on_tick, sleep):
        sleep(0.01)  # returns normally

    run(timer)
