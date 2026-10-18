
from collections.abc import Callable
from threading import Event

from app.database import get_targets
from app.monitoring.ping import PingResult, measure_ping


class MonitoringScheduler:
    def __init__(
        self,
        interval_seconds: float = 10.0,
        target_provider: Callable = get_targets,
        ping_fn: Callable[[str], PingResult] = measure_ping,
        measurement_writer: Callable[
            [int, bool, float | None], int
        ] | None = None
    ):
        if interval_seconds <= 0:
            raise ValueError("Interval must be positive.")

        self.interval_seconds = interval_seconds
        self.target_provider = target_provider
        self.ping_fn = ping_fn
        self.measurement_writer = measurement_writer

    def run_once(self) -> list[PingResult]:
        targets = self.target_provider()
        results = []

        for target in targets:
            result = self.ping_fn(target["address"])
            results.append(result)

            if self.measurement_writer is not None:
                self.measurement_writer(
                    target["id"],
                    result.reachable,
                    result.latency_ms
                )

        return results

    def run(
        self,
        stop_event: Event,
        on_results: Callable[[list[PingResult]], None]
    ) -> None:
        while not stop_event.is_set():
            results = self.run_once()
            on_results(results)

            stop_event.wait(self.interval_seconds)
