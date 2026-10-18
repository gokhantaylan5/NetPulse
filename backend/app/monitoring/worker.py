
import logging
import signal

from threading import Event

from app.database import DB_PATH, init_db, add_measurement
from app.monitoring.scheduler import MonitoringScheduler
from app.monitoring.ping import PingResult


logger = logging.getLogger(__name__)

MONITOR_INTERVAL = 10.0


def run_worker(stop_event: Event) -> None:
    """
    Initialize the database and run the monitoring
    scheduler until a stop signal is received.
    """

    init_db(DB_PATH)

    scheduler = MonitoringScheduler(
        interval_seconds=MONITOR_INTERVAL,
        measurement_writer=add_measurement
    )

    def on_results(results: list[PingResult]) -> None:
        online_count = sum(
            result.reachable for result in results
        )

        logger.info(
            "Monitoring cycle completed: "
            "%d checked, %d reachable",
            len(results),
            online_count
        )

    logger.info("Monitoring worker started.")

    scheduler.run(
        stop_event=stop_event,
        on_results=on_results
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    stop_event = Event()

    def handle_shutdown(signum, frame):
        logger.info("Shutdown requested.")
        stop_event.set()

    previous_handler = signal.signal(
        signal.SIGINT,
        handle_shutdown
    )

    try:
        run_worker(stop_event)

    finally:
        stop_event.set()

        signal.signal(
            signal.SIGINT,
            previous_handler
        )

        logger.info("Monitoring worker stopped.")


if __name__ == "__main__":
    main()
