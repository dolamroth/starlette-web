## Setting-up the application

After you have installed `starlette-web` package, an util `starlette-web-admin` is installed to virtual environment.

To start project, execute:

```bash
starlette-web-admin startproject %project_name%
cd %project_name%
```

At this point, there should be a directory `%project_name%`, containing directory `core`, alembic files, `.env`,
`command.py`, `asgi.py`. 
**This is your project root.** 
Execute all commands from here.
Directory `core` is central to your application and contains `settings.py` file.

### Settings

Environment variable `STARLETTE_SETTINGS_MODULE` must be set with string value, 
that points to the import location `settings.py`. By default, it is `core.settings` 
(resolving from project root).

```bash
export STARLETTE_SETTINGS_MODULE=core.settings  # Linux
set STARLETTE_SETTINGS_MODULE=core.settings  # Windows
```

### Environment variables

By default, `settings.py` file fetches some config from `.env` file. 
Example files `.env` and `.env.template` will be created upon running `startproject`.
**Don't forget to add `.env` to `.gitignore`!**

### Configuring database

By default, `settings.py` contains options for `postgresql+asyncpg`.
The main setting is `DATABASE_DSN`, which typically has the following format:

```python
DATABASE_DSN = "{driver}://{username}:{password}@{host}:{port}/{database}"
```

Adjust this parameter to your preferences.

At this point, `starlette_web` **only supports setting up a single database**.
*Issue on multiple databases support is due to version 0.4.*

`settings.DATABASE` is required as to version `0.1.x`, but will be deprecated by `0.2`.

### Setting database migrations

Database migrations are managed via `alembic`, this is a contrib migrations library for SQLAlchemy.
After running `startproject`, in project root there will be `alembic.ini` file.
Open it and edit setting `sqlalchemy.url`, setting it to the same value, as `settings.DATABASE_DSN`.

```bash
alembic revision -c "%new_revision_name%" --autogenerate  # analog of django makemigrations
alembic upgrade head  # analog of django migrate
alembic downgrade -1 # backwards migration
```

Alembic migrations have multiple notable differences, compared to Django ORM migrations:

- Only SQL-related field options are moved to migrations, not all like in Django ORM;
- Alembic autogenerate creates new migration file every time you run the command, even if no changes should be made;
- In general, alembic migrations require more manual configuration, but are more powerful, than Django migrations.

### Managing applications

Run the following command to instantiate a new app (application module in Django terminology):

```bash
python command.py startapp %appname%
```

A newly created application contains `apps.py`, `models.py`, `admin.py`, `views.py`, `routes.py`.

- `apps.py` is a required file, if you add your application to `settings.INSTALLED_APPS`. 
  It contains code for application initialization and checks on startup.
  It also allows to configure, which other applications are preliminary requirements for this one.
- `models.py` is file, where you define database models. It is introspected by application 
  manager for subclasses of ModelBase.
- `admin.py` is file, where you define `AdminView`'s for admin panel. It is introspected, 
  if you have installed `starlette_web.contrib.admin`.
- `views.py` and `routes.py` are files, in which you define your endpoints and routing.
