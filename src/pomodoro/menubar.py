"""Live countdown in the macOS menu bar, using PyObjC."""

import threading

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSEventMaskAny,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from Foundation import NSDate, NSDefaultRunLoopMode, NSObject

from pomodoro.cli import format_time

ICON = "🍅"
REFRESH_SECONDS = 0.25


class TimerStopped(Exception):
    """Raised inside the timer thread when the user stops the timer."""


def format_title(phase, remaining):
    """Menu bar text, e.g. '🍅 Work 24:13'."""
    if phase is None:
        return f"{ICON} --:--"
    return f"{ICON} {phase} {format_time(remaining)}"


def format_status(phase, cycle, cycles):
    """Menu item text, e.g. 'Cycle 1/4 - Work'."""
    if phase is None:
        return "Starting…"
    return f"Cycle {cycle}/{cycles} - {phase}"


class TimerThread:
    """Runs timer(on_tick=..., sleep=...) in a background thread.

    AppKit must run on the main thread, so the timer runs here and only
    records its state; the main thread reads that state to draw the menu bar.
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


class _MenuTarget(NSObject):
    """Receives clicks on the Stop menu item."""

    def initWithCallback_(self, callback):
        self = objc.super(_MenuTarget, self).init()
        if self is None:
            return None
        self.callback = callback
        return self

    def stop_(self, _sender):
        self.callback()


class MenuBar:
    """A menu bar item showing a title, a status line and a Stop button."""

    def __init__(self, on_stop):
        self.app = NSApplication.sharedApplication()
        # Show in the menu bar only, with no Dock icon.
        self.app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength)
        # No action, so the menu shows it greyed out as plain information.
        self.status = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "", None, "")
        self._target = _MenuTarget.alloc().initWithCallback_(on_stop)
        stop = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Stop", "stop:", "")
        stop.setTarget_(self._target)

        menu = NSMenu.alloc().init()
        menu.addItem_(self.status)
        menu.addItem_(NSMenuItem.separatorItem())
        menu.addItem_(stop)
        self.item.setMenu_(menu)

        self.app.finishLaunching()

    def update(self, title, status):
        self.item.button().setTitle_(title)
        self.status.setTitle_(status)

    def process_events(self, timeout):
        """Handle clicks and redraws for up to `timeout` seconds."""
        deadline = NSDate.dateWithTimeIntervalSinceNow_(timeout)
        while True:
            event = self.app.nextEventMatchingMask_untilDate_inMode_dequeue_(
                NSEventMaskAny, deadline, NSDefaultRunLoopMode, True)
            if event is None:
                return
            self.app.sendEvent_(event)

    def close(self):
        NSStatusBar.systemStatusBar().removeStatusItem_(self.item)


def run_with_menubar(timer, menubar_factory=MenuBar, refresh=REFRESH_SECONDS):
    """Run timer(on_tick=..., sleep=...) while showing it in the menu bar.

    Raises KeyboardInterrupt if the timer is stopped before it finishes,
    either from the menu bar or with Ctrl+C.
    """
    worker = TimerThread(timer)
    bar = menubar_factory(on_stop=worker.stop)
    worker.start()
    try:
        # Python handles Ctrl+C between calls here, raising KeyboardInterrupt.
        while not worker.finished:
            phase, cycle, cycles, remaining = worker.state
            bar.update(format_title(phase, remaining),
                       format_status(phase, cycle, cycles))
            bar.process_events(refresh)
    finally:
        worker.stop()
        worker.join()
        bar.close()

    if worker.error:
        raise worker.error
    if not worker.completed:
        raise KeyboardInterrupt
