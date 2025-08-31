from argparse import ArgumentParser
from functools import lru_cache

from core.console import CONSOLE, make_title, input_subject, input_names, input_crl_server_info
from core.editors import RootCA, IntimidateCA, ServerCertsEditor, make_server_pki

from core.models import Args
from logging_settings import LoggingSettings, setup_logging
from rich_argparse import RichHelpFormatter

from core.settings import settings


def get_args() -> Args:
    parser = ArgumentParser(
        prog="G-PKI",
        description="🚀 Generate PKI for your server",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "--root_ca_c",
        type=str,
        help="Root CA: Country",
        required=False,
    )
    parser.add_argument(
        "--root_ca_o",
        type=str,
        help="Root CA: Organization",
        required=False,
    )
    parser.add_argument(
        "--root_ca_cn",
        type=str,
        help="Root CA: Common Name",
        required=False,
    )
    parser.add_argument(
        "--intermediate_ca_c",
        type=str,
        help="Intermediate CA: Country",
        required=False,
    )
    parser.add_argument(
        "--intermediate_ca_o",
        type=str,
        help="Intermediate CA: Organization",
        required=False,
    )
    parser.add_argument(
        "--intermediate_ca_cn",
        type=str,
        help="Intermediate CA: Common Name",
        required=False,
    )
    parser.add_argument(
        "--server_cn",
        type=str,
        help="Server: Common Name",
        required=False,
    )
    parser.add_argument(
        "--server_san",
        type=str,
        help="Server: Subject Alternative Names",
        required=False,
    )
    parser.add_argument(
        "--crl_server_host",
        type=str,
        help="SRL server hostname",
        required=False,
    )
    parser.add_argument(
        "--crl_server_port",
        type=int,
        help="SRL server port",
        required=False,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode",
        required=False,
    )

    return Args.model_validate(vars(parser.parse_args()))


@lru_cache
def logging_config(debug: bool = False) -> dict:
    log_settings = LoggingSettings(
        rotating_file_handler=True,
        add_logger_name=False,
        loglevel="DEBUG" if debug else "WARNING",
        logs_dir=settings.base_dir.parent / "logs",
        filename="g-pki.log",
    )
    return setup_logging(log_settings)


def gen_full_pki(args: Args) -> None:
    CONSOLE.print(f"[bold cyan]{make_title("Root CA")}[/bold cyan]")

    root_ca = RootCA()
    root_ca.load_private_key()
    root_ca.load_certificate()

    if not root_ca.private_key:
        root_ca.gen_private_key()

        CONSOLE.print(
            f"[bold green]Generated Root CA private key => {root_ca.private_key_file.absolute().as_posix()!r}[/bold green]"
        )
    else:
        CONSOLE.print(
            f"[green]Loaded Root CA private key <= {root_ca.private_key_file.absolute().as_posix()!r}[/green]"
        )

    if not root_ca.certificate:
        root_ca.make_subject(
            **input_subject(
                args.root_ca_c,
                args.root_ca_o,
                args.root_ca_cn,
            ).model_dump()
        )
        root_ca.make_certificate()

        CONSOLE.print(
            f"[bold green]Generated Root CA certificate => {root_ca.certificate_file.absolute().as_posix()!r}[/bold green]"
        )

    else:
        CONSOLE.print(
            f"[green]Loaded Root CA certificate <= {root_ca.certificate_file.absolute().as_posix()!r}[/green]"
        )

    CONSOLE.print(f"[bold cyan]{make_title("Intermediate CA")}[/bold cyan]")

    intermediate_ca = IntimidateCA()
    intermediate_ca.load_private_key()
    intermediate_ca.load_certificate()

    if not intermediate_ca.private_key:
        intermediate_ca.gen_private_key()

        CONSOLE.print(
            f"[bold green]Generated Intermediate CA private key => {intermediate_ca.private_key_file.absolute().as_posix()!r}[/bold green]"
        )
    else:
        CONSOLE.print(
            f"[green]Loaded Intermediate CA private key <= {intermediate_ca.private_key_file.absolute().as_posix()!r}[/green]"
        )

    if not intermediate_ca.certificate:
        intermediate_ca.make_subject(
            **input_subject(
                args.intermediate_ca_c,
                args.intermediate_ca_o,
                args.intermediate_ca_cn,
            ).model_dump()
        )
        intermediate_ca.make_certificate(
            root_ca.private_key,
            root_ca.certificate,
        )
        CONSOLE.print(
            f"[bold green]Generated Intermediate CA certificate => {intermediate_ca.certificate_file.absolute().as_posix()!r}[/bold green]"
        )

    else:
        CONSOLE.print(
            f"[green]Loaded Intermediate CA certificate <= {intermediate_ca.certificate_file.absolute().as_posix()!r}[/green]"
        )

    CONSOLE.print(f"[bold cyan]{make_title("Server")}[/bold cyan]")

    server_certs_editor = ServerCertsEditor(intermediate_ca)

    common_name, alt_names = input_names(args.server_cn, args.server_san)
    crl_server_host, crl_server_port = input_crl_server_info(
        args.crl_server_host, args.crl_server_port
    )

    (private_key, private_key_file), (certificate, certificate_file) = make_server_pki(
        server_certs_editor,
        common_name,
        alt_names,
        crl_server_host,
        crl_server_port,
    )
    CONSOLE.print(
        f"[bold green]Generated {common_name!r} private key => {private_key_file.absolute().as_posix()!r}[/bold green]"
    )
    CONSOLE.print(
        f"[bold green]Generated {common_name!r} certificate => {certificate_file.absolute().as_posix()!r}[/bold green]"
    )
