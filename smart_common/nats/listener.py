import json
import logging

from nats.js.api import DeliverPolicy

from smart_common.nats.client import nats_client

logger = logging.getLogger(__name__)


class NatsListener:

    def __init__(self, client=nats_client):
        self.client = client
        self.consumer_name = "device_communication_listener"

    async def subscribe(self):
        if not self.client.js:
            raise RuntimeError("JetStream not initialized — did you call connect()?")

        async def handler(msg):
            try:
                subject = msg.subject
                data = json.loads(msg.data.decode("utf-8"))

                logger.info(f"[NATS] Received subject={subject} data={data}")

                await msg.ack()
            except Exception as e:
                logger.exception(f"[NATS] Failed to process message: {e}")

        sub = await self.client.js.subscribe(
            subject="device_communication.>",
            durable=self.consumer_name,
            stream="device_communication",
            manual_ack=True,
            ack_wait=10,
            deliver_policy=DeliverPolicy.NEW,
            cb=handler,
        )

        logger.info(
            "[NATS] Listener subscribed to device_communication.> "
            f"with durable={self.consumer_name}"
        )

        return sub
