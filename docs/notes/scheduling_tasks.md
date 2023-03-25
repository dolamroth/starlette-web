## Scheduling of delayed and periodic tasks

Sometimes, you would like to execute a separate non-blocking task after user's request.
There are multiple built-ins to do that:

- Native `starlette` has BackgroundTask for HttpEndpoint, which accept any awaitables to be executed right 
  after user's request. This is well-suited for short async task like sending SMS, emails or queries to outer APIs.
  Spawning short processes within background task is possible with `anyio.to_process`.
- `starlette_web` allows you to spawn background tasks in WebsocketEndpoint, bounding them to parent `anyio.TaskGroup`.
  These are intended as background tasks with the same lifespan, as websocket connection, i.e. for listeners/publishers.
- `starlette_web` also provides a `contrib.scheduler` module to allow running periodic tasks with the help of OS builtin
  scheduler. Implementations for POSIX crontab and Windows Task Scheduler 2.0 are provided.

There are also outer libraries, which provide different options to run scheduled tasks.

### [Celery](https://github.com/celery/celery) 

- Useful for task chains with complicated logic (chains, chords) 
  or if you need retries, acknowledgement, task cancelling and such. 
- Only applicable for synchronous tasks
- May run in multiprocess, threading and eventlet modes.
- Works with Redis and RabbitMQ, allows sharding.
- It is practically the only viable option, if you want to run tens of thousands tasks per second, 
  or if you need complicated logging, task monitoring and such.
- **Recommended** overall.

### [huey](https://github.com/coleifer/huey) 

- A simpler version of celery. 
- Does not provide chains and chords, but does provide acknowledgement, retries, cancelling.
- Only applicable for synchronous tasks.
- May run in multiprocess, threading and greenlet modes.
- Has issues with multiprocess mode on Windows, which are "won't do" by the author.
- Has builtin workers for SQLite, file backend, which is good for small applications with little dependencies.
- **Partially recommended**, has limited applicability.

### [APScheduler](https://github.com/agronholm/apscheduler) 
- A **recommended** way to run asynchronous delayed or periodic tasks, 
  if you need to run one-off or periodic/delayed async tasks.
- Needs extension to support retries/cancelling.
- Supports database storages, Redis and some other.
- Works with anyio.

**Note**: If you are going to use it, note that starlette supports lifespan tasks since `0.26.0`,
so you don't have to add middleware as per docs: https://apscheduler.readthedocs.io/en/master/integrations.html
Simply inherit `starlette_web.common.app.BaseStarletteApplication` and re-define method `get_lifespan`.

### [aiotasks](https://github.com/cr0hn/aiotasks)
- Celery-like job queue for async tasks.
- Has limited functionality.
- Works with asyncio.
- **Not recommended**, has not got releases since 2017.

### [celery-pool-asyncio](https://github.com/kai3341/celery-pool-asyncio)
- Monkey-patches celery to use a separate pool class, which accepts async functions as tasks. 
  Other celery features remain. 
- Original repository frozen, the latest release from fork is dated May 2020.
- **Not recommended** unless you know what you are doing.

### Custom task broker with ThreadPool/ProcessPool
- This approach has no drawbacks :)
- In case of multiprocessing, you may consider using a [fork with better serialization](https://github.com/uqfoundation/multiprocess)
