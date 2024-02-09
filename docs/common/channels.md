## Channels (Pub-sub)

Channels is a common module in `starlette_web`, designed to provide a pub-sub functionality.
It is named after `django-channels`, however is based off `https://github.com/encode/broadcaster`.
The core is adapted to `anyio`, whereas underlying channel layers may depend on `asyncio`-based libraries.

The exact type of delivering pipeline is based on underlying channel layer, and may either require
acknowledgement, or be fire-and-forget.

Supported channel layers:

- `starlette_web.common.channels.layers.local_memory.InMemoryChannelLayer` -single-process, fire-and-forget, for testing
- `starlette_web.contrib.redis.channel_layers.RedisPubSubChannelLayer` - cross-process, fire-and-forget
- `starlette_web.contrib.postgres.channel_layers.PostgreSQLChannelLayer` - cross-process, fire-and-forget
- `starlette_web.contrib.mqtt.MQTTChannelLayer` - cross-process, experimental, supports acknowledgement

## Example

```python3
from starlette_web.common.channels.base import Channel
from starlette_web.common.channels.layers.local_memory import InMemoryChannelLayer

async with Channel(InMemoryChannelLayer()) as channel:
    await channel.publish("chatroom", {"message": "Message"})
    ...
    async with channel.subscribe("chatroom") as subscribe:
        # This is infinite iterator, so use it in a scope, where it can be cancelled/stopped
        # i.e. websockets, anyio.move_on_after, or simply with an exiting message
        async for event in subscribe:
            await process_event(event)
```

## Subscribing to multiple groups/channels

Currently, this not implemented for default channel layers, 
since different brokers support such behavior differently, 
and some do not support at all. 
You may define a custom channel layer for this purpose. Example:

```python3
from starlette_web.contrib.redis.channel_layers import RedisPubSubChannelLayer


class RedisMultipleChannelLayer(RedisPubSubChannelLayer):
    def subscribe(self, groups: str) -> None:
        groups = groups.split(";")
        # Redis SUBSCRIBE command accepts multiple arguments
        # https://redis.io/commands/subscribe/
        await self._pubsub.subscribe(*groups)

    def unsubscribe(self, groups: str) -> None:
        groups = groups.split(";")
        # Redis UNSUBSCRIBE command accepts multiple arguments
        # https://redis.io/commands/unsubscribe/
        await self._pubsub.unsubscribe(*groups)


class RedisMultiplePatternsChannelLayer(RedisPubSubChannelLayer):
    def subscribe(self, patterns: str) -> None:
        patterns = patterns.split(";")
        # https://redis.io/commands/psubscribe/
        await self._pubsub.psubscribe(*patterns)

    def unsubscribe(self, patterns: str) -> None:
        patterns = patterns.split(";")
        # https://redis.io/commands/punsubscribe/
        await self._pubsub.punsubscribe(*patterns)
```

Another approach is to create a single connection and subscribe to multiple topics in different coroutines:

```python
import anyio

from starlette_web.common.channels.base import Channel
from starlette_web.common.channels.layers.local_memory import InMemoryChannelLayer

async def subscribe_to_channel_topic(channel: Channel, topic: str):
    async with channel.subscribe("chatroom") as subscribe:
        # This is infinite iterator, so use it in a scope, where it can be cancelled/stopped
        # i.e. websockets, anyio.move_on_after, or simply with an exiting message
        async for event in subscribe:
            await process_event(event)

async with Channel(InMemoryChannelLayer()) as channel:
    async with anyio.create_task_group() as task_group:
        task_group.start_soon(subscribe_to_channel_topic, channel, "topic_1")
        task_group.start_soon(subscribe_to_channel_topic, channel, "topic_2")
```

## Acknowledgement

If you want to publish messages and guarantee, that recipient has got them, you need to use
broker that allows acknowledgement for messages. Again, this is not provided by default, and 
you'll have to define a custom channel layer for this purpose. 
For an example, see kafka backend for `encode/broadcaster`:

- https://github.com/encode/broadcaster/blob/956571d030d33d6cb820758ec5ed8fe79c3288c6/broadcaster/_backends/kafka.py

For Redis, use redis Streams which support acknowledgment:  
- https://redis.io/commands/xack/
- https://github.com/encode/broadcaster/blob/3cfcc8b41339862b1f5d50f42ab027bcae92d78c/broadcaster/_backends/redis_stream.py

## Limitations & Caveats

#### Channel initialization

It is preferable to **only use channels as async context manager**, 
since it registers its own `anyio.TaskGroup`.
In some cases, like websockets, when you need to control channel creation and deletion, 
there are available synchronisation mechanisms with `anyio.Event`.

#### Backpressure

Built-in `InMemoryChannelLayer` may be prone to 
[backpressure](https://vorpus.org/blog/some-thoughts-on-asynchronous-api-design-in-a-post-asyncawait-world/#bug-1-backpressure)
problem, if publish happens much more often, than listening to messages. In case of other channel layers,
backpressure is theoretically possible on the broker side. This is not something you should expect on a
daily basis (it concerns cases with 10k+ messages per minute), 
but it is preferable to design exchange with relatively short messages. 

## Examples

- `starlette_web.tests.contrib.test_channels.TestChannelLayers`
- `starlette_web.tests.views.websocket.ChatWebsocketTestEndpoint`
