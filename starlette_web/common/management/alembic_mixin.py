import tempfile
from typing import Tuple

import anyio
import chardet


class AlembicMixin:
    @staticmethod
    async def run_alembic_main(args) -> Tuple[str, str]:
        with tempfile.NamedTemporaryFile() as stdout:
            with tempfile.NamedTemporaryFile() as stderr:
                async with await anyio.open_process(
                    ["alembic"] + args,
                    stdout=stdout,
                    stderr=stderr,
                ) as process:
                    await process.wait()

                stdout.seek(0)
                stderr.seek(0)

                out, err = stdout.read(), stderr.read()
                out_encoding = chardet.detect(out)["encoding"]
                err_encoding = chardet.detect(err)["encoding"]

                if out_encoding is None:
                    out = ""
                else:
                    out = out.decode(out_encoding)

                if err_encoding is None:
                    err = ""
                else:
                    err = err.decode(err_encoding)

                return out, err
