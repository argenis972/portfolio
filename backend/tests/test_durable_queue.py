import json
import pytest
from unittest.mock import AsyncMock, patch
from app.core.queue import RedisStreamsQueue
from app.worker import StreamWorker


@pytest.mark.asyncio
async def test_redis_queue_enqueue_success():
    """Verifies that RedisStreamsQueue.enqueue calls xadd with correct params."""
    mock_redis = AsyncMock()

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        queue = RedisStreamsQueue("redis://localhost", stream_name="test_stream")
        payload = {"test": "data"}

        await queue.enqueue("test_job", payload)

        # Verify xadd call
        mock_redis.xadd.assert_called_once()
        args, kwargs = mock_redis.xadd.call_args
        assert args[0] == "test_stream"
        assert kwargs["maxlen"] == 10000
        assert kwargs["approximate"] is True

        # Verify data content
        data = args[1]
        assert data["job_name"] == "test_job"
        assert json.loads(data["payload"]) == payload


@pytest.mark.asyncio
async def test_worker_process_job_calls_use_case():
    """Verifies that StreamWorker correctly dispatches a job to the use case."""
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = True

    # Payload for the job
    payload = {
        "name": "Argenis",
        "email": "test@example.com",
        "message": "Hello World",
        "subject": "Test",
        "is_suspicious": False,
        "spam_score": 10,
    }

    job_data = {"job_name": "send_contact_email", "payload": json.dumps(payload)}

    worker = StreamWorker("redis://localhost")

    # Mock dependencies
    with patch("app.worker.get_send_contact_use_case", return_value=mock_use_case):
        await worker.process_job("job-123", job_data)

        # Verify use case execution
        mock_use_case.execute.assert_called_once_with(
            name="Argenis",
            email="test@example.com",
            subject="Test",
            message="Hello World",
            is_suspicious=False,
            spam_score=10,
        )


@pytest.mark.asyncio
async def test_worker_ack_after_processing():
    """Verifies that the worker ACKs the message after successful processing."""
    mock_redis = AsyncMock()
    # Mock xreadgroup response: [(stream_name, [(job_id, data)])]
    payload = {"name": "Test", "email": "test@test.com", "message": "msg"}
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
    # Avoid infinite loop
    worker.running = True

    def stop_worker(*args, **kwargs):
        worker.running = False
        return mock_redis.xreadgroup.return_value

    mock_redis.xreadgroup.side_effect = stop_worker

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        with patch("app.worker.get_send_contact_use_case", return_value=AsyncMock()):
            await worker.run()

            # Verify xack was called
            mock_redis.xack.assert_called_once_with(
                "contact_jobs", "email_workers", "job-1"
            )
