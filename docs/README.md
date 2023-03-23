## starlette_web documentation

starlette_web brings a number of features atop base starlette.

### Common features

- ORM (via SQLAlchemy.ORM)
- Admin panel (via `starlette_admin`)
- Caches
- Pub-sub mechanism
- Email senders (based on `django.common.mail`)
- File storages
- Management commands (based on django management commands)
- Base HTTP and WebSocket endpoints

### Contrib modules

- Redis support
- Authorization (based on `django.contrib.auth`)
- Constance (based on `django-constance`)
- Periodic task scheduler (based on `django-crontab`), 
  that uses OS native scheduling mechanism (crontab, Windows Task Scheduler 2.0)
