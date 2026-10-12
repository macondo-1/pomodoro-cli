"""A simple Pomodoro timer for the command line."""

import argparse
import platform
import shutil
import subprocess
import sys
import time

DEFAULT_WORKING_TIME = 25
DEFAULT_REST_TIME = 5
DEFAULT_CYCLES = 1


def _applescript_string(text):
    """Quote text as an AppleScript string literal."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


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
        cycles=DEFAULT_CYCLES, notifier=notify, sleep=time.sleep,
        out=sys.stdout, on_tick=None):
    """Run the given number of work/rest cycles, notifying at each transition.

    If given, on_tick(phase, cycle, cycles, remaining_seconds) is called once
    per second, where phase is "Work" or "Rest".
    """
    def ticker(phase, cycle):
        if on_tick:
            return lambda remaining: on_tick(phase, cycle, cycles, remaining)
        return None

    for cycle in range(1, cycles + 1):
        prefix = f"Cycle {cycle}/{cycles}"

        countdown(working_time, f"{prefix} - Work", sleep=sleep, out=out,
                  on_tick=ticker("Work", cycle))
        notifier("Work period ended",
                 f"{prefix}: time for a {format_minutes(rest_time)} break.",
                 sound="Glass")

        countdown(rest_time, f"{prefix} - Rest", sleep=sleep, out=out,
                  on_tick=ticker("Rest", cycle))
        if cycle < cycles:
            notifier("Rest period ended",
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
    parser.add_argument("--no-menubar", dest="menubar", action="store_false",
                        help="don't show the countdown in the macOS menu bar")
    return parser.parse_args(argv)


def load_menubar():
    """Return the menu bar module, or None if it isn't available here."""
    if sys.platform != "darwin":
        return None
    try:
        from pomodoro import menubar
    except ImportError:
        print("Menu bar countdown unavailable (PyObjC is not installed).",
              file=sys.stderr)
        return None
    return menubar


def main(argv=None):
    args = parse_args(argv)
    menubar = load_menubar() if args.menubar else None
    try:
        if menubar:
            menubar.run_with_menubar(
                lambda **kwargs: run(args.working_time, args.rest_time,
                                     args.cycles, **kwargs))
        else:
            run(args.working_time, args.rest_time, args.cycles)
    except KeyboardInterrupt:
        print("\nPomodoro stopped.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
