## Installation

Get latest version:

```bash
pip install starlette-web
pip install starlette-web[postgres,redis,apispec,auth,scheduler]
pip install starlette-web[all]
```

starlette-web has a lot of extra dependencies, most of which correspond to contrib modules:
- apispec
- admin
- auth
- mqtt
- postgres
- redis
- scheduler
- deploy
- develop
- testing

All but "development" and "testing" are recommended for production.

## Setting-up

See [docs/howto/setup](./setup/README.md)

## Running & Deployment

See [docs/howto/deploy](./deploy/README.md)
