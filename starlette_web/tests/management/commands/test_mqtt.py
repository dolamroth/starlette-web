import anyio

from starlette_web.common.channels.base import Channel
from starlette_web.common.management.base import BaseCommand
from starlette_web.contrib.mqtt.channel_layers import MQTTChannelLayer


class Command(BaseCommand):
    help = "Command to test mqtt"

    async def handle(self, **options):
        group_1 = "#"

        # TODO: set from config file / from command line
        group_2 = None
        mqtt_options = {}
        channel_ctx = Channel(MQTTChannelLayer(**mqtt_options))

        async def subscribe_task(_channel, _topic):
            async with _channel.subscribe(_topic) as subscriber:
                i = 0

                async for event in subscriber:
                    print(event.message)
                    i += 1

                    if _topic == "#" and i >= 10:
                        break

        async with channel_ctx as channel:
            await channel.publish("TEST/TEST/TEST", {"1": 1})

            async with anyio.create_task_group() as task_group:
                task_group.start_soon(subscribe_task, channel, group_1)
                task_group.start_soon(subscribe_task, channel, group_2)
