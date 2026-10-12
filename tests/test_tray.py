import importlib
import sys
import types

import pytest


class FakeIcon:
    """Stands in for pystray.Icon; records what the tray was asked to do."""

    def __init__(self, name, image, title, menu):
        self.title = title
        self.menu = menu
        self.visible = False
        self.stopped = False

    def run_detached(self, setup):
        setup(self)

    def stop(self):
        self.stopped = True


class FakeMenuItem:
    def __init__(self, text, action):
        self.text = text
        self.action = action


class FakeDraw:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


@pytest.fixture
def tray(monkeypatch):
    """Import pomodoro.tray against fake pystray and PIL modules."""
    pystray = types.ModuleType("pystray")
    pystray.Icon = FakeIcon
    pystray.Menu = lambda *items: list(items)
    pystray.MenuItem = FakeMenuItem

    pil = types.ModuleType("PIL")
    pil.Image = types.SimpleNamespace(new=lambda *args: "image")
    pil.ImageDraw = types.SimpleNamespace(Draw=lambda image: FakeDraw())

    monkeypatch.setitem(sys.modules, "pystray", pystray)
    monkeypatch.setitem(sys.modules, "PIL", pil)
    monkeypatch.delitem(sys.modules, "pomodoro.tray", raising=False)
    return importlib.import_module("pomodoro.tray")


def test_format_tooltip(tray):
    assert (tray.format_tooltip("🍅 Work 24:13", "Cycle 1/4 - Work")
            == "🍅 Work 24:13\nCycle 1/4 - Work")


def test_icon_is_shown_on_start(tray):
    t = tray.Tray(on_stop=lambda: None)
    assert t.icon.visible


def test_update_sets_tooltip(tray):
    t = tray.Tray(on_stop=lambda: None)
    t.update("🍅 Work 12:34", "Cycle 2/3 - Work")
    assert t.icon.title == "🍅 Work 12:34\nCycle 2/3 - Work"


def test_stop_menu_item_calls_on_stop(tray):
    stopped = []
    t = tray.Tray(on_stop=lambda: stopped.append(True))
    (item,) = t.icon.menu
    assert item.text == "Stop"
    item.action(t.icon, item)
    assert stopped == [True]


def test_close_stops_icon(tray):
    t = tray.Tray(on_stop=lambda: None)
    t.close()
    assert t.icon.stopped


def test_run_with_tray_shows_countdown_and_closes(tray):
    trays = []

    def factory(on_stop):
        trays.append(tray.Tray(on_stop))
        return trays[-1]

    def timer(on_tick, sleep):
        on_tick("Rest", 1, 1, 65)
        sleep(0.05)  # long enough for the main loop to draw this tick

    tray.run_with_tray(timer, tray_factory=factory, refresh=0.001)
    assert trays[0].icon.title == "🍅 Rest 01:05\nCycle 1/1 - Rest"
    assert trays[0].icon.stopped
