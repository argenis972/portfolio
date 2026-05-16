import asyncio
from redis import asyncio as redis


async def inject_poison_message(redis_url: str, stream: str = "contact_jobs") -> str:
    client = redis.from_url(redis_url, decode_responses=True)
    return await client.xadd(
        stream, {"job_name": "send_contact_email", "payload": "{bad-json"}
    )


async def simulate_redis_intermittent(redis_url: str) -> None:
    client = redis.from_url(redis_url, decode_responses=True)
    await client.ping()
    await client.aclose()  # type: ignore[attr-defined]
    await asyncio.sleep(0.2)


if __name__ == "__main__":
    raise SystemExit("Use from tests or local scripts.")
