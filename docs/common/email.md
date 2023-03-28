## Sending email

`starlette_web` allows sending emails via `starlette_web.common.email`.
**Only emails with html content are supported.**


```python
from starlette_web.common.email import send_email

subject = "Test subject"
html_content = "Test message"
recipients_list = ["test@gmail.com"]
from_email = "from@gmail.com"
await send_email(subject, html_content, recipients_list, from_email)
```

### Setting up

In your settings file define setting `EMAIL_SENDER`:

```python
EMAIL_SENDER = {
    "BACKEND": "starlette_web.common.email.smtp.SMTPEmailSender",
    "OPTIONS": {
        "hostname": "smtp.server.com",
        "port": 443,
        "username": "email@gmail.com",
        "password": "password",
        "use_tls": True,
    }
}
```

The email sender is lazily inited upon calling `send_email`, 
so you may leave this setting unfilled if you don't want to use it.

### Manual backend management

You may want to define email backend on the fly, instead on relying built-in mechanisms:

```python
from starlette_web.common.email.smtp import SMTPEmailSender

sender_options = {
    "hostname": "smtp.server.com",
    "port": 443,
    "username": "email@gmail.com",
    "password": "password",
    "use_tls": True,
}

subject = "Test subject"
html_content = "Test message"
recipients_list = ["test@gmail.com"]
from_email = "from@gmail.com"

async with SMTPEmailSender(**sender_options) as sender:
    await sender.send_email(subject, html_content, recipients_list, from_email)
```

### Implementations 

A default `SMTP` implementation is provided via `starlette_web.common.email.smtp.SMTPEmailSender`.
It uses `aiosmtplib` underneath. 
For list of possible options, please see input arguments for `aiosmtplib.api.send`.

For custom implementation, subclass `starlette_web.common.email.base_sender.BaseEmailSender`.
