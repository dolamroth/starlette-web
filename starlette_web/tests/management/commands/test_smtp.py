import base64
from email.mime.image import MIMEImage

from starlette_web.common.conf import settings
from starlette_web.common.email import send_email
from starlette_web.common.management.base import BaseCommand


class Command(BaseCommand):
    help = "Command to test smtp"

    async def handle(self, **options):
        settings.EMAIL_SENDER = {
            "BACKEND": "starlette_web.common.email.smtp.SMTPEmailSender",
            "OPTIONS": {
                "hostname": "",
                "port": 465,
                "username": "",
                "password": "",
                "use_tls": True,
            },
        }

        # Small Skyrim icon
        image_raw_data = base64.b64decode(
            b'iVBORw0KGgoAAAANSUhEUgAAAGYAAABmAQMAAAADEXYhAAAAAXNSR0IArs4c6QAAAARnQU1BA'
            b'ACxjwv8YQUAAAAGUExURQwMDPz8/O1fsT8AAAAJcEhZcwAACxMAAAsTAQCanBgAAAFoSURBVD'
            b'jLhdTBagIxEADQbPeQW3PpsZgfEfNbPUizxUNPZf9A/6RELAi9+Ac14sGjEaFGmma6WpqZFHe'
            b'dQ+CRwDCZSRiQCNd1gGWmCdEa6lbN4DkTJ3ppzqImmSTs2hSlplLaoYLSnkp5TfWA8urOK5Qu'
            b'idwjDxI1LIjskA0F0X0fZULscdQRiKpv6JUooCoAVJHEIA6SItNNfpQyniUVanRMCuVY7CudF'
            b'CUkeR4UGHVR7lSrkX8STa1JVgTRLEmv/CvJiPdyY3nSW8GJLBMoXjFu/mTZKcRFubPkRfmzVI'
            b'dS7R2KrGI3eIPMsluGN//JxqQPe/ZRkI5VkfbPEE3BACey/0TmBWxsk9OOTp1yHuXlypFp5Tu'
            b'DCmJlyZSLtUFFvraAEnODAlGvqMSUiEv6Gms5y0T3FnJONJ9siLbLBdViS3SoqX4/lCRJFVUm'
            b'TRV0+14cZOpnGVimItNTplGmWYc2HYJrgvAD4KZY2kIHv7MAAAAASUVORK5CYII='
        )

        await send_email(
            "Test topic",
            "<p>Test message</p>",
            [],
            from_email="",
            attachments=[MIMEImage(image_raw_data)],
        )
