"""Shows the running timer outside the terminal (menu bar or system tray).

This module has no platform dependencies; menubar.py (macOS) and tray.py
(Windows) supply the widget that draws the state.
"""

import threading

from pomodoro.cli import format_time

ICON = "🍅"
REFRESH_SECONDS = 0.25


class TimerStopped(Exception):
    """Raised inside the timer thread when the user stops the timer."""


def format_title(phase, remaining):
    """Short countdown text, e.g. '🍅 Work 24:13'."""
    if phase is None:
        return f"{ICON} --:--"
    return f"{ICON} {phase} {format_time(remaining)}"


def format_status(phase, cycle, cycles):
    """Cycle text, e.g. 'Cycle 1/4 - Work'."""
    if phase is None:
        return "Starting…"
    return f"Cycle {cycle}/{cycles} - {phase}"


class TimerThread:
    """Runs timer(on_tick=..., sleep=...) in a background thread.

    GUI toolkits want the main thread, so the timer runs here and only
    records its state; the main thread reads that state to draw it.
    """

    def __init__(self, timer):
        self.state = (None, 0, 0, 0)  # phase, cycle, cycles, remaining
        self.completed = False  # True if the timer ran to the end
        self.error = None
        self._timer = timer
        self._stop_requested = threading.Event()
        self._thread = threading.Thread(target=self._work, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_requested.set()

    def join(self):
        self._thread.join()

    @property
    def finished(self):
        return not self._thread.is_alive()

    def _on_tick(self, phase, cycle, cycles, remaining):
        self.state = (phase, cycle, cycles, remaining)

    def _sleep(self, seconds):
        if self._stop_requested.wait(seconds):
            raise TimerStopped

    def _work(self):
        try:
            self._timer(on_tick=self._on_tick, sleep=self._sleep)
            self.completed = True
        except TimerStopped:
            pass
        except Exception as exc:
            self.error = exc


def run_with_indicator(timer, indicator_factory, refresh=REFRESH_SECONDS):
    """Run timer(on_tick=..., sleep=...) while showing it in an indicator.

    indicator_factory(on_stop=...) must return an object with
    update(title, status), process_events(timeout) and close().

    Raises KeyboardInterrupt if the timer is stopped before it finishes,
    either from the indicator or with Ctrl+C.
    """
    worker = TimerThread(timer)
    indicator = indicator_factory(on_stop=worker.stop)
    worker.start()
    try:
        # Python handles Ctrl+C between calls here, raising KeyboardInterrupt.
        while not worker.finished:
            phase, cycle, cycles, remaining = worker.state
            indicator.update(format_title(phase, remaining),
                             format_status(phase, cycle, cycles))
            indicator.process_events(refresh)
    finally:
        worker.stop()
        worker.join()
        indicator.close()

    if worker.error:
        raise worker.error
    if not worker.completed:
        raise KeyboardInterrupt
