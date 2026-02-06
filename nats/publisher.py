import asyncio
import json
import logging
from typing import Any, Callable, Dict

from smart_common.nats.client import nats_client

logger = logging.getLogger(__name__)


class NatsPublisher:
    def __init__(self, client):
        self.client = client
        self._closing = False
        self._publish_lock = asyncio.Lock()

    async def publish(
        self,
        subject: str,
        payload: Dict[str, Any],
        *,
        retries: int = 3,
        context: Dict[str, Any] | None = None,
    ):
        if self._closing:
            raise RuntimeError("NATS publisher is shutting down")

        context = context or {}
        data = json.dumps(payload).encode("utf-8")
        last_error: Exception | None = None

        for attempt in range(1, retries + 1):
            if self.client.is_draining():
                await self._handle_draining_connection(context, subject, attempt)
                last_error = RuntimeError("NATS connection draining")
                await asyncio.sleep(self._backoff(attempt))
                continue

            async with self._publish_lock:
                if not await self._ensure_ready_for_publish(context, subject, attempt):
                    last_error = RuntimeError("NATS connection not ready")
                    await asyncio.sleep(self._backoff(attempt))
                    continue

                try:
                    logger.info(
                        "[NATS] Publishing",
                        extra={
                            **context,
                            "subject": subject,
                            "attempt": attempt,
                        },
                    )
                    js = self.client.js
                    if not js:
                        raise RuntimeError("JetStream not initialized")

                    ack = await js.publish(
                        subject=subject,
                        payload=data,
                        timeout=5.0,
                    )

                    logger.info(
                        "[NATS] Published",
                        extra={
                            **context,
                            "subject": subject,
                            "seq": ack.seq,
                            "payload_bytes": len(data),
                            "payload": data,
                        },
                    )
                    return ack

                except Exception as exc:
                    last_error = exc
                    logger.error(
                        "[NATS] Publish failed",
                        extra={
                            **context,
                            "subject": subject,
                            "attempt": attempt,
                            "error": str(exc),
                        },
                    )
                    if attempt < retries:
                        await self._recover_connection(exc, context, subject, attempt)
                        await asyncio.sleep(self._backoff(attempt))
                    else:
                        raise

        raise Exception(
            f"NATS publish failed after {retries} attempts",
            last_error,
        )

    async def _ensure_ready_for_publish(
        self,
        context: Dict[str, Any],
        subject: str,
        attempt: int,
    ) -> bool:
        if self.client.is_ready():
            return True

        try:
            await self.client.ensure_connected()
        except Exception as exc:
            logger.warning(
                "[NATS] Ensure connected failed",
                extra={
                    **context,
                    "subject": subject,
                    "attempt": attempt,
                    "error": str(exc),
                },
            )
            return False

        return self.client.is_ready()

    async def _handle_draining_connection(
        self,
        context: Dict[str, Any],
        subject: str,
        attempt: int,
    ) -> None:
        logger.warning(
            "[NATS] Connection draining before publish",
            extra={
                **context,
                "subject": subject,
                "attempt": attempt,
            },
        )
        await self._recover_connection(
            RuntimeError("connection draining"),
            context,
            subject,
            attempt,
        )

    async def _recover_connection(
        self,
        exc: Exception,
        context: Dict[str, Any],
        subject: str,
        attempt: int,
    ) -> None:
        if self.client.nc and getattr(self.client.nc, "is_closed", False):
            try:
                await self.client.reset_connection()
            except Exception as reset_exc:
                logger.warning(
                    "[NATS] Reconnection step failed",
                    extra={
                        **context,
                        "subject": subject,
                        "attempt": attempt,
                        "error": str(reset_exc),
                    },
                )

    def _backoff(self, attempt: int) -> float:
        return min(0.3, 0.1 * attempt)

    async def close(self):
        if self._closing:
            return
        self._closing = True
        await self.client.close()

    async def publish_and_wait_for_ack(
        self,
        subject: str,
        ack_subject: str,
        message: Dict[str, Any],
        predicate: Callable[[Dict[str, Any]], bool],
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        await self.client.ensure_connected()

        js = self.client.js
        if not js:
            raise RuntimeError("JetStream not initialized")

        data = json.dumps(message).encode("utf-8")
        future = asyncio.get_event_loop().create_future()

        async def ack_handler(msg):
            try:
                payload = json.loads(msg.data.decode())

                if predicate(payload) and not future.done():
                    future.set_result(payload)

            except Exception as e:
                if not future.done():
                    future.set_exception(e)

        sub = await self.client.nc.subscribe(ack_subject, cb=ack_handler)

        await js.publish(subject=subject, payload=data)

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise Exception("Timeout waiting for ACK")
        finally:
            await sub.unsubscribe()

        return result


publisher = NatsPublisher(nats_client)
