
import logging

from collections.abc import Callable
from threading import Event

from app.database import get_targets
from app.monitoring.ping import PingResult, measure_ping


logger = logging.getLogger(__name__)


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
            raise ValueError(
                "Interval must be positive."
            )

        self.interval_seconds = interval_seconds
        self.target_provider = target_provider
        self.ping_fn = ping_fn
        self.measurement_writer = measurement_writer

    def run_once(self) -> list[PingResult]:
        """
        Perform one monitoring cycle for all targets.

        A failure affecting one target should not prevent
        the remaining targets from being monitored.
        """

        targets = self.target_provider()
        results: list[PingResult] = []

        for target in targets:
            try:
                host = target["address"]

                result = self.ping_fn(host)

            except Exception:
                logger.exception(
                    "Ping operation failed for target: %s",
                    target
                )
                continue

            results.append(result)

            if self.measurement_writer is None:
                continue

            try:
                self.measurement_writer(
                    target["id"],
                    result.reachable,
                    result.latency_ms
                )

            except Exception:
                logger.exception(
                    "Failed to save measurement for %s",
                    result.host
                )

        return results

    def run(
        self,
        stop_event: Event,
        on_results: Callable[
            [list[PingResult]], None
        ]
    ) -> None:
        """
        Run monitoring cycles periodically until
        the stop event is triggered.
        """

        logger.info(
            "Monitoring scheduler started. Interval: %s seconds",
            self.interval_seconds
        )

        try:
            while not stop_event.is_set():

                try:
                    results = self.run_once()

                except Exception:
                    logger.exception(
                        "Monitoring cycle failed."
                    )

                else:
                    try:
                        on_results(results)

                    except Exception:
                        logger.exception(
                            "Failed to process monitoring results."
                        )

                stop_event.wait(
                    self.interval_seconds
                )

        finally:
            logger.info(
                "Monitoring scheduler stopped."
            )
