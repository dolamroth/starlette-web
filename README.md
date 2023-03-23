## starlette-web

`starlette-web` is a native-asynchronous web-framework, based on Starlette and inspired by Django and its ecosystem.
It aims to provide most of the relevant features of Django in async-all-the-way setting.

Its priorities, from most important to least important, are as follows:

- **Providing a single ecosystem** - all parts of framework are aimed to work well together and follow same ideas. 
  In a way, this goes against idea of mini-frameworks like Starlette, which favor a lot of contrib plug-ins, 
  written by different authors.
- **Robustness** - `starlette-web` is written with **anyio** and tries to follow principles of structured concurrency.
- **Feature completeness** - while the aim is not to cover all the Django ecosystem 
  (especially, because a lot of it is legacy), many useful libraries are included.
- **Cross-platform support** - most of the features are supported for both POSIX and Windows systems. 
  However, a number of contrib modules aim specifically at certain OS, and obviously it's mostly Linux. 
- **Speed** - while framework is being used in multiple projects without speed issues, it is not properly benchmarked.
  Probably, it is slower than all other async Python frameworks, though not by a large amount.

starlette-web uses **SQLAlchemy** as its database toolkit and ORM.

The framework is not well suited for novice users. It assumes prior knowledge of Django and async development in Python.

## Examples of usage

A sample instruction to start a new project is given in `docs/howto/startup` section. 
See tests for more examples of usage.

## Code borrowing

starlette-web borrows/adopts a lot of code from other open-source Python libraries. 
List of libraries is given in the `docs/licences` section, with links to repositories and licences.
