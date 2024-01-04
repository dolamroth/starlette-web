# Adapted from https://github.com/sabuhish/fastapi-mqtt/blob/master/fastapi_mqtt/fastmqtt.py

import logging
import ssl
import uuid
from itertools import zip_longest
from typing import Any, Optional, Union, Literal, Type, Set

import anyio
from anyio.streams.memory import (
    MemoryObjectReceiveStream,
    MemoryObjectSendStream,
    ClosedResourceError,
)
from gmqtt import Client as MQTTClient
from gmqtt.mqtt.connection import MQTTConnection
from gmqtt.mqtt.constants import MQTTv50, MQTTv311
from gmqtt.mqtt.protocol import MQTTProtocol
from gmqtt.mqtt.property import PROPERTIES_BY_NAME

from starlette_web.common.channels.event import Event
from starlette_web.common.channels.exceptions import ListenerClosed
from starlette_web.common.channels.layers.base import BaseChannelLayer
from starlette_web.common.utils.inspect import get_available_options
from starlette_web.common.utils.serializers import BytesSerializer
from starlette_web.contrib.mqtt.serializers import MQTTSerializer


logger = logging.getLogger("starlette_web.contrib.mqtt")


class MQTTChannelLayer(BaseChannelLayer):
    """
    Experimental implementation of MQTT support.

    Underlying library may be changed
    (to anyio client, when such is developed and out of pre-alpha,
    or to aiomqtt, once issue with Windows.ProactorEventLoop is fixed)

    NOTE: gmqtt has problems with auto-switching to 4-th version of protocol,
    so you have to manually set it.
    """

    client: MQTTClient
    _available_options = list(
        {
            "retry_deliver_timeout",
            "persistent_storage",
            "topic_alias_maximum",
            *get_available_options(MQTTConnection.auth),
            *get_available_options(MQTTProtocol.send_auth_package),
            *list(PROPERTIES_BY_NAME.keys()),
        }
    )
    serializer_class: Type[BytesSerializer] = MQTTSerializer
    _connection_closed_flag = object()

    def __init__(self, **options):
        super().__init__(**options)

        self.host: str = options.pop("host", "localhost")
        self.port: int = options.pop("port", 1883)
        self.ssl: Union[bool, ssl.SSLContext] = options.pop("ssl", False)
        self.keepalive: int = options.pop("keepalive", 60)
        self.username: Optional[str] = options.pop("username", None)
        self.password: Optional[str] = options.pop("password", None)
        self.version: Literal[MQTTv50, MQTTv311] = options.pop("version", MQTTv50)

        self.reconnect_retries: Optional[int] = options.pop("reconnect_retries", 1)
        self.reconnect_delay: Optional[int] = options.pop("reconnect_delay", 6)

        self.client_id = options.get("client_id", uuid.uuid4().hex)
        self.client = MQTTClient(
            self.client_id,
            **{key: value for key, value in options.items() if key in self._available_options},
        )

        self.clean_session: bool = options.get("clean_session", True)
        self.optimistic_acknowledgement: bool = options.get("optimistic_acknowledgement", True)

        self.client._clean_session = self.clean_session
        self.client._username = self.username
        self.client._password = self.password
        self.client._host = self.host
        self.client._port = self.port
        self.client._keepalive = self.keepalive
        self.client._ssl = self.ssl
        self.client.optimistic_acknowledgement = self.optimistic_acknowledgement
        self.subscriptions: Set[str] = set()

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.on_subscribe = self._on_subscribe

        self._receive_stream: Optional[MemoryObjectReceiveStream] = None
        self._send_stream: Optional[MemoryObjectSendStream] = None
        self._serializer = self.serializer_class()

    def __str__(self):
        return f"{MQTTChannelLayer} {self.host}:{self.port} [{self.client_id}]"

    async def connect(self) -> None:
        self._send_stream, self._receive_stream = anyio.create_memory_object_stream()

        if self.client._username:
            self.client.set_auth_credentials(self.client._username, self.client._password)
            logger.debug("User is authenticated")

        self.client.set_config(
            {
                "reconnect_retries": self.reconnect_retries,
                "reconnect_delay": self.reconnect_delay,
            }
        )

        version = self.version or MQTTv50
        logger.info("Used broker version is %s", version)

        await self.client.connect(
            self.client._host,
            self.client._port,
            self.client._ssl,
            self.client._keepalive,
            version,
        )
        logger.debug(f"Connected to {self}")

    async def disconnect(self) -> None:
        try:
            await self.client.disconnect()
        finally:
            self._receive_stream.close()
            self._send_stream.close()
            self._receive_stream = None
            self._send_stream = None

    async def subscribe(
        self,
        topic: str,
        qos: int = 0,
        no_local: bool = False,
        retain_as_published: bool = False,
        retain_handling_options: int = 0,
        subscription_identifier: Any = None,
        **kwargs,
    ) -> None:
        logger.debug(f"Subscribe to {topic}")
        self.subscriptions.add(topic)
        self.client.subscribe(topic)

    async def unsubscribe(self, topic: str, **kwargs) -> None:
        """
        Defined to unsubscribe topic

        topic: topic name
        """
        logger.debug(f"Unsubscribe from {topic}")
        if topic in self.subscriptions:
            self.subscriptions.discard(topic)

        return self.client.unsubscribe(topic, **kwargs)

    async def publish(
        self,
        topic: str,
        message: Any,
        qos: int = 0,
        retain: bool = False,
        **kwargs,
    ) -> None:
        """
        Defined to publish payload MQTT server

        message_or_topic: topic name

        payload: message payload

        qos: Quality of Assurance

        retain:
        """
        _message = self._serializer.serialize(message)
        return self.client.publish(topic, payload=_message, qos=qos, retain=retain, **kwargs)

    async def next_published(self) -> Event:
        try:
            event: Event = await self._receive_stream.receive()
        except ClosedResourceError as exc:
            raise ListenerClosed from exc

        return event

    def _on_subscribe(self, client, mid, qos, properties):
        logger.debug("SUBSCRIBED")

    def _on_connect(self, client: MQTTClient, flags: int, rc: int, properties: Any):
        """
        Generic on connecting handler, it would call user handler if defined.
        Will perform subscription for given topics.
        It cannot be done earlier, since subscription relies on connection.
        """
        for topic in self.subscriptions:
            logger.debug(f"Subscribing for {topic}")
            self.client.subscribe(topic)

    async def _on_message(
        self,
        client: MQTTClient,
        topic: str,
        payload: bytes,
        qos: int,
        properties: Any,
    ):
        _decoded = self._serializer.deserialize(payload)
        logger.debug(f"Received message: {topic}, {_decoded}, {qos}, {properties}")

        for template in self.subscriptions.copy():
            if self.match(topic, template):
                event = Event(group=template, message=_decoded)
                await self._send_stream.send(event)

    def _on_disconnect(self, client, packet, exc=None):
        logger.debug(f"Disconnected from {self}")
        self._send_stream.close()

    @staticmethod
    def match(topic: str, template: str) -> bool:
        """
        Defined match topics

        topic: topic name
        template: template topic name that contains wildcards
        """
        if str(template).startswith("$share/"):
            template = template.split("/", 2)[2]

        topic_parts = topic.split("/")
        template_parts = template.split("/")

        for topic_part, part in zip_longest(topic_parts, template_parts):
            if part == "#" and not str(topic_part).startswith("$"):
                return True
            elif (topic_part is None or part not in {"+", topic_part}) or (
                part == "+" and topic_part.startswith("$")
            ):
                return False
            continue

        return len(template_parts) == len(topic_parts)
