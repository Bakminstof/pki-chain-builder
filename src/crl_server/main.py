from os import getcwd
from sys import path

if getcwd() not in path:
    path.append(getcwd())

from crl_server.utils import get_args, startup_server, logging_config


def main() -> None:
    args = get_args()
    logging_config(args.debug)

    startup_server(args)


if __name__ == "__main__":
    main()
