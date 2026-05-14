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
    payload = {"job_name": "send_contact_email", "payload": {"name": "a", "email": "a@a.com", "message": "m"}, "meta": {"retry_count": 0}}
    mock_redis.xautoclaim.return_value = ["0", []]
    mock_redis.xreadgroup.return_value = [("contact_jobs", [("job-1", {"job_name": "send_contact_email", "payload": json.dumps(payload)})])]

    worker = StreamWorker("redis://localhost")

    def stop_once(*args, **kwargs):
        worker.running = False
        return mock_redis.xreadgroup.return_value

    mock_redis.xreadgroup.side_effect = stop_once

    uc_mock = AsyncMock()
    uc_mock.execute.side_effect = ValueError("Invalid email format") # Permanent

    with patch("redis.asyncio.from_url", return_value=mock_redis), patch(
        "app.worker.get_send_contact_use_case", return_value=uc_mock
    ), patch.object(RedisStreamsQueue, "enqueue_dlq", new=AsyncMock()) as mock_dlq:
        await worker.run()
        mock_redis.xack.assert_called_once_with("contact_jobs", "email_workers", "job-1")
        mock_dlq.assert_called_once()


@pytest.mark.asyncio
async def test_worker_transient_error_retries_and_re_enqueues():
    mock_redis = AsyncMock()
    payload = {"job_name": "send_contact_email", "payload": {"name": "a", "email": "a@a.com", "message": "m"}, "meta": {"retry_count": 0}}
    mock_redis.xautoclaim.return_value = ["0", []]
    mock_redis.xreadgroup.return_value = [("contact_jobs", [("job-1", {"job_name": "send_contact_email", "payload": json.dumps(payload)})])]

    worker = StreamWorker("redis://localhost")

    def stop_once(*args, **kwargs):
        worker.running = False
        return mock_redis.xreadgroup.return_value

    mock_redis.xreadgroup.side_effect = stop_once

    uc_mock = AsyncMock()
    uc_mock.execute.side_effect = TimeoutError("Connection timeout") # Transient

    with patch("redis.asyncio.from_url", return_value=mock_redis), patch(
        "app.worker.get_send_contact_use_case", return_value=uc_mock
    ), patch("asyncio.sleep", new=AsyncMock()):
        await worker.run()
        # Should xack the old one
        mock_redis.xack.assert_called_once_with("contact_jobs", "email_workers", "job-1")
        # Should xadd a new one for retry
        assert mock_redis.xadd.call_count == 1
        args, _ = mock_redis.xadd.call_args
        assert args[0] == "contact_jobs"


@pytest.mark.asyncio
async def test_worker_transient_error_exceeds_retries_and_dlq():
    mock_redis = AsyncMock()
    payload = {"job_name": "send_contact_email", "payload": {"name": "a", "email": "a@a.com", "message": "m"}, "meta": {"retry_count": 3}} # Max retries
    mock_redis.xautoclaim.return_value = ["0", []]
    mock_redis.xreadgroup.return_value = [("contact_jobs", [("job-1", {"job_name": "send_contact_email", "payload": json.dumps(payload)})])]

    worker = StreamWorker("redis://localhost")

    def stop_once(*args, **kwargs):
        worker.running = False
        return mock_redis.xreadgroup.return_value

    mock_redis.xreadgroup.side_effect = stop_once

    uc_mock = AsyncMock()
    uc_mock.execute.side_effect = TimeoutError("Connection timeout") # Transient

    with patch("redis.asyncio.from_url", return_value=mock_redis), patch(
        "app.worker.get_send_contact_use_case", return_value=uc_mock
    ), patch.object(RedisStreamsQueue, "enqueue_dlq", new=AsyncMock()) as mock_dlq:
        await worker.run()
        mock_redis.xack.assert_called_once_with("contact_jobs", "email_workers", "job-1")
        mock_dlq.assert_called_once()


@pytest.mark.asyncio
async def test_worker_unknown_error_1_retry_then_dlq():
    mock_redis = AsyncMock()
    # First attempt (retry=0)
    payload = {"job_name": "send_contact_email", "payload": {"name": "a", "email": "a@a.com", "message": "m"}, "meta": {"retry_count": 0}}
    mock_redis.xautoclaim.return_value = ["0", []]
    mock_redis.xreadgroup.return_value = [("contact_jobs", [("job-1", {"job_name": "send_contact_email", "payload": json.dumps(payload)})])]

    worker = StreamWorker("redis://localhost")

    def stop_once(*args, **kwargs):
        worker.running = False
        return mock_redis.xreadgroup.return_value

    mock_redis.xreadgroup.side_effect = stop_once

    uc_mock = AsyncMock()
    uc_mock.execute.side_effect = Exception("Mysterious failure") # Unknown

    with patch("redis.asyncio.from_url", return_value=mock_redis), patch(
        "app.worker.get_send_contact_use_case", return_value=uc_mock
    ), patch("asyncio.sleep", new=AsyncMock()):
        await worker.run()
        # Should xack old and xadd new
        mock_redis.xack.assert_called_once_with("contact_jobs", "email_workers", "job-1")
        assert mock_redis.xadd.call_count == 1

    # Second attempt (retry=1)
    mock_redis.reset_mock()
    payload["meta"]["retry_count"] = 1
    mock_redis.xautoclaim.return_value = ["0", []]
    mock_redis.xreadgroup.return_value = [("contact_jobs", [("job-2", {"job_name": "send_contact_email", "payload": json.dumps(payload)})])]
    mock_redis.xreadgroup.side_effect = stop_once

    with patch("redis.asyncio.from_url", return_value=mock_redis), patch(
        "app.worker.get_send_contact_use_case", return_value=uc_mock
    ), patch.object(RedisStreamsQueue, "enqueue_dlq", new=AsyncMock()) as mock_dlq:
        worker.running = True
        await worker.run()
        mock_redis.xack.assert_called_once_with("contact_jobs", "email_workers", "job-2")
        mock_dlq.assert_called_once()


@pytest.mark.asyncio
async def test_worker_corrupt_payload_does_not_crash_loop():
    mock_redis = AsyncMock()
    mock_redis.xautoclaim.return_value = ["0", []]
    # payload is completely invalid JSON
    mock_redis.xreadgroup.return_value = [("contact_jobs", [("job-1", {"job_name": "send_contact_email", "payload": "{bad json"})])]

    worker = StreamWorker("redis://localhost")

    def stop_once(*args, **kwargs):
        worker.running = False
        return mock_redis.xreadgroup.return_value

    mock_redis.xreadgroup.side_effect = stop_once

    with patch("redis.asyncio.from_url", return_value=mock_redis), patch.object(RedisStreamsQueue, "enqueue_dlq", new=AsyncMock()) as mock_dlq:
        await worker.run()
        # It handles the JSONDecodeError internally, moves to DLQ, and ACKs
        mock_redis.xack.assert_called_once_with("contact_jobs", "email_workers", "job-1")
        mock_dlq.assert_called_once()


@pytest.mark.asyncio
async def test_worker_reclaims_pel():
    mock_redis = AsyncMock()
    # Reclaim returns 1 message
    payload = {"job_name": "send_contact_email", "payload": {"name": "a", "email": "a@a.com", "message": "m"}, "meta": {"retry_count": 0}}
    mock_redis.xautoclaim.return_value = ["0", [("job-pel-1", {"job_name": "send_contact_email", "payload": json.dumps(payload)})]]

    worker = StreamWorker("redis://localhost")
    worker.running = False # So it just runs one iteration and exits

    uc_mock = AsyncMock()
    uc_mock.execute.return_value = True

    with patch("redis.asyncio.from_url", return_value=mock_redis), patch(
        "app.worker.get_send_contact_use_case", return_value=uc_mock
    ):
        worker.running = True
        # Monkey patch run to break out after one successful iteration
        original_xautoclaim = mock_redis.xautoclaim
        def side_effect(*args, **kwargs):
            worker.running = False
            return ["0", [("job-pel-1", {"job_name": "send_contact_email", "payload": json.dumps(payload)})]]
        mock_redis.xautoclaim.side_effect = side_effect

        await worker.run()

        # Should xack the pel message
        mock_redis.xack.assert_called_once_with("contact_jobs", "email_workers", "job-pel-1")
        # xreadgroup should not even be called because claim_res was truthy
        mock_redis.xreadgroup.assert_not_called()
