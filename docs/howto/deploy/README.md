After setting up the project, there will be file `asgi.py` containing the variable `app`.
`app` is the instance of [ASGI 3 application](https://asgi.readthedocs.io/en/latest/specs/main.html)
and, as such, may be run with any Asgi-compliant server.

### Running manually

`app` can be run manually with `uvicorn`. Default `asgi.py` already provides the relevant code:

```python3
import uvicorn

from starlette_web.common.app import get_app

app = get_app()
uvicorn.run(app, host="127.0.0.1", port=80)
```

### Deployment

It is recommended to deploy on Linux (Ubuntu >= 20.04) with **nginx** and **gunicorn**.
Recommended setup includes **PostgreSQL** as database, and **Redis** as cache, 
cross-process synchronization mechanism and pub-sub server.

[Sample config for nginx](./nginx.conf) as well as 
[sample systemd service for gunicorn](gunicorn.service) are provided.

### Settings

Environment variable `STARLETTE_SETTINGS_MODULE` must be set and point to settings file.
By default, it is `core.settings` (resolving from project root).

### Additional notes

- If you don't need saving Redis data on disk, consider disabling persistence for extra speed: 
  https://stackoverflow.com/a/28786320
- If you use PostgreSQL and many workers for `starlette_web`, consider setting up a pgbouncer
- If you have high RPS, consider setting `use_epoll` for nginx:
  https://gist.github.com/DanielTheFirst/837210#file-nginx-conf-L21
