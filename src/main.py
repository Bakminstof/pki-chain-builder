from os import getcwd
from sys import path

if getcwd() not in path:
    path.append(getcwd())

from core.console import CONSOLE
from core.utils import gen_full_pki, get_args, logging_config


def main() -> None:
    args = get_args()
    logging_config(args.debug)

    try:
        gen_full_pki(args)
    except KeyboardInterrupt:
        CONSOLE.print("\n[bold yellow]> User canceled[/bold yellow]")


if __name__ == "__main__":
    main()
