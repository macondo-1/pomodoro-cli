import io
import subprocess

import pytest

from pomodoro import cli


class FakeClock:
    """Stands in for time.sleep and records how long we 'slept'."""

    def __init__(self):
        self.elapsed = 0

    def __call__(self, seconds):
        self.elapsed += seconds


class RecordingNotifier:
    def __init__(self, clock=None):
        self.calls = []
        self.clock = clock

    def __call__(self, title, message, sound=None):
        at = self.clock.elapsed if self.clock else None
        self.calls.append({"title": title, "message": message,
                           "sound": sound, "at": at})

    @property
    def titles(self):
        return [call["title"] for call in self.calls]


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def notifier(clock):
    return RecordingNotifier(clock)


def run(notifier, clock, **kwargs):
    cli.run(notifier=notifier, sleep=clock, out=io.StringIO(), **kwargs)


# --- argument parsing -------------------------------------------------------

def test_defaults():
    args = cli.parse_args([])
    assert args.working_time == 25
    assert args.rest_time == 5
    assert args.cycles == 1


def test_custom_values_long_flags():
    args = cli.parse_args(["--working-time", "50", "--rest-time", "10",
                           "--cycles", "4"])
    assert (args.working_time, args.rest_time, args.cycles) == (50, 10, 4)


def test_custom_values_short_flags():
    args = cli.parse_args(["-w", "1.5", "-r", "0.5", "-c", "2"])
    assert (args.working_time, args.rest_time, args.cycles) == (1.5, 0.5, 2)


@pytest.mark.parametrize("argv", [
    ["-w", "0"], ["-w", "-5"], ["-w", "abc"],
    ["-r", "0"], ["-r", "-1"], ["-r", "x"],
    ["-c", "0"], ["-c", "-2"], ["-c", "1.5"], ["-c", "two"],
])
def test_invalid_values_rejected(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.parse_args(argv)
    assert exc.value.code == 2
    assert "error" in capsys.readouterr().err


# --- timer behaviour --------------------------------------------------------

def test_default_run_lasts_30_minutes(notifier, clock):
    run(notifier, clock)
    assert clock.elapsed == 30 * 60


def test_single_cycle_notifications(notifier, clock):
    run(notifier, clock, working_time=25, rest_time=5, cycles=1)
    assert notifier.titles == ["Work period ended", "Pomodoro complete"]
    assert notifier.calls[0]["at"] == 25 * 60
    assert notifier.calls[1]["at"] == 30 * 60


def test_multiple_cycles_notification_order(notifier, clock):
    run(notifier, clock, working_time=2, rest_time=1, cycles=3)
    assert notifier.titles == [
        "Work period ended", "Rest period ended",
        "Work period ended", "Rest period ended",
        "Work period ended",
        "Pomodoro complete",
    ]
    assert [c["at"] for c in notifier.calls] == [
        120, 180, 300, 360, 480, 540,
    ]


def test_total_duration_with_custom_times(notifier, clock):
    run(notifier, clock, working_time=10, rest_time=3, cycles=4)
    assert clock.elapsed == (10 + 3) * 4 * 60


def test_fractional_minutes(notifier, clock):
    run(notifier, clock, working_time=0.5, rest_time=0.25, cycles=1)
    assert clock.elapsed == 45


def test_completion_notification_is_distinct(notifier, clock):
    run(notifier, clock, working_time=1, rest_time=1, cycles=2)
    final = notifier.calls[-1]
    others = notifier.calls[:-1]
    assert final["title"] == "Pomodoro complete"
    assert "2 cycles" in final["message"]
    assert all(c["title"] != final["title"] for c in others)
    assert all(c["sound"] != final["sound"] for c in others)


def test_completion_message_singular_cycle(notifier, clock):
    run(notifier, clock, working_time=1, rest_time=1, cycles=1)
    assert "1 cycle finished" in notifier.calls[-1]["message"]


def test_work_and_rest_notifications_differ(notifier, clock):
    run(notifier, clock, working_time=1, rest_time=1, cycles=2)
    work, rest = notifier.calls[0], notifier.calls[1]
    assert work["title"] != rest["title"]
    assert work["sound"] != rest["sound"]
    assert "1 min break" in work["message"]
    assert "back to work" in rest["message"]


def test_countdown_output(clock):
    out = io.StringIO()
    cli.countdown(0.05, "Work", sleep=clock, out=out)  # 3 seconds
    text = out.getvalue()
    assert "Work: 00:03" in text
    assert "Work: 00:01" in text
    assert text.endswith("Work: 00:00 \n")
    assert clock.elapsed == 3


@pytest.mark.parametrize("seconds,expected", [
    (0, "00:00"), (59, "00:59"), (60, "01:00"), (1500, "25:00"),
    (3725, "62:05"),
])
def test_format_time(seconds, expected):
    assert cli.format_time(seconds) == expected


def test_on_tick_reports_phase_cycle_and_remaining(notifier, clock):
    ticks = []
    run(notifier, clock, working_time=2 / 60, rest_time=1 / 60, cycles=2,
        on_tick=lambda *args: ticks.append(args))
    assert ticks == [
        ("Work", 1, 2, 2), ("Work", 1, 2, 1), ("Rest", 1, 2, 1),
        ("Work", 2, 2, 2), ("Work", 2, 2, 1), ("Rest", 2, 2, 1),
    ]


# --- notifications ----------------------------------------------------------

def test_notify_macos_uses_osascript(monkeypatch):
    calls = []
    monkeypatch.setattr(cli.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(cli.subprocess, "run",
                        lambda cmd, check: calls.append(cmd))
    cli.notify("Title", 'Say "hi"', sound="Ping")
    assert len(calls) == 1
    cmd = calls[0]
    assert cmd[:2] == ["osascript", "-e"]
    assert 'display notification "Say \\"hi\\""' in cmd[2]
    assert 'with title "Title"' in cmd[2]
    assert 'sound name "Ping"' in cmd[2]


def test_notify_linux_uses_notify_send(monkeypatch):
    calls = []
    monkeypatch.setattr(cli.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(cli.subprocess, "run",
                        lambda cmd, check: calls.append(cmd))
    cli.notify("Title", "Message")
    assert calls == [["notify-send", "Title", "Message"]]


def test_notify_falls_back_to_terminal(monkeypatch, capsys):
    monkeypatch.setattr(cli.platform, "system", lambda: "Windows")
    cli.notify("Title", "Message")
    assert "[Title] Message" in capsys.readouterr().out


def test_notify_falls_back_when_command_fails(monkeypatch, capsys):
    def failing_run(cmd, check):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(cli.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(cli.subprocess, "run", failing_run)
    cli.notify("Title", "Message")
    assert "[Title] Message" in capsys.readouterr().out


# --- main -------------------------------------------------------------------

@pytest.fixture
def no_menubar(monkeypatch):
    """Keep main() from drawing a real menu bar item during tests."""
    monkeypatch.setattr(cli, "load_menubar", lambda: None)


def test_main_passes_arguments_to_run(monkeypatch, no_menubar):
    received = {}
    monkeypatch.setattr(cli, "run",
                        lambda w, r, c: received.update(w=w, r=r, c=c))
    assert cli.main(["-w", "50", "-r", "10", "-c", "3"]) == 0
    assert received == {"w": 50, "r": 10, "c": 3}


def test_main_handles_ctrl_c(monkeypatch, capsys, no_menubar):
    def interrupted(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "run", interrupted)
    assert cli.main([]) == 130
    assert "stopped" in capsys.readouterr().out


def test_main_uses_menubar_when_available(monkeypatch):
    calls = []

    class FakeMenubarModule:
        @staticmethod
        def run_with_menubar(timer):
            timer(on_tick="tick", sleep="sleep")

    monkeypatch.setattr(cli, "load_menubar", lambda: FakeMenubarModule)
    monkeypatch.setattr(cli, "run", lambda *args, **kwargs:
                        calls.append((args, kwargs)))
    assert cli.main(["-w", "50", "-r", "10", "-c", "3"]) == 0
    assert calls == [((50, 10, 3), {"on_tick": "tick", "sleep": "sleep"})]


def test_main_no_menubar_flag_skips_menubar(monkeypatch):
    def fail():
        raise AssertionError("menu bar should not be loaded")

    monkeypatch.setattr(cli, "load_menubar", fail)
    monkeypatch.setattr(cli, "run", lambda *args: None)
    assert cli.main(["--no-menubar"]) == 0


def test_menubar_enabled_by_default():
    assert cli.parse_args([]).menubar is True
    assert cli.parse_args(["--no-menubar"]).menubar is False


def test_load_menubar_skipped_off_macos(monkeypatch):
    monkeypatch.setattr(cli.sys, "platform", "linux")
    assert cli.load_menubar() is None
