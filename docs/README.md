## starlette_web documentation

starlette_web brings a number of features atop base starlette.

### Common features

- ORM (via SQLAlchemy.ORM)
- Admin panel (via `starlette_admin`)
- Extended support for OpenAPI (via apispec)
- Caches
- Pub-sub mechanism (based on `encode/broadcaster`)
- Email senders (based on `django.common.mail`)
- Management commands (based on django management commands)
- Base HTTP and WebSocket endpoints

### Contrib modules

- Redis support
- Authorization (based on `django.contrib.auth`)
- Constance (based on `django-constance`)
- Periodic task scheduler (based on `django-crontab`), 
  that uses OS native scheduling mechanism (POSIX crontab, Windows Task Scheduler 2.0)

### Planned features

- See github issues/milestones for planned features: 
  https://github.com/dolamroth/starlette-web/milestones

### Not planned features

- FileField, ImageField (see [docs/notes](./notes/orm_filefield_challenges.md) for explanation)

## Additional notes, articles and links

- [docs/notes](./notes) section contains various notes and best practices
- See blog of Nathaniel Smith for articles about structured concurrency: https://vorpus.org/blog/archives.html
- See GINO docs for articles about using asynchronous ORM: https://python-gino.org/docs/en/1.0/explanation/async.html
- [Project wiki](https://github.com/dolamroth/starlette-web/wiki) also has an unsorted bunch of 
  articles/discussions on various topics
