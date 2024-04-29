import argparse


def parse_startapp_known_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", type=str, default=None, required=False)
    parser.add_argument(
        "--skip_checks",
        const=True,
        default=False,
        action="store_const",
        required=False,
    )
    parser.add_argument(
        "--use_pool",
        const=True,
        default=False,
        action="store_const",
        required=False,
    )
    parser.add_argument("--host", default="127.0.0.1", type=str, required=False)
    parser.add_argument("--port", default=8000, type=int, required=False)
    args, _ = parser.parse_known_args()
    return args
