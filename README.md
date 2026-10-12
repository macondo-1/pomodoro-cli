# pomodoro-cli

A simple Pomodoro timer for the command line. It counts down work and rest
periods in your terminal, in the macOS menu bar or Windows system tray, and
sends a desktop notification at each transition.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

On macOS, [PyObjC](https://pyobjc.readthedocs.io/) is installed
automatically for the menu bar countdown. On Windows,
[pystray](https://github.com/moses-palmer/pystray) and
[Pillow](https://python-pillow.org/) are installed for the tray icon. There
are no dependencies on other systems.

## Installation

Install `pomodoro` as a command you can run from any folder.

### From GitHub

No need to clone the repo:

```sh
uv tool install git+https://github.com/macondo-1/pomodoro-cli
```

To update to the latest version later:

```sh
uv tool upgrade pomodoro-cli
```

### From a local clone (for development)

```sh
git clone https://github.com/macondo-1/pomodoro-cli.git
cd pomodoro-cli
uv tool install --editable .
```

Because the install is editable, code changes take effect immediately. After
changing `pyproject.toml` (e.g. adding a dependency), reinstall:

```sh
uv tool install --editable . --reinstall
```

You can also run it from the project folder without installing it:

```sh
uv run pomodoro
```

### Finding and removing the command

uv places the command in `~/.local/bin`. If your shell can't find it, run
`uv tool update-shell` and open a new terminal.

To uninstall:

```sh
uv tool uninstall pomodoro-cli
```

## Usage

```sh
pomodoro                     # 25 min work, 5 min rest, 1 cycle
pomodoro -w 50 -r 10         # 50 min work, 10 min rest
pomodoro -c 4                # 4 cycles of 25/5
pomodoro -w 0.5 -r 0.25      # fractional minutes work too (30s / 15s)
```

| Option | Description | Default |
|---|---|---|
| `-w`, `--working-time` | Work period in minutes | `25` |
| `-r`, `--rest-time` | Rest period in minutes | `5` |
| `-c`, `--cycles` | Number of work/rest cycles | `1` |
| `--no-menubar`, `--no-tray` | Don't show the countdown in the macOS menu bar or Windows tray | off |

Times must be greater than 0; cycles must be a whole number greater than 0.
Press `Ctrl+C` to stop the timer.

## Menu bar countdown (macOS)

While the timer runs, the time left is shown in the menu bar, and it stays
visible whatever app you're in:

```
🍅 Work 24:13
```

Click it to see the current cycle (e.g. `Cycle 1/4 - Work`) or to **Stop**
the timer. The item disappears when the timer finishes or is stopped. Use
`--no-menubar` to turn it off.

## Tray countdown (Windows)

While the timer runs, a tomato icon sits in the system tray. Windows tray
icons can't show text, so hover over it to see the time left and the
current cycle:

```
🍅 Work 24:13
Cycle 1/4 - Work
```

Right-click it to **Stop** the timer. The icon disappears when the timer
finishes or is stopped. Use `--no-tray` to turn it off.

## Notifications

Each cycle is a work period followed by a rest period. You get a distinct
notification (title and sound) for each event:

| Event | Title | Sound |
|---|---|---|
| A work period ends | Work period ended | Glass |
| A rest period ends | Rest period ended | Ping |
| All cycles are done | Pomodoro complete | Hero |

After the last cycle's rest period, only "Pomodoro complete" is sent.

How notifications are delivered:

- **macOS**: via `osascript`. If none appear, allow notifications for
  **Script Editor** in System Settings → Notifications.
- **Windows**: as a toast notification via the built-in Windows PowerShell,
  so they're listed as coming from **Windows PowerShell**. If none appear,
  check that notifications are on in Settings → System → Notifications and
  that Do Not Disturb / Focus is off. The sounds are Windows' own: Default,
  Instant Message and Reminder.
- **Linux**: via `notify-send` (from `libnotify`).
- **Elsewhere**, or if the above fails: a message is printed in the terminal
  with a bell.

## Development

```sh
uv sync            # create .venv and install dev dependencies
uv run pytest      # run the test suite
```

The tests use a fake clock, notifier, menu bar and tray icon, so they run
instantly on any platform and don't send real notifications or draw
anything on screen.

## Project layout

```
src/pomodoro/cli.py       timer, notifications and argument parsing
src/pomodoro/indicator.py runs the timer alongside the menu bar or tray icon
src/pomodoro/menubar.py   macOS menu bar countdown
src/pomodoro/tray.py      Windows system tray countdown
src/pomodoro/__main__.py  enables `python -m pomodoro`
tests/                    pytest suite
pyproject.toml            project metadata and the `pomodoro` entry point
```

## License

[MIT](LICENSE)
