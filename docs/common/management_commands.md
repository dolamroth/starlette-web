## Management commands

Management commands copy the [Django implementation](https://docs.djangoproject.com/en/4.1/howto/custom-management-commands/), 
except that in `starlette_web` they have async handlers. They are designed to run isolated piece of execution
and thus do not return.

## Custom commands and usage

Any management command must be defined in `%app_dir%/management/command/%command_name%.py`.
The file must define a class named `Command`, subclassed from `starlette_web.common.management.base.BaseCommand`.
In order to use management commands, you have to add a respective application to `settings.INSTALLED_APPS`.

You may then run command with its `%command_name%`: 

From code

```python3

from starlette_web.common.management.base import call_command

await call_command("test_parser", ["1", "2", "3", "--sum"])
```

From command line

```bash
python command.py test_parser 1 2 3 --sum
```

## Available commands

- startproject
- startapp
- collectstatic

## Notes

In order to use database connection, in command method `handle` create session like this.

```python3
async with self.app.sessionmaker() as session:
    ...
```

By default, sessionmaker in commands uses `NoPool`-strategy to manage connection pool, meaning that
it will open new connection every time you call sessionmaker and close it immediately after usage.
To vary this behavior, set `settings.DB_USE_CONNECTION_POOL_FOR_MANAGEMENT_COMMANDS`.

Beware, that any `call_command` creates a new instance of application.

Management commands respect `lifespan` wrapper of Starlette application. 
The state of lifespan wrapper is available as `options["_lifespan_state"]`.

## Examples

See `starlette_web.tests.management.commands` for more examples of usage.
