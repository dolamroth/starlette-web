## Deployment

It is recommended to deploy on Linux (Ubuntu >= 20.04) with **nginx** and **gunicorn**.
Recommended setup includes **PostgreSQL** as database, and **Redis** as cache, 
cross-process synchronization mechanism and pub-sub server.

[Sample config for nginx](./nginx.conf) as well as 
[sample systemd service for gunicorn](gunicorn.service) are provided.

### Additional notes

- If you don't need saving Redis data on disk, consider disabling persistence for extra speed: 
  https://stackoverflow.com/a/28786320
- If you use PostgreSQL and many workers for `starlette_web`, consider setting up a pgbouncer
- If you have high RPS, consider setting `use_epoll` for nginx:
  https://gist.github.com/DanielTheFirst/837210#file-nginx-conf-L21
