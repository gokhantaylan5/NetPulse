
from threading import Event
from unittest.mock import patch

from app.database import DB_PATH, add_measurement
from app.monitoring import worker


def test_worker_initializes_and_starts_scheduler():
    stop_event = Event()

    with (
        patch(
            "app.monitoring.worker.init_db"
        ) as mock_init,
        patch(
            "app.monitoring.worker.MonitoringScheduler"
        ) as mock_scheduler
    ):
        worker.run_worker(stop_event)

    mock_init.assert_called_once_with(DB_PATH)

    mock_scheduler.assert_called_once_with(
        interval_seconds=10.0,
        measurement_writer=add_measurement
    )

    call_args = mock_scheduler.return_value.run.call_args

    assert call_args.kwargs["stop_event"] is stop_event
    assert callable(call_args.kwargs["on_results"])


def test_worker_shutdown_signal():
    with (
        patch(
            "app.monitoring.worker.signal.signal"
        ) as mock_signal,
        patch(
            "app.monitoring.worker.run_worker"
        ) as mock_run_worker
    ):
        def simulate_worker(stop_event):
            shutdown_handler = mock_signal.call_args_list[0].args[1]

            shutdown_handler(signal_number, None)

            assert stop_event.is_set()

        signal_number = worker.signal.SIGINT

        mock_run_worker.side_effect = simulate_worker

        worker.main()

    assert mock_signal.call_count == 2
    assert mock_run_worker.call_count == 1
