import sys

from .server import serve


def main() -> None:
    raise SystemExit(serve(sys.stdin.buffer, sys.stdout.buffer, sys.stderr))


if __name__ == "__main__":
    main()
