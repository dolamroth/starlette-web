## starlette_web documentation

starlette_web brings a number of features atop base starlette.

### Common features

- ORM (via SQLAlchemy.ORM), model helper methods
- Admin panel (via [starlette_admin](https://github.com/jowilf/starlette-admin))
- [Caches](./common/caching.md)
- [Pub-sub channels](./common/channels.md) (based on `encode/broadcaster`)
- Email senders
- [Management commands](./common/management_commands.md)
- Base [HTTP](./common/http.md) and [WebSocket](./common/websockets.md) endpoints
- [Authentication backend and permission classes](./common/authorization_permissions.md)
  (based on `djangorestframework`)
- [Extended support for OpenAPI](./contrib/apispec.md)

### Contrib modules

- Redis support
- Authorization (based on `django.contrib.auth`)
- [Constance](./contrib/constance.md) (based on `django-constance`)
- [Periodic task scheduler](./contrib/scheduler.md) (based on `django-crontab`), 
  that uses OS native scheduling mechanism (POSIX crontab, Windows Task Scheduler 2.0).
  For additional scheduling schemes, please [see docs](./notes/scheduling_tasks.md).

### Planned features

- See github issues/milestones for planned features: 
  https://github.com/dolamroth/starlette-web/milestones

### Not planned features

- FileField, ImageField (see [docs/notes](./notes/orm_filefield_challenges.md) for explanation)

## Additional notes, articles and links

- [docs/notes](./notes) section contains various notes and best practices
- See blog of Nathaniel Smith for articles about structured concurrency: https://vorpus.org/blog/archives.html
- See GINO docs for articles about [asynchronous programming](https://python-gino.org/docs/en/1.0/explanation/async.html),
  and [asynchronous ORM](https://python-gino.org/docs/en/1.0/explanation/why.html)
- [Project wiki](https://github.com/dolamroth/starlette-web/wiki) also has an unsorted bunch of 
  articles/discussions on various topics
