## Installation

Latest version:

```bash
python -m pip install https://github.com/dolamroth/starlette-web/archive/refs/heads/main.zip#egg=starlette_web
python -m pip install https://github.com/dolamroth/starlette-web/archive/refs/heads/main.zip#egg=starlette_web[postgres,redis]
```

Or download archive from https://github.com/dolamroth/starlette-web and install via

```bash
python -m pip install .
python -m pip install .[postgres,redis]
```

starlette-web has a lot of extra dependencies, most of which correspond to contrib modules:
- apispec
- admin
- auth
- postgres
- redis
- scheduler
- deploy
- develop
- testing

All but "development" and "testing" are recommended for production.

## Setup

### TODO:

## Deployment

See [docs/howto/deploy](./deploy/README.md)

## Additional notes

- If you don't need saving Redis data on disk, consider disabling persistence for extra speed: 
  https://stackoverflow.com/a/28786320
- If you use PostgreSQL and many workers for `starlette_web`, consider setting up a pgbouncer
- If you have high RPS, consider setting `use_epoll` for nginx:
  https://gist.github.com/DanielTheFirst/837210#file-nginx-conf-L21
