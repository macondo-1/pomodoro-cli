"""A simple Pomodoro timer for the command line."""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
from xml.sax.saxutils import escape

DEFAULT_WORKING_TIME = 25
DEFAULT_REST_TIME = 5
DEFAULT_CYCLES = 1
DEFAULT_LONG_REST_EVERY = 4


def _applescript_string(text):
    """Quote text as an AppleScript string literal."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


# Windows PowerShell 5.1 (always installed) can load the WinRT toast API;
# PowerShell 7 can't. Toasts need an app ID, so they appear as coming from
# Windows PowerShell.
WINDOWS_TOAST_SCRIPT = """
$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($env:POMODORO_TOAST_XML)
$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show(
    [Windows.UI.Notifications.ToastNotification]::new($xml))
"""

# Windows has no named sounds like macOS, so map each one to a toast sound.
WINDOWS_SOUNDS = {
    "Glass": "ms-winsoundevent:Notification.Default",
    "Ping": "ms-winsoundevent:Notification.IM",
    "Hero": "ms-winsoundevent:Notification.Reminder",
}


def _windows_toast_xml(title, message, sound):
    """Build the XML for a Windows toast notification."""
    audio = WINDOWS_SOUNDS.get(sound, WINDOWS_SOUNDS["Glass"])
    return (
        "<toast><visual><binding template=\"ToastGeneric\">"
        f"<text>{escape(title)}</text><text>{escape(message)}</text>"
        f"</binding></visual><audio src=\"{audio}\"/></toast>"
    )


def notify(title, message, sound="Glass"):
    """Send a desktop notification. Falls back to the terminal bell."""
    system = platform.system()
    try:
        if system == "Darwin":
            script = (
                f"display notification {_applescript_string(message)} "
                f"with title {_applescript_string(title)} "
                f"sound name {_applescript_string(sound)}"
            )
            subprocess.run(["osascript", "-e", script], check=True)
            return
        if system == "Windows":
            # The XML goes in an environment variable to avoid quoting it.
            env = {**os.environ,
                   "POMODORO_TOAST_XML": _windows_toast_xml(title, message,
                                                            sound)}
            subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive",
                            "-Command", WINDOWS_TOAST_SCRIPT],
                           check=True, env=env, capture_output=True)
            return
        if system == "Linux" and shutil.which("notify-send"):
            subprocess.run(["notify-send", title, message], check=True)
            return
    except (OSError, subprocess.CalledProcessError):
        pass
    print(f"\a[{title}] {message}")


def format_time(seconds):
    """Format seconds as MM:SS."""
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def countdown(minutes, label, sleep=time.sleep, out=sys.stdout, on_tick=None):
    """Count down the given number of minutes, one second at a time.

    If given, on_tick(remaining_seconds) is called once per second.
    """
    remaining = int(round(minutes * 60))
    while remaining > 0:
        out.write(f"\r{label}: {format_time(remaining)} ")
        out.flush()
        if on_tick:
            on_tick(remaining)
        sleep(1)
        remaining -= 1
    out.write(f"\r{label}: {format_time(0)} \n")
    out.flush()


def run(working_time=DEFAULT_WORKING_TIME, rest_time=DEFAULT_REST_TIME,
        cycles=DEFAULT_CYCLES, long_rest_time=None,
        long_rest_every=DEFAULT_LONG_REST_EVERY, notifier=notify,
        sleep=time.sleep, out=sys.stdout, on_tick=None):
    """Run the given number of work/rest cycles, notifying at each transition.

    If long_rest_time is given, every long_rest_every-th cycle ends with a
    long rest of that many minutes instead of the normal rest.

    If given, on_tick(phase, cycle, cycles, remaining_seconds) is called once
    per second, where phase is "Work", "Rest" or "Long rest".
    """
    def ticker(phase, cycle):
        if on_tick:
            return lambda remaining: on_tick(phase, cycle, cycles, remaining)
        return None

    for cycle in range(1, cycles + 1):
        prefix = f"Cycle {cycle}/{cycles}"
        long_rest = (long_rest_time is not None
                     and cycle % long_rest_every == 0)
        if long_rest:
            phase, minutes, kind = "Long rest", long_rest_time, "long break"
        else:
            phase, minutes, kind = "Rest", rest_time, "break"

        countdown(working_time, f"{prefix} - Work", sleep=sleep, out=out,
                  on_tick=ticker("Work", cycle))
        notifier("Work period ended",
                 f"{prefix}: time for a {format_minutes(minutes)} {kind}.",
                 sound="Glass")

        countdown(minutes, f"{prefix} - {phase}", sleep=sleep, out=out,
                  on_tick=ticker(phase, cycle))
        if cycle < cycles:
            notifier("Long rest ended" if long_rest else "Rest period ended",
                     f"{prefix}: back to work!",
                     sound="Ping")

    notifier("Pomodoro complete",
             f"All {cycles} cycle{'s' if cycles != 1 else ''} finished. Great job!",
             sound="Hero")


def format_minutes(minutes):
    """Format a minute count for display, e.g. 5 -> '5 min', 0.5 -> '0.5 min'."""
    return f"{minutes:g} min"


def positive_float(value):
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number")
    if number <= 0:
        raise argparse.ArgumentTypeError(f"{value!r} must be greater than 0")
    return number


def positive_int(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer")
    if number <= 0:
        raise argparse.ArgumentTypeError(f"{value!r} must be greater than 0")
    return number


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="pomodoro", description="A simple Pomodoro timer.")
    parser.add_argument("-w", "--working-time", type=positive_float,
                        default=DEFAULT_WORKING_TIME,
                        help="working period in minutes (default: %(default)s)")
    parser.add_argument("-r", "--rest-time", type=positive_float,
                        default=DEFAULT_REST_TIME,
                        help="rest period in minutes (default: %(default)s)")
    parser.add_argument("-c", "--cycles", type=positive_int,
                        default=DEFAULT_CYCLES,
                        help="number of work/rest cycles (default: %(default)s)")
    parser.add_argument("-l", "--long-rest", type=positive_float,
                        dest="long_rest_time", metavar="LONG_REST_TIME",
                        help="take a long rest of this many minutes every "
                             "few cycles (default: no long rests)")
    parser.add_argument("-e", "--long-rest-every", type=positive_int,
                        default=None, metavar="N",
                        help="take the long rest after every N cycles "
                             f"(default: {DEFAULT_LONG_REST_EVERY})")
    parser.add_argument("--no-menubar", "--no-tray", dest="indicator",
                        action="store_false",
                        help="don't show the countdown in the macOS menu bar "
                             "or Windows system tray")
    args = parser.parse_args(argv)
    if args.long_rest_every is None:
        args.long_rest_every = DEFAULT_LONG_REST_EVERY
    elif args.long_rest_time is None:
        parser.error("--long-rest-every needs --long-rest to set its length")
    return args


def load_indicator():
    """Return a run_with_*(timer) function for this platform's menu bar or
    system tray, or None if there isn't one here."""
    try:
        if sys.platform == "darwin":
            from pomodoro.menubar import run_with_menubar
            return run_with_menubar
        if sys.platform == "win32":
            from pomodoro.tray import run_with_tray
            return run_with_tray
    except ImportError as exc:
        print(f"Countdown indicator unavailable ({exc.name} is not installed).",
              file=sys.stderr)
    return None


def main(argv=None):
    args = parse_args(argv)
    settings = dict(working_time=args.working_time, rest_time=args.rest_time,
                    cycles=args.cycles, long_rest_time=args.long_rest_time,
                    long_rest_every=args.long_rest_every)
    show_indicator = load_indicator() if args.indicator else None
    try:
        if show_indicator:
            show_indicator(lambda **kwargs: run(**settings, **kwargs))
        else:
            run(**settings)
    except KeyboardInterrupt:
        print("\nPomodoro stopped.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
