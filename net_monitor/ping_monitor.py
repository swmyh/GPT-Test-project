import logging
import platform
import re
import shutil
import subprocess
from typing import List

from .state import PingStats

logger = logging.getLogger(__name__)


class PingMonitor:
    def __init__(self, command: str = "ping"):
        self.command = command

    def _build_command(self, target: str, count: int, timeout: int) -> List[str]:
        system_name = platform.system().lower()
        if "windows" in system_name:
            return [self.command, "-n", str(count), "-w", str(timeout * 1000), target]
        if shutil.which("ping") is None:
            raise FileNotFoundError("ping command not found")
        if "darwin" in system_name:
            return [self.command, "-c", str(count), "-W", str(timeout), target]
        return [self.command, "-c", str(count), "-W", str(timeout), target]

    def run(self, target: str, count: int = 4, timeout: int = 2) -> PingStats:
        cmd = self._build_command(target, count, timeout)
        logger.debug("Executing ping command: %s", " ".join(cmd))
        try:
            process = subprocess.run(cmd, capture_output=True, check=False, text=True)
        except FileNotFoundError as exc:
            logger.error("ping command not found: %s", exc)
            raise
        output = (process.stdout or "") + (process.stderr or "")
        return self._parse_output(output)

    def _parse_output(self, output: str) -> PingStats:
        packet_loss = self._parse_packet_loss(output)
        min_ms, avg_ms, max_ms = self._parse_latency(output)
        return PingStats(min_ms=min_ms, avg_ms=avg_ms, max_ms=max_ms, packet_loss=packet_loss, raw_output=output)

    @staticmethod
    def _parse_packet_loss(output: str) -> float:
        loss_pattern = re.compile(r"(\d+)%\s+packet\s+loss|Lost = \d+ \((\d+)% loss\)")
        for line in output.splitlines():
            match = loss_pattern.search(line)
            if match:
                number = match.group(1) or match.group(2)
                try:
                    return float(number)
                except ValueError:
                    continue
        return 0.0

    @staticmethod
    def _parse_latency(output: str):
        unix_pattern = re.compile(r"= ([0-9\.]+)/([0-9\.]+)/([0-9\.]+)")
        windows_pattern = re.compile(r"Minimum = ([0-9]+)ms, Maximum = ([0-9]+)ms, Average = ([0-9]+)ms")
        for line in output.splitlines():
            unix_match = unix_pattern.search(line)
            if unix_match:
                min_ms, avg_ms, max_ms = unix_match.groups()
                return float(min_ms), float(avg_ms), float(max_ms)
            windows_match = windows_pattern.search(line)
            if windows_match:
                min_ms, max_ms, avg_ms = windows_match.groups()
                return float(min_ms), float(avg_ms), float(max_ms)
        return None, None, None
