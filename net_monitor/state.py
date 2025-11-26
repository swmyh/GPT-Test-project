import json
import logging
import os
import platform
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional


logger = logging.getLogger(__name__)


@dataclass
class Thresholds:
    max_latency_ms: float = 200.0
    max_packet_loss: float = 10.0
    min_download_mbps: float = 20.0
    min_upload_mbps: float = 5.0


@dataclass
class PingStats:
    min_ms: Optional[float] = None
    avg_ms: Optional[float] = None
    max_ms: Optional[float] = None
    packet_loss: Optional[float] = None
    raw_output: str = ""

    def is_healthy(self, thresholds: Thresholds) -> bool:
        if self.packet_loss is not None and self.packet_loss > thresholds.max_packet_loss:
            return False
        if self.avg_ms is not None and self.avg_ms > thresholds.max_latency_ms:
            return False
        return True


@dataclass
class SpeedStats:
    download_mbps: Optional[float] = None
    upload_mbps: Optional[float] = None
    latency_ms: Optional[float] = None
    note: str = ""

    def is_healthy(self, thresholds: Thresholds) -> bool:
        if self.download_mbps is not None and self.download_mbps < thresholds.min_download_mbps:
            return False
        if self.upload_mbps is not None and self.upload_mbps < thresholds.min_upload_mbps:
            return False
        return True


@dataclass
class NetworkSnapshot:
    timestamp: str
    target: str
    ping: PingStats
    speed: Optional[SpeedStats] = None
    thresholds: Thresholds = field(default_factory=Thresholds)

    def status(self) -> str:
        ping_ok = self.ping.is_healthy(self.thresholds)
        speed_ok = True if self.speed is None else self.speed.is_healthy(self.thresholds)
        if ping_ok and speed_ok:
            return "healthy"
        if not ping_ok and not speed_ok:
            return "degraded"
        return "warning"


@dataclass
class MonitorConfig:
    target: str = "8.8.8.8"
    count: int = 4
    timeout: int = 2
    interval: float = 30.0
    thresholds: Thresholds = field(default_factory=Thresholds)
    history_path: Path = Path(".net_monitor_history.json")
    csv_export_path: Path = Path("net_history.csv")
    enable_speed_test: bool = False
    notify: bool = False


class HistoryStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, snapshot: NetworkSnapshot) -> None:
        history = self.load()
        history.append(asdict(snapshot))
        with self.path.open("w", encoding="utf-8") as fp:
            json.dump(history, fp, ensure_ascii=False, indent=2)
        logger.debug("Snapshot appended: %s", snapshot)

    def load(self) -> List[dict]:
        if not self.path.exists():
            return []
        try:
            with self.path.open("r", encoding="utf-8") as fp:
                return json.load(fp)
        except json.JSONDecodeError as exc:
            logger.warning("Failed to read history file %s: %s", self.path, exc)
            backup_path = self.path.with_suffix(".bak")
            os.replace(self.path, backup_path)
            logger.warning("Corrupt history backed up to %s", backup_path)
            return []

    def export_csv(self, destination: Path) -> None:
        history = self.load()
        if not history:
            raise ValueError("No history to export")
        headers = [
            "timestamp",
            "target",
            "status",
            "ping_min_ms",
            "ping_avg_ms",
            "ping_max_ms",
            "packet_loss",
            "download_mbps",
            "upload_mbps",
            "speed_latency_ms",
        ]
        lines = [",".join(headers)]
        for entry in history:
            ping = entry.get("ping", {})
            speed = entry.get("speed") or {}
            snapshot = NetworkSnapshot(
                timestamp=entry.get("timestamp", ""),
                target=entry.get("target", ""),
                ping=PingStats(**ping),
                speed=SpeedStats(**speed) if speed else None,
            )
            values = [
                snapshot.timestamp,
                snapshot.target,
                snapshot.status(),
                str(ping.get("min_ms", "")),
                str(ping.get("avg_ms", "")),
                str(ping.get("max_ms", "")),
                str(ping.get("packet_loss", "")),
                str(speed.get("download_mbps", "")),
                str(speed.get("upload_mbps", "")),
                str(speed.get("latency_ms", "")),
            ]
            lines.append(",".join(values))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("\n".join(lines), encoding="utf-8")
        logger.info("History exported to %s", destination)


def current_timestamp() -> str:
    return datetime.utcnow().isoformat()


def notify_message(title: str, message: str, enabled: bool) -> None:
    if not enabled:
        return
    platform_name = os.environ.get("OS") or platform.system()
    try:
        if platform_name.lower().startswith("darwin"):
            os.system(f"osascript -e 'display notification \"{message}\" with title \"{title}\"'")
        elif platform_name.lower().startswith("windows"):
            # Windows 10+ toast notifications via PowerShell
            os.system(
                "powershell -command \"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; "
                "$template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02; "
                "$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template); "
                "$textNodes = $xml.GetElementsByTagName('text'); "
                "$textNodes[0].AppendChild($xml.CreateTextNode('" + title + "')) > $null; "
                "$textNodes[1].AppendChild($xml.CreateTextNode('" + message + "')) > $null; "
                "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml); "
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('NetMonitor').Show($toast);\""
            )
        else:
            logger.info("Notification: %s - %s", title, message)
    except Exception as exc:  # pragma: no cover - OS specific
        logger.debug("Notification failed: %s", exc)
