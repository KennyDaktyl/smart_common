# smart_common/nats/module.py

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from smart_common.events.event_dispatcher import EventDispatcher
from smart_common.nats.client import NATSClient
from smart_common.nats.listener import NatsListener
from smart_common.nats.publisher import NatsPublisher
from smart_common.nats.event_helpers import stream_name

logger = logging.getLogger(__name__)


class NatsModule:

    def __init__(self, create_stream: bool = False):
        self.client = NATSClient()
        self.publisher = NatsPublisher(self.client)
        self.listener = NatsListener(self.client)
        self.events = EventDispatcher(self.publisher)
        self.create_stream = create_stream

    async def _ensure_stream(self):
        await self.client.ensure_connected()
        js = self.client.js
        if js is None:
            raise RuntimeError("JetStream context unavailable when ensuring stream.")

        try:
            existing = await js.stream_info(stream_name())
            logger.info(
                "[NATS] Stream %s already exists.", stream_name()
            )
        except Exception:
            logger.warning(
                "[NATS] Stream missing — creating %s...", stream_name()
            )
            await js.add_stream(
                name=stream_name(),
                subjects=[f"{stream_name()}.>"],
                storage="file",
                retention="limits",
            )
            logger.info("[NATS] Stream %s created.", stream_name())

    async def ensure_stream(self):
        await self._ensure_stream()

    def init_app(self, app: FastAPI):

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            logger.info("[NATS] Connecting...")

            await self.client.connect()

            if self.create_stream:
                await self._ensure_stream()

            await self.listener.subscribe()

            logger.info("[NATS] Ready.")

            app.state.nats = self

            yield

            logger.info("[NATS] Closing...")
            await self.client.close()

        app.router.lifespan_context = lifespan
        logger.info("[NATS] Lifespan enabled.")


nats_module = NatsModule(create_stream=False)
