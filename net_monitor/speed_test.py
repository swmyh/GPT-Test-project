import logging

from .state import SpeedStats

logger = logging.getLogger(__name__)


class SpeedTestRunner:
    def __init__(self):
        self._speedtest_module = self._load_speedtest()

    @staticmethod
    def _load_speedtest():
        try:
            import speedtest  # type: ignore

            return speedtest
        except Exception:  # pragma: no cover - optional dependency
            return None

    def available(self) -> bool:
        return self._speedtest_module is not None

    def run(self) -> SpeedStats:
        if not self.available():
            note = "speedtest-cli not installed; skipping speed measurement"
            logger.info(note)
            return SpeedStats(note=note)
        try:
            st = self._speedtest_module.Speedtest()
            st.get_best_server()
            download = st.download() / 1_000_000
            upload = st.upload() / 1_000_000
            ping_latency = st.results.ping
            return SpeedStats(
                download_mbps=round(download, 2),
                upload_mbps=round(upload, 2),
                latency_ms=ping_latency,
            )
        except Exception as exc:  # pragma: no cover - network dependency
            logger.warning("Speed test failed: %s", exc)
            return SpeedStats(note=f"speed test failed: {exc}")
