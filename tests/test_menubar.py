import threading

import pytest

menubar = pytest.importorskip("pomodoro.menubar",
                              reason="menu bar needs macOS with PyObjC")


class FakeMenuBar:
    """Stands in for the real menu bar; records what it was asked to show."""

    instances = []

    def __init__(self, on_stop):
        self.on_stop = on_stop
        self.updates = []
        self.closed = False
        FakeMenuBar.instances.append(self)

    def update(self, title, status):
        self.updates.append((title, status))

    def process_events(self, timeout):
        threading.Event().wait(0.001)

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def reset_fake():
    FakeMenuBar.instances.clear()


def run(timer):
    menubar.run_with_menubar(timer, menubar_factory=FakeMenuBar, refresh=0)
    return FakeMenuBar.instances[-1]


# --- formatting -------------------------------------------------------------

def test_format_title():
    assert menubar.format_title("Work", 1453) == "🍅 Work 24:13"
    assert menubar.format_title("Rest", 59) == "🍅 Rest 00:59"
    assert menubar.format_title(None, 0) == "🍅 --:--"


def test_format_status():
    assert menubar.format_status("Work", 1, 4) == "Cycle 1/4 - Work"
    assert menubar.format_status(None, 0, 0) == "Starting…"


# --- run_with_menubar -------------------------------------------------------

def test_shows_timer_state_and_closes_when_done():
    ticked = threading.Event()
    seen = threading.Event()

    def timer(on_tick, sleep):
        on_tick("Work", 2, 3, 754)
        ticked.set()
        seen.wait(5)  # stay on this tick until the menu bar has drawn it

    class Watcher(FakeMenuBar):
        def update(self, title, status):
            super().update(title, status)
            if ticked.is_set():
                seen.set()

    menubar.run_with_menubar(timer, menubar_factory=Watcher, refresh=0)
    bar = Watcher.instances[-1]
    assert ("🍅 Work 12:34", "Cycle 2/3 - Work") in bar.updates
    assert bar.closed


def test_completed_timer_returns_normally():
    bar = run(lambda on_tick, sleep: None)
    assert bar.closed


def test_stop_button_raises_keyboard_interrupt():
    def timer(on_tick, sleep):
        FakeMenuBar.instances[-1].on_stop()  # user clicks "Stop"
        sleep(60)  # interrupted immediately instead of waiting

    with pytest.raises(KeyboardInterrupt):
        run(timer)
    assert FakeMenuBar.instances[-1].closed


def test_ctrl_c_stops_timer_thread():
    stopped = threading.Event()

    def timer(on_tick, sleep):
        try:
            sleep(60)
        except menubar.TimerStopped:
            stopped.set()
            raise

    class CtrlC(FakeMenuBar):
        def process_events(self, timeout):
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        menubar.run_with_menubar(timer, menubar_factory=CtrlC, refresh=0)
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
