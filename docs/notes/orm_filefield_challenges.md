## A note on ORM FileField

Django ORM provides a model.FileField class to allow user to store links to files in database, 
while implicitly manage files in selected file storage. This approach, however, has multiple caveats:

- The whole mechanism relies on database triggers, so the ORM of choice must support them. 
  Django ORM only emits signals on instance save and does not trigger, whenever bulk operations are executed, 
  which makes implicit managing of files fallible to errors.
- There exist multiple strategies of what to do with deprecated file links. 
  By default, Django leaves related files on disk, 
  so you have to implement a separate object save/Manager, 
  if you want to delete them from disk upon link deletion.
- To be simple and stable, this approach requires specific conditions to be met. 
  In particular, autocommit mode for ORM is strongly preferred to make all operations atomic and simpler to manage. 
  Saving files on disk should be atomic operation without mid-interrupting, 
  or the intermediate representation should be easily disposable.

As for the last point, default Django settings do just that. By default, framework uses `InMemoryUploadHandler`, 
which means that in case of interruption files will be safely discarded. Furthermore, autocommit is used by default
in Django ORM.

As for non-autocommit, libraries that take a daunting task to support FileField, do this in a 
[very elaborate manner](https://github.com/jowilf/sqlalchemy-file/blob/main/sqlalchemy_file/types.py). 
All such known libraries are also synchronous: 
- https://github.com/jowilf/sqlalchemy-file
- https://github.com/pylover/sqlalchemy-media

In case of async framework, however, everything is a bit more difficult.

- Async reading/writing in chunks should be supported. 
  Apparently, not all storage/filefield libraries support that, though Django does.
- It is desired to have a cancellation mechanism, since async operations, 
  including those that manage files, can be cancelled (i.e. by closing websocket connection).
- Asynchronous database events are not widely supported. In particular, SQLAlchemy ORM does not yet have them, though
  it allows to imitate them by listening to sync events from within spawned greenlet. It is not a stable feature, 
  and sqlalchemy-file/-media do not support it yet.
  - https://github.com/sqlalchemy/sqlalchemy/issues/5905
  - https://github.com/sqlalchemy/sqlalchemy/discussions/7152
  - https://github.com/sqlalchemy/sqlalchemy/discussions/6594

Considering all that, `starlette_web` does not support FileFields for the time being, 
and instead aims to provide an easy-to-use API for async file storages (*upcoming feature in 0.2*).
