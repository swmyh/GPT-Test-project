# GPT Test Project - Network Monitor

Cross-platform network monitoring utilities with ping statistics, optional speed testing, history persistence, and a simple CLI/TUI.

## Setup

1. Ensure Python 3.9+ is installed.
2. Optional but recommended packages:
   - [`rich`](https://github.com/Textualize/rich) for colorized tables.
   - [`speedtest-cli`](https://www.speedtest.net/apps/cli) for download/upload measurements.
3. Install dependencies:

```bash
pip install -r requirements.txt  # if you maintain one
pip install rich speedtest-cli   # optional extras
```

## OS-specific notes

- **macOS**: `ping` uses `-c` for count and `-W` for timeout (seconds). Desktop notifications use `osascript` and may prompt for permission the first time.
- **Windows**: `ping` uses `-n` for count and `-w` for timeout (milliseconds). Desktop notifications rely on PowerShell and Windows 10+ toast support.
- **Linux**: Uses standard `ping -c/-W`. Desktop notification falls back to log output unless you plug in your own notifier.
- If `speedtest-cli` is missing, the tool gracefully skips speed tests with a log message.

## CLI usage

```bash
python -m net_monitor.cli --help
```

### Quick commands

- Start monitoring loop with history: `python -m net_monitor.cli monitor --target 8.8.8.8 --interval 60 --history ~/.netmon/history.json`
- Single check: `python -m net_monitor.cli status --speed`
- Show recent history: `python -m net_monitor.cli history --limit 5`
- Export history to CSV: `python -m net_monitor.cli export --destination ~/net_history.csv`

### Configurable settings

- Sampling interval, ping count/timeout.
- Latency/packet-loss/download/upload thresholds for warnings.
- History persistence paths (JSON and CSV export).
- Desktop notifications on degraded status (macOS/Windows) and plain log fallback elsewhere.

## Example output (rich TUI)

```
╔════════════════════════════════════════════════════════╗
║                 Network status for 8.8.8.8             ║
╟──────────────────────┬────────┬─────────────┬──────────╢
║ Timestamp            │ Status │ Latency (ms)│ Loss (%) ║
╟──────────────────────┼────────┼─────────────┼──────────╢
║ 2024-05-01T12:00:00Z │ healthy│ min 12 / avg 18 / max 24│ 0.0 ║
║ Download / Upload (Mbps): 90.1 / 12.3                   ║
╚════════════════════════════════════════════════════════╝
```

When `rich` is unavailable, the CLI falls back to plain text output.

## Screenshots

No binary screenshot is bundled in the repository to keep patches lightweight. To capture your own preview:

1. Run `python -m net_monitor.cli status --target 8.8.8.8 --speed`.
2. Take a screenshot of the output in your terminal (or the rich TUI if the dependency is installed).
3. Save the image wherever you prefer (for example `docs/net-monitor-sample.png`) and reference it in your own documentation if needed.

## Logging & history

- Snapshots are appended to the JSON history path (default: `.net_monitor_history.json`).
- Use the `export` command to create CSVs for spreadsheets or BI dashboards.

## Development notes

- Commands live in `net_monitor/cli.py`.
- Ping parsing is implemented in `net_monitor/ping_monitor.py` with macOS/Windows flag handling.
- Speed test wrapping and dependency fallback lives in `net_monitor/speed_test.py`.
- Data structures and persistence reside in `net_monitor/state.py`.
