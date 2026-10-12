"""Live countdown in the macOS menu bar, using PyObjC."""

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

from pomodoro.indicator import REFRESH_SECONDS, run_with_indicator


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
    """Run timer(on_tick=..., sleep=...) while showing it in the menu bar."""
    run_with_indicator(timer, menubar_factory, refresh)
