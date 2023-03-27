## Installation

Get latest version:

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

## Setting-up

See [docs/howto/setup](./setup/README.md)

## Deployment

See [docs/howto/deploy](./deploy/README.md)
