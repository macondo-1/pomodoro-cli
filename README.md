# pomodoro-cli

A simple Pomodoro timer for the command line. It counts down work and rest
periods in your terminal and sends a desktop notification at each transition.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

There are no runtime dependencies.

## Installation

Install `pomodoro` as a command you can run from any folder:

```sh
uv tool install --editable .
```

uv places the command in `~/.local/bin`. If your shell can't find it, run
`uv tool update-shell` and open a new terminal.

Because the install is editable, code changes take effect immediately. After
changing `pyproject.toml` (e.g. adding a dependency), reinstall:

```sh
uv tool install --editable . --reinstall
```

To uninstall:

```sh
uv tool uninstall pomodoro-cli
```

You can also run it from the project folder without installing it:

```sh
uv run pomodoro
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

Times must be greater than 0; cycles must be a whole number greater than 0.
Press `Ctrl+C` to stop the timer.

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
- **Linux**: via `notify-send` (from `libnotify`).
- **Elsewhere**, or if the above fails: a message is printed in the terminal
  with a bell.

## Development

```sh
uv sync            # create .venv and install dev dependencies
uv run pytest      # run the test suite
```

The tests use a fake clock and a fake notifier, so they run instantly and
don't send real notifications.

## Project layout

```
src/pomodoro/cli.py       timer, notifications and argument parsing
src/pomodoro/__main__.py  enables `python -m pomodoro`
tests/test_cli.py         pytest suite
pyproject.toml            project metadata and the `pomodoro` entry point
```

## License

[MIT](LICENSE)
