"""Live countdown in the Windows system tray, using pystray.

Tray icons can't show text, so the countdown goes in the icon's tooltip
(shown on hover); right-clicking the icon offers Stop.
"""

import threading
import time

import pystray
from PIL import Image, ImageDraw

from pomodoro.indicator import REFRESH_SECONDS, run_with_indicator

ICON_SIZE = 64


def make_icon_image(size=ICON_SIZE):
    """Draw a small tomato for the tray icon."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    s = size / 64
    draw.ellipse((4 * s, 12 * s, 60 * s, 62 * s), fill=(220, 53, 34))
    draw.polygon([(32 * s, 6 * s), (22 * s, 18 * s), (32 * s, 15 * s),
                  (42 * s, 18 * s)], fill=(46, 139, 60))
    return image


def format_tooltip(title, status):
    """Tooltip text: the countdown, then the cycle on a second line."""
    return f"{title}\n{status}"


class Tray:
    """A tray icon whose tooltip shows the countdown, with a Stop menu item.

    On Windows, pystray runs the icon's message loop in its own thread, so
    the main thread only has to change the tooltip.
    """

    START_TIMEOUT = 5

    def __init__(self, on_stop):
        self._tooltip = None
        self.icon = pystray.Icon(
            "pomodoro", make_icon_image(), "Pomodoro",
            menu=pystray.Menu(pystray.MenuItem(
                "Stop", lambda icon, item: on_stop())))
        # Wait until the loop is running: icon.stop() does nothing before.
        started = threading.Event()

        def setup(icon):
            icon.visible = True
            started.set()

        self.icon.run_detached(setup)
        started.wait(self.START_TIMEOUT)

    def update(self, title, status):
        tooltip = format_tooltip(title, status)
        if tooltip != self._tooltip:
            self.icon.title = tooltip
            self._tooltip = tooltip

    def process_events(self, timeout):
        # Clicks are handled on pystray's thread; time.sleep stays
        # interruptible by Ctrl+C on Windows.
        time.sleep(timeout)

    def close(self):
        # The loop hides the icon as it exits.
        self.icon.stop()


def run_with_tray(timer, tray_factory=Tray, refresh=REFRESH_SECONDS):
    """Run timer(on_tick=..., sleep=...) while showing it in the tray."""
    run_with_indicator(timer, tray_factory, refresh)
