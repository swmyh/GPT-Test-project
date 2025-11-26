import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional

from .ping_monitor import PingMonitor
from .speed_test import SpeedTestRunner
from .state import (
    HistoryStore,
    MonitorConfig,
    NetworkSnapshot,
    PingStats,
    SpeedStats,
    Thresholds,
    current_timestamp,
    notify_message,
)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    console: Optional[Console] = Console()
except Exception:  # pragma: no cover - optional dependency
    console = None

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def render_status(snapshot: NetworkSnapshot) -> str:
    if console:
        status_text = Text(snapshot.status())
        color = "green" if snapshot.status() == "healthy" else "yellow" if snapshot.status() == "warning" else "red"
        status_text.stylize(color)
        return status_text
    return snapshot.status()


def print_snapshot(snapshot: NetworkSnapshot) -> None:
    status_value = render_status(snapshot)
    if console:
        table = Table(title=f"Network status for {snapshot.target}")
        table.add_column("Timestamp", style="cyan")
        table.add_column("Status")
        table.add_column("Latency (ms)")
        table.add_column("Loss (%)")
        table.add_column("Download / Upload (Mbps)")
        table.add_row(
            snapshot.timestamp,
            status_value,
            f"min {snapshot.ping.min_ms} / avg {snapshot.ping.avg_ms} / max {snapshot.ping.max_ms}",
            str(snapshot.ping.packet_loss),
            f"{snapshot.speed.download_mbps if snapshot.speed else '-'} / {snapshot.speed.upload_mbps if snapshot.speed else '-'}",
        )
        console.print(table)
    else:
        print(f"[{snapshot.timestamp}] {snapshot.target} -> {snapshot.status()}")
        print(f"  latency: min {snapshot.ping.min_ms} avg {snapshot.ping.avg_ms} max {snapshot.ping.max_ms}")
        print(f"  packet loss: {snapshot.ping.packet_loss}%")
        if snapshot.speed:
            print(
                f"  speed: download {snapshot.speed.download_mbps} Mbps / upload {snapshot.speed.upload_mbps} Mbps (latency {snapshot.speed.latency_ms} ms)"
            )
        if snapshot.speed and snapshot.speed.note:
            print(f"  note: {snapshot.speed.note}")


def run_sample(config: MonitorConfig) -> NetworkSnapshot:
    ping_monitor = PingMonitor()
    speed_runner = SpeedTestRunner()

    ping_stats = ping_monitor.run(config.target, config.count, config.timeout)
    speed_stats: Optional[SpeedStats] = None
    if config.enable_speed_test:
        speed_stats = speed_runner.run()
    snapshot = NetworkSnapshot(
        timestamp=current_timestamp(),
        target=config.target,
        ping=ping_stats,
        speed=speed_stats,
        thresholds=config.thresholds,
    )
    return snapshot


def monitor_command(args: argparse.Namespace) -> None:
    config = MonitorConfig(
        target=args.target,
        count=args.count,
        timeout=args.timeout,
        interval=args.interval,
        thresholds=Thresholds(
            max_latency_ms=args.max_latency,
            max_packet_loss=args.max_loss,
            min_download_mbps=args.min_download,
            min_upload_mbps=args.min_upload,
        ),
        history_path=Path(args.history),
        csv_export_path=Path(args.csv),
        enable_speed_test=args.speed,
        notify=args.notify,
    )
    history = HistoryStore(config.history_path)
    try:
        while True:
            snapshot = run_sample(config)
            history.append(snapshot)
            print_snapshot(snapshot)
            if snapshot.status() != "healthy":
                notify_message("Network Monitor", f"Status {snapshot.status()} for {snapshot.target}", config.notify)
            time.sleep(config.interval)
    except KeyboardInterrupt:
        logger.info("Monitoring stopped")


def status_command(args: argparse.Namespace) -> None:
    config = MonitorConfig(
        target=args.target,
        count=args.count,
        timeout=args.timeout,
        thresholds=Thresholds(
            max_latency_ms=args.max_latency,
            max_packet_loss=args.max_loss,
            min_download_mbps=args.min_download,
            min_upload_mbps=args.min_upload,
        ),
        enable_speed_test=args.speed,
    )
    snapshot = run_sample(config)
    print_snapshot(snapshot)


def history_command(args: argparse.Namespace) -> None:
    history = HistoryStore(Path(args.history))
    records = history.load()
    if not records:
        print("No history yet. Run monitor to start collecting data.")
        return
    if console:
        table = Table(title="Recent network history")
        table.add_column("Timestamp")
        table.add_column("Target")
        table.add_column("Status")
        table.add_column("Avg Latency")
        table.add_column("Loss %")
        for entry in records[-args.limit :]:
            snapshot = NetworkSnapshot(
                timestamp=entry.get("timestamp", ""),
                target=entry.get("target", ""),
                ping=PingStats(**entry.get("ping", {})),
                speed=SpeedStats(**entry.get("speed") or {}) if entry.get("speed") else None,
            )
            table.add_row(
                snapshot.timestamp,
                snapshot.target,
                render_status(snapshot),
                str(snapshot.ping.avg_ms),
                str(snapshot.ping.packet_loss),
            )
        console.print(table)
    else:
        for entry in records[-args.limit :]:
            snapshot = NetworkSnapshot(
                timestamp=entry.get("timestamp", ""),
                target=entry.get("target", ""),
                ping=PingStats(**entry.get("ping", {})),
                speed=SpeedStats(**entry.get("speed") or {}) if entry.get("speed") else None,
            )
            print(f"[{snapshot.timestamp}] {snapshot.target} {snapshot.status()} avg {snapshot.ping.avg_ms}ms loss {snapshot.ping.packet_loss}%")


def export_command(args: argparse.Namespace) -> None:
    history = HistoryStore(Path(args.history))
    try:
        history.export_csv(Path(args.destination))
        print(f"Exported history to {args.destination}")
    except ValueError as exc:
        print(str(exc))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform network monitor")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command")

    monitor_parser = subparsers.add_parser("monitor", help="Start monitoring loop")
    monitor_parser.add_argument("--target", default="8.8.8.8", help="Ping target host")
    monitor_parser.add_argument("--count", type=int, default=4, help="Ping count per sample")
    monitor_parser.add_argument("--timeout", type=int, default=2, help="Ping timeout seconds")
    monitor_parser.add_argument("--interval", type=float, default=30.0, help="Sampling interval in seconds")
    monitor_parser.add_argument("--max-latency", type=float, default=200.0, help="Latency threshold in ms")
    monitor_parser.add_argument("--max-loss", type=float, default=10.0, help="Packet loss threshold in percent")
    monitor_parser.add_argument("--min-download", type=float, default=20.0, help="Minimum download Mbps")
    monitor_parser.add_argument("--min-upload", type=float, default=5.0, help="Minimum upload Mbps")
    monitor_parser.add_argument("--history", default=".net_monitor_history.json", help="History JSON path")
    monitor_parser.add_argument("--csv", default="net_history.csv", help="CSV export path")
    monitor_parser.add_argument("--speed", action="store_true", help="Run speed tests alongside ping")
    monitor_parser.add_argument("--notify", action="store_true", help="Enable desktop notification on issues")
    monitor_parser.set_defaults(func=monitor_command)

    status_parser = subparsers.add_parser("status", help="Run a single status check")
    status_parser.add_argument("--target", default="8.8.8.8", help="Ping target host")
    status_parser.add_argument("--count", type=int, default=4, help="Ping count")
    status_parser.add_argument("--timeout", type=int, default=2, help="Ping timeout seconds")
    status_parser.add_argument("--max-latency", type=float, default=200.0, help="Latency threshold in ms")
    status_parser.add_argument("--max-loss", type=float, default=10.0, help="Packet loss threshold in percent")
    status_parser.add_argument("--min-download", type=float, default=20.0, help="Minimum download Mbps")
    status_parser.add_argument("--min-upload", type=float, default=5.0, help="Minimum upload Mbps")
    status_parser.add_argument("--speed", action="store_true", help="Run speed tests")
    status_parser.set_defaults(func=status_command)

    history_parser = subparsers.add_parser("history", help="Show recent samples")
    history_parser.add_argument("--history", default=".net_monitor_history.json", help="History JSON path")
    history_parser.add_argument("--limit", type=int, default=10, help="Rows to display")
    history_parser.set_defaults(func=history_command)

    export_parser = subparsers.add_parser("export", help="Export history to CSV")
    export_parser.add_argument("--history", default=".net_monitor_history.json", help="History JSON path")
    export_parser.add_argument("destination", default="net_history.csv", help="CSV destination")
    export_parser.set_defaults(func=export_command)

    return parser


def main(argv: Optional[list] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
