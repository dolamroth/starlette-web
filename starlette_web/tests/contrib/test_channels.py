import sys
from subprocess import DEVNULL

import anyio
import pytest

from starlette_web.common.conf import settings
from starlette_web.common.caches import caches
from starlette_web.common.channels.base import Channel, Event
from starlette_web.common.channels.layers.local_memory import InMemoryChannelLayer
from starlette_web.contrib.redis.channel_layers import RedisPubSubChannelLayer
from starlette_web.contrib.postgres.channel_layers import PostgreSQLChannelLayer
from starlette_web.tests.helpers import await_


class TestChannelLayers:
    # Check both correctness and idempotence of channel layers
    def test_in_memory_channel_layer(self):
        channel_ctx = Channel(InMemoryChannelLayer())
        self.run_channels_test(channel_ctx)
        self.run_channels_test(channel_ctx)
        self.run_channels_test(channel_ctx)

    def test_redis_pubsub_channel_layer(self):
        redis_options = settings.CHANNEL_LAYERS["redispubsub"]["OPTIONS"]
        channel_ctx = Channel(RedisPubSubChannelLayer(**redis_options))
        self.run_channels_test(channel_ctx)
        self.run_channels_test(channel_ctx)
        self.run_channels_test(channel_ctx)

    def test_postgres_channel_layer(self):
        psql_options = {"dsn": settings.DATABASE_DSN.replace("+asyncpg", "")}
        channel_ctx = Channel(PostgreSQLChannelLayer(**psql_options))
        self.run_channels_test(channel_ctx)
        self.run_channels_test(channel_ctx)
        self.run_channels_test(channel_ctx)

    def run_channels_test(self, channel_ctx: Channel):
        accepted_messages = []

        async def publisher_task(channel):
            with anyio.fail_after(2):
                for i in range(5):
                    await anyio.sleep(0.2)
                    await channel.publish("test_group", f"Message {i}")

            # Tests utilize subscribers in an infinite-loop manner,
            # so an outer exception must be raised in order for it to stop.
            # In real application subscribers are expected to be in Websockets,
            # which receive WebsocketDisconnected exception when finished,
            # causing subscriber to stop.
            # This is a mock for tests.
            # Exception will propagate to task group and
            # will close infinite consumers as well.
            await anyio.sleep(0.1)
            raise Exception

        async def subscriber_task(channel: Channel, messages_pool):
            async with channel.subscribe("test_group") as subscriber:
                async for message in subscriber:
                    messages_pool.append(message)

        async def task_coroutine():
            nonlocal accepted_messages

            async with channel_ctx as channels:
                async with anyio.create_task_group() as task_group:
                    task_group.start_soon(publisher_task, channels)
                    task_group.start_soon(subscriber_task, channels, accepted_messages)
                    task_group.start_soon(subscriber_task, channels, accepted_messages)
                    task_group.start_soon(subscriber_task, channels, accepted_messages)

        # Redis will actually raise ExceptionGroup,
        # having 3 subscribers within task group
        # that will raise ConnectionError after close
        with pytest.raises(Exception):
            await_(task_coroutine())

        assert len(accepted_messages) == 15
        messages = []
        for event in accepted_messages:
            assert type(event) is Event
            messages.append(event.message)

        for i in range(5):
            assert messages.count(f"Message {i}") == 3

    def test_channels_crossprocess(self):
        test_group_name = "6B65mbrpcAy4zHAjNOZW8T84c7Yl2b"
        subscriber_1 = "Ej3Qu6JFtVbUXh9qb20z"
        subscriber_2 = "Eh9DnQeYvlLI2x5lkMPb"
        subscriber_3 = "ooF5oCaGYAE9dy8aXBSI"

        async def run_command_in_process(command_name, command_args):
            cmd = (
                f"cd {settings.PROJECT_ROOT_DIR} && "
                f"{sys.executable} command.py {command_name}"
            )

            if command_args:
                cmd += " " + " ".join(command_args)

            async with await anyio.open_process(
                cmd, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL
            ) as process:
                await process.wait()

        async def task_coroutine():
            async with anyio.create_task_group() as task_group:
                task_group.cancel_scope.deadline = anyio.current_time() + 10
                task_group.start_soon(
                    run_command_in_process,
                    "test_channels_publisher",
                    [f"--group={test_group_name}", "--skip_checks"],
                )
                task_group.start_soon(
                    run_command_in_process,
                    "test_channels_subscriber",
                    [f"--group={test_group_name}", f"--subscriber={subscriber_1}", "--skip_checks"],
                )
                task_group.start_soon(
                    run_command_in_process,
                    "test_channels_subscriber",
                    [f"--group={test_group_name}", f"--subscriber={subscriber_2}", "--skip_checks"],
                )
                task_group.start_soon(
                    run_command_in_process,
                    "test_channels_subscriber",
                    [f"--group={test_group_name}", f"--subscriber={subscriber_3}", "--skip_checks"],
                )

        await_(task_coroutine())

        # TODO: share data via file-cache in tests
        default_cache = caches["default"]
        publisher_flag = await_(default_cache.async_get(f"{test_group_name}-publisher-done"))
        assert publisher_flag == 1

        subscriber_1_flag = await_(
            default_cache.async_get(f"{test_group_name}-{subscriber_1}-done")
        )
        subscriber_2_flag = await_(
            default_cache.async_get(f"{test_group_name}-{subscriber_2}-done")
        )
        subscriber_3_flag = await_(
            default_cache.async_get(f"{test_group_name}-{subscriber_3}-done")
        )
        assert subscriber_1_flag == ["Message 0", "Message 1", "Message 2", "DONE"]
        assert subscriber_2_flag == ["Message 0", "Message 1", "Message 2", "DONE"]
        assert subscriber_3_flag == ["Message 0", "Message 1", "Message 2", "DONE"]

    def test_immediate_subscriber_cleanup_on_exit(self):
        async def task_coroutine():
            _publisher_result = []

            async def publisher_task(channel, _res):
                await anyio.sleep(0.1)
                await channel.publish("test_group", "Message")
                await anyio.sleep(0.2)
                _res.append(len(channel._subscribers))
                _res.append(len({
                    k: v
                    for k, v in channel._channel_layer._subscribed.items()
                    if v > 0
                }))

            async def subscriber_task(channel: Channel):
                async with channel.subscribe("test_group") as subscriber:
                    async for message in subscriber:
                        # break immediately
                        break

            async with Channel(InMemoryChannelLayer()) as channels:
                async with anyio.create_task_group() as task_group:
                    task_group.cancel_scope.deadline = anyio.current_time() + 5.0
                    task_group.start_soon(publisher_task, channels, _publisher_result)
                    task_group.start_soon(subscriber_task, channels)
                    task_group.start_soon(subscriber_task, channels)
                    task_group.start_soon(subscriber_task, channels)

            return _publisher_result

        res = await_(task_coroutine())
        assert res == [0, 0]

    def test_multiple_same_subscribers_inmemorychannellayer(self):
        async def task_coroutine():
            _result = []

            async def publisher_task(channel: Channel):
                await anyio.sleep(0.1)
                for _ in range(10):
                    await channel.publish("test_group", "Message")

            async def subscriber_task(channel: Channel, _res: list, break_after: int):
                async with channel.subscribe("test_group") as subscriber:
                    _message_counter = 0
                    async for message in subscriber:
                        if _message_counter >= break_after:
                            break
                        _res.append(message)
                        _message_counter += 1

            async with Channel(InMemoryChannelLayer()) as channels:
                async with anyio.create_task_group() as task_group:
                    task_group.cancel_scope.deadline = anyio.current_time() + 5.0
                    task_group.start_soon(publisher_task, channels)
                    task_group.start_soon(subscriber_task, channels, _result, 5)
                    task_group.start_soon(subscriber_task, channels, _result, 2)
                    task_group.start_soon(subscriber_task, channels, _result, 1)

            return _result

        res = await_(task_coroutine())
        assert len(res) == 8

    def test_publish_in_subscribe_inmemorychannellayer(self):
        async def task_coroutine():
            _result = []

            async def pipeline_1(channel: Channel):
                await anyio.sleep(0.1)
                for _ in range(10):
                    await channel.publish("topic_1", "Message")

            async def pipeline_2(channel: Channel):
                async with channel.subscribe("topic_1") as subscriber:
                    _messages_count = 0
                    async for event in subscriber:
                        await channel.publish("topic_2", event.message)
                        _messages_count += 1
                        if _messages_count >= 10:
                            break

            async def pipeline_3(channel: Channel, _res):
                async with channel.subscribe("topic_2") as subscriber:
                    _messages_count = 0
                    async for event in subscriber:
                        _res.append(event)
                        # This topic is not listened by anyone
                        await channel.publish("topic_3", event.message)
                        _messages_count += 1
                        if _messages_count >= 10:
                            break

            async with Channel(InMemoryChannelLayer()) as channels:
                async with anyio.create_task_group() as task_group:
                    task_group.cancel_scope.deadline = anyio.current_time() + 3.0
                    task_group.start_soon(pipeline_1, channels)
                    task_group.start_soon(pipeline_2, channels)
                    task_group.start_soon(pipeline_3, channels, _result)

            return _result

        res = await_(task_coroutine())
        assert len(res) == 10
