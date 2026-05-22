import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.queue import RedisStreamsQueue
from app.worker import StreamWorker


@pytest.mark.asyncio
async def test_enqueue_includes_operational_metadata():
    mock_redis = AsyncMock()
    with patch("app.core.queue.get_redis", return_value=mock_redis):
        queue = RedisStreamsQueue("redis://localhost", stream_name="test_stream")
        await queue.enqueue("test_job", {"a": 1})
        args, kwargs = mock_redis.xadd.call_args
        data = args[1]
        body = json.loads(data["payload"])
        assert body["job_name"] == "test_job"
        assert body["payload"] == {"a": 1}
        assert body["meta"]["retry_count"] == 0
        assert "first_seen_at" in body["meta"]
        assert kwargs["maxlen"] == 10000


@pytest.mark.asyncio
async def test_enqueue_dlq_publishes_failure_context():
    mock_redis = AsyncMock()
    with patch("app.core.queue.get_redis", return_value=mock_redis):
        queue = RedisStreamsQueue("redis://localhost")
        await queue.enqueue_dlq(
            job_name="send_contact_email",
            payload={"name": "n"},
            metadata={"retry_count": 3},
            reason="bad payload",
            error_type="ValueError",
        )
        args, _ = mock_redis.xadd.call_args
        assert args[0] == "contact_jobs_dlq"
        body = json.loads(args[1]["payload"])
        assert body["meta"]["last_error"] == "bad payload"
        assert body["meta"]["last_error_type"] == "ValueError"


@pytest.mark.asyncio
async def test_worker_permanent_error_moves_to_dlq_and_acks():
    mock_redis = AsyncMock()
    payload = {
        "job_name": "send_contact_email",
        "payload": {"name": "a", "email": "a@a.com", "message": "m"},
        "meta": {"retry_count": 0},
    }
    mock_redis.xautoclaim.return_value = ["0", []]
    mock_redis.xreadgroup.return_value = [
        (
            "contact_jobs",
            [
                (
                    "job-1",
                    {"job_name": "send_contact_email", "payload": json.dumps(payload)},
                )
            ],
        )
    ]

    worker = StreamWorker("redis://localhost")

    def stop_once(*args, **kwargs):
        worker.running = False
        return mock_redis.xreadgroup.return_value

    mock_redis.xreadgroup.side_effect = stop_once

    uc_mock = AsyncMock()
    uc_mock.execute.side_effect = ValueError("Invalid email format")  # Permanent

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("app.worker.get_send_contact_use_case", return_value=uc_mock),
        patch.object(RedisStreamsQueue, "enqueue_dlq", new=AsyncMock()) as mock_dlq,
    ):
        await worker.run()
        mock_redis.xack.assert_called_once_with(
            "contact_jobs", "email_workers", "job-1"
        )
        mock_dlq.assert_called_once()


@pytest.mark.asyncio
async def test_worker_transient_error_retries_and_re_enqueues():
    mock_redis = AsyncMock()
    payload = {
        "job_name": "send_contact_email",
        "payload": {"name": "a", "email": "a@a.com", "message": "m"},
        "meta": {"retry_count": 0},
    }
    mock_redis.xautoclaim.return_value = ["0", []]
    mock_redis.xreadgroup.return_value = [
        (
            "contact_jobs",
            [
                (
                    "job-1",
                    {"job_name": "send_contact_email", "payload": json.dumps(payload)},
                )
            ],
        )
    ]

    worker = StreamWorker("redis://localhost")

    def stop_once(*args, **kwargs):
        worker.running = False
        return mock_redis.xreadgroup.return_value

    mock_redis.xreadgroup.side_effect = stop_once

    uc_mock = AsyncMock()
    uc_mock.execute.side_effect = TimeoutError("Connection timeout")  # Transient

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("app.worker.get_send_contact_use_case", return_value=uc_mock),
        patch("asyncio.sleep", new=AsyncMock()),
    ):
        await worker.run()
        # Should xack the old one
        mock_redis.xack.assert_called_once_with(
            "contact_jobs", "email_workers", "job-1"
        )
        # Should xadd a new one for retry
        assert mock_redis.xadd.call_count == 1
        args, _ = mock_redis.xadd.call_args
        assert args[0] == "contact_jobs"


@pytest.mark.asyncio
async def test_worker_transient_error_exceeds_retries_and_dlq():
    mock_redis = AsyncMock()
    payload = {
        "job_name": "send_contact_email",
        "payload": {"name": "a", "email": "a@a.com", "message": "m"},
        "meta": {"retry_count": 3},
    }  # Max retries
    mock_redis.xautoclaim.return_value = ["0", []]
    mock_redis.xreadgroup.return_value = [
        (
            "contact_jobs",
            [
                (
                    "job-1",
                    {"job_name": "send_contact_email", "payload": json.dumps(payload)},
                )
            ],
        )
    ]

    worker = StreamWorker("redis://localhost")

    def stop_once(*args, **kwargs):
        worker.running = False
        return mock_redis.xreadgroup.return_value

    mock_redis.xreadgroup.side_effect = stop_once

    uc_mock = AsyncMock()
    uc_mock.execute.side_effect = TimeoutError("Connection timeout")  # Transient

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("app.worker.get_send_contact_use_case", return_value=uc_mock),
        patch.object(RedisStreamsQueue, "enqueue_dlq", new=AsyncMock()) as mock_dlq,
    ):
        await worker.run()
        mock_redis.xack.assert_called_once_with(
            "contact_jobs", "email_workers", "job-1"
        )
        mock_dlq.assert_called_once()


@pytest.mark.asyncio
async def test_worker_unknown_error_1_retry_then_dlq():
    mock_redis = AsyncMock()
    # First attempt (retry=0)
    payload = {
        "job_name": "send_contact_email",
        "payload": {"name": "a", "email": "a@a.com", "message": "m"},
        "meta": {"retry_count": 0},
    }
    mock_redis.xautoclaim.return_value = ["0", []]
    mock_redis.xreadgroup.return_value = [
        (
            "contact_jobs",
            [
                (
                    "job-1",
                    {"job_name": "send_contact_email", "payload": json.dumps(payload)},
                )
            ],
        )
    ]

    worker = StreamWorker("redis://localhost")

    def stop_once(*args, **kwargs):
        worker.running = False
        return mock_redis.xreadgroup.return_value

    mock_redis.xreadgroup.side_effect = stop_once

    uc_mock = AsyncMock()
    uc_mock.execute.side_effect = Exception("Mysterious failure")  # Unknown

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("app.worker.get_send_contact_use_case", return_value=uc_mock),
        patch("asyncio.sleep", new=AsyncMock()),
    ):
        await worker.run()
        # Should xack old and xadd new
        mock_redis.xack.assert_called_once_with(
            "contact_jobs", "email_workers", "job-1"
        )
        assert mock_redis.xadd.call_count == 1

    # Second attempt (retry=1)
    mock_redis.reset_mock()
    payload["meta"]["retry_count"] = 1
    mock_redis.xautoclaim.return_value = ["0", []]
    mock_redis.xreadgroup.return_value = [
        (
            "contact_jobs",
            [
                (
                    "job-2",
                    {"job_name": "send_contact_email", "payload": json.dumps(payload)},
                )
            ],
        )
    ]
    mock_redis.xreadgroup.side_effect = stop_once

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("app.worker.get_send_contact_use_case", return_value=uc_mock),
        patch.object(RedisStreamsQueue, "enqueue_dlq", new=AsyncMock()) as mock_dlq,
    ):
        worker.running = True
        await worker.run()
        mock_redis.xack.assert_called_once_with(
            "contact_jobs", "email_workers", "job-2"
        )
        mock_dlq.assert_called_once()


@pytest.mark.asyncio
async def test_worker_corrupt_payload_does_not_crash_loop():
    mock_redis = AsyncMock()
    mock_redis.xautoclaim.return_value = ["0", []]
    # payload is completely invalid JSON
    mock_redis.xreadgroup.return_value = [
        (
            "contact_jobs",
            [("job-1", {"job_name": "send_contact_email", "payload": "{bad json"})],
        )
    ]

    worker = StreamWorker("redis://localhost")

    def stop_once(*args, **kwargs):
        worker.running = False
        return mock_redis.xreadgroup.return_value

    mock_redis.xreadgroup.side_effect = stop_once

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch.object(RedisStreamsQueue, "enqueue_dlq", new=AsyncMock()) as mock_dlq,
    ):
        await worker.run()
        # It handles the JSONDecodeError internally, moves to DLQ, and ACKs
        mock_redis.xack.assert_called_once_with(
            "contact_jobs", "email_workers", "job-1"
        )
        mock_dlq.assert_called_once()


@pytest.mark.asyncio
async def test_worker_reclaims_pel():
    mock_redis = AsyncMock()
    payload = {
        "job_name": "send_contact_email",
        "payload": {"name": "a", "email": "a@a.com", "message": "m"},
        "meta": {"retry_count": 0},
    }
    mock_redis.xpending.return_value = {"pending": 1}
    mock_redis.xautoclaim.return_value = [
        "0",
        [
            (
                "job-pel-1",
                {"job_name": "send_contact_email", "payload": json.dumps(payload)},
            )
        ],
    ]

    worker = StreamWorker("redis://localhost", recovery_interval=0.01)

    uc_mock = AsyncMock()
    uc_mock.execute.return_value = True

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("app.worker.get_send_contact_use_case", return_value=uc_mock),
    ):
        worker.running = True
        task = asyncio.create_task(worker._recovery_loop())
        await asyncio.sleep(0.05)
        worker.running = False
        await task

        mock_redis.xpending.assert_called()
        mock_redis.xautoclaim.assert_called()


@pytest.mark.asyncio
async def test_worker_recovery_reports_pending():
    """Recovery loop reports pending count via worker_recovery_runs_total metric."""
    mock_redis = AsyncMock()
    mock_redis.xpending.return_value = {"pending": 7}
    mock_redis.xautoclaim.return_value = ["0", []]

    worker = StreamWorker("redis://localhost", recovery_interval=0.01)

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("app.worker.inc_recovery_run") as inc_mock,
    ):
        worker.running = True
        task = asyncio.create_task(worker._recovery_loop())
        await asyncio.sleep(0.05)
        worker.running = False
        await task

        mock_redis.xpending.assert_called()
        inc_mock.assert_called_with(7)


@pytest.mark.asyncio
async def test_worker_xadds_before_xack_on_retry():
    mock_redis = AsyncMock()
    payload = {
        "job_name": "send_contact_email",
        "payload": {"name": "a", "email": "a@a.com", "message": "m"},
        "meta": {"retry_count": 0},
    }
    mock_redis.xautoclaim.return_value = ["0", []]
    mock_redis.xreadgroup.return_value = [
        (
            "contact_jobs",
            [
                (
                    "job-1",
                    {"job_name": "send_contact_email", "payload": json.dumps(payload)},
                )
            ],
        )
    ]

    worker = StreamWorker("redis://localhost")

    def stop_once(*args, **kwargs):
        worker.running = False
        return mock_redis.xreadgroup.return_value

    mock_redis.xreadgroup.side_effect = stop_once

    uc_mock = AsyncMock()
    uc_mock.execute.side_effect = TimeoutError("Connection timeout")

    calls: list[str] = []

    async def xack_side_effect(*args, **kwargs):
        calls.append("xack")

    async def xadd_side_effect(*args, **kwargs):
        calls.append("xadd")

    mock_redis.xack.side_effect = xack_side_effect
    mock_redis.xadd.side_effect = xadd_side_effect

    with (
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("app.worker.get_send_contact_use_case", return_value=uc_mock),
        patch("asyncio.sleep", new=AsyncMock()),
    ):
        await worker.run()

    assert "xack" in calls and "xadd" in calls
    assert calls.index("xadd") < calls.index("xack")


@pytest.mark.asyncio
async def test_worker_signal_handler_unix(monkeypatch):
    """On non-Windows platforms, worker uses loop.add_signal_handler for graceful shutdown."""
    from app.worker import main

    monkeypatch.setattr("app.worker.settings.redis_url", "redis://localhost")
    monkeypatch.setattr("app.worker.sys.platform", "linux")

    registered_signals: list[int] = []

    class FakeLoop:
        def add_signal_handler(self, sig, cb):
            registered_signals.append(sig)

    fake_loop = FakeLoop()

    async def fake_run(self):
        pass

    with (
        patch("app.worker.asyncio.get_running_loop", return_value=fake_loop),
        patch.object(StreamWorker, "run", new=fake_run),
    ):
        await main()

    import signal as _signal

    assert _signal.SIGINT in registered_signals
    assert _signal.SIGTERM in registered_signals


@pytest.mark.asyncio
async def test_worker_signal_handler_windows(monkeypatch):
    """On Windows, worker falls back to signal.signal for graceful shutdown."""
    from app.worker import main

    monkeypatch.setattr("app.worker.settings.redis_url", "redis://localhost")
    monkeypatch.setattr("app.worker.sys.platform", "win32")

    registered_signals: list[int] = []

    def fake_signal(sig, handler):
        registered_signals.append(sig)

    import signal as _signal

    async def fake_run(self):
        pass

    with (
        patch("app.worker.signal.signal", side_effect=fake_signal),
        patch.object(StreamWorker, "run", new=fake_run),
    ):
        await main()

    assert _signal.SIGINT in registered_signals
    assert _signal.SIGTERM in registered_signals
