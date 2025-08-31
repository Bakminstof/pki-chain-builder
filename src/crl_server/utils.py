from argparse import ArgumentParser
from datetime import datetime, UTC
from functools import lru_cache
from logging import getLogger
from pathlib import Path
from threading import Thread
from time import sleep

from bottle import Bottle, Route
from crl_server.models import Args
from logging_settings import LoggingSettings, setup_logging
from rich_argparse import RichHelpFormatter
from cryptography.x509 import Certificate

from core.editors import IntimidateCA
from core.models import CertInfo
from core.settings import settings
from core.io_utils import load_certificate
from crl_server.routes import crl

from crl_server.app import APP_NAME

logger = getLogger(__name__)


def get_args() -> Args:
    parser = ArgumentParser(
        prog="CRL server",
        description="🚀 Start simple CRL server",
        formatter_class=RichHelpFormatter,
    )

    parser.add_argument(
        "--host",
        type=str,
        help=f"Host. Default: {settings.intermediate_ca.crl_server.host}",
        required=False,
        default=settings.intermediate_ca.crl_server.host,
    )
    parser.add_argument(
        "--port",
        type=int,
        help=f"Port. Default: {settings.intermediate_ca.crl_server.port}",
        required=False,
        default=settings.intermediate_ca.crl_server.port,
    )
    parser.add_argument(
        "--crl-file",
        type=Path,
        help=f"CRL file path. Default: {settings.intermediate_ca.crl_file.absolute().as_posix()}",
        required=False,
        default=settings.intermediate_ca.crl_file,
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
        filename="crl-server.log",
    )
    return setup_logging(log_settings)


def startup_server(args: Args) -> None:
    intimidate_ca = IntimidateCA()
    intimidate_ca.load_certificate()
    intimidate_ca.load_private_key()

    run_server(intimidate_ca, args.host, args.port, args.crl_file)


def run_server(
    intimidate_ca: IntimidateCA,
    host: str = settings.intermediate_ca.crl_server.host,
    port: int = settings.intermediate_ca.crl_server.port,
    crl_file: Path = settings.intermediate_ca.crl_file,
) -> None:
    settings.intermediate_ca.crl_server.host = host
    settings.intermediate_ca.crl_server.port = port
    settings.intermediate_ca.crl_file = crl_file

    app = Bottle()

    app.add_route(Route(app, settings.intermediate_ca.crl_server.route, "GET", crl))

    logger.warning("Starting %s", settings.intermediate_ca.crl_server.url)

    worker = Thread(target=app.run, kwargs={"host": host, "port": port}, daemon=True)
    worker.start()

    try:
        watch_revoked_certs_dir(intimidate_ca)
    except KeyboardInterrupt:
        logger.warning("Shutting down")


def update_revoked_status_in_serial(
    certs_data: dict[int, Certificate],
    intimidate_ca: IntimidateCA,
    revoked_serials: list[int],
    timestamp: float,
) -> None:
    intimidate_ca.load_serial_file()

    for num in revoked_serials:
        cert_info = intimidate_ca.serial_info.data.get(num)

        if cert_info is None:
            cert_info = CertInfo(
                sha_256_fingerprint=certs_data[num].fingerprint(intimidate_ca.hash_algorithm).hex(),
            )
            intimidate_ca.serial_info.data[num] = cert_info

        cert_info.revoked = True
        cert_info.revocation_timestamp = timestamp

    intimidate_ca.write_serial_file()


def check_revoked_certs_dir(
    intimidate_ca: IntimidateCA,
    revoked_certs_dir: Path = settings.intermediate_ca.revoked_certs_dir,
) -> None:
    revoked_serials: list[int] = []

    certs_data: dict[int, Certificate] = {}

    for item in revoked_certs_dir.iterdir():
        if item.is_dir():
            continue

        cert = None

        try:
            cert = load_certificate(item, intimidate_ca.backend)
        except ValueError as e:
            logger.error(
                "[%s] Failed to load certificate: %r, %s",
                APP_NAME,
                item.absolute().as_posix(),
                e,
            )

        if cert is None:
            continue

        info = intimidate_ca.serial_info.data.get(cert.serial_number)

        if info is None or info.revoked == False:
            certs_data[cert.serial_number] = cert
            revoked_serials.append(cert.serial_number)

    if not intimidate_ca.crl or datetime.now(UTC) >= intimidate_ca.crl.next_update_utc:
        intimidate_ca.generate_crl(revoked_serials)

        try:
            update_revoked_status_in_serial(
                certs_data,
                intimidate_ca,
                revoked_serials,
                datetime.now(UTC).timestamp(),
            )
        except KeyError as e:
            logger.error("[%s] Failed to update revoked status: %s", APP_NAME, e)
            intimidate_ca.write_serial_file()


def watch_revoked_certs_dir(
    intimidate_ca: IntimidateCA,
    revoked_certs_dir: Path = settings.intermediate_ca.revoked_certs_dir,
    refresh_revoked_dir_time_seconds: int = settings.intermediate_ca.crl_server.refresh_revoked_dir_time_seconds,
) -> None:
    if not revoked_certs_dir.exists():
        logger.error(
            "[%s] Revoked certs dir not found: %r",
            APP_NAME,
            revoked_certs_dir.absolute().as_posix(),
        )
        exit(1)

    intimidate_ca.load_serial_file()
    intimidate_ca.load_crl()

    while True:
        check_revoked_certs_dir(intimidate_ca, revoked_certs_dir)

        sleep(refresh_revoked_dir_time_seconds)
