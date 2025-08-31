from datetime import datetime, UTC, timedelta
from logging import getLogger
from pathlib import Path

from cryptography.hazmat.backends.openssl.backend import Backend
from cryptography.x509 import (
    CertificateRevocationListBuilder,
    CertificateRevocationList,
    Certificate,
    RevokedCertificateBuilder,
)
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from core.models import SerialCertsInfoModel, CertInfo

from cryptography.x509.base import _AllowedHashTypes
from core.io_utils import load_json_as_model, write_model_as_json, write_crl, load_crl

logger = getLogger(__name__)


class SerialInfoHelper:
    def __init__(self, serial_file: Path) -> None:
        self.serial_file = serial_file

        self.serial_info: SerialCertsInfoModel | None = None

    def load_serial_file(self) -> None:
        if not self.serial_file.exists():
            self.serial_info = SerialCertsInfoModel()
            self.write_serial_file()

        self.serial_info = load_json_as_model(self.serial_file, SerialCertsInfoModel)

        logger.debug(
            "Loaded serial info: %r",
            self.serial_file.absolute().as_posix(),
        )

    def write_serial_file(self) -> None:
        write_model_as_json(self.serial_file, self.serial_info)

        logger.debug(
            "Written serial info: %r",
            self.serial_file.absolute().as_posix(),
        )

    @property
    def next_serial_num(self) -> int:
        if not self.serial_info:
            self.load_serial_file()

        serial_numbers = self.serial_info.data.keys()
        current_max_serial = max(serial_numbers) if serial_numbers else 0
        return current_max_serial + 1

    def save_to_serial_file(self, serial_num: int, sha_256_fingerprint: str) -> None:
        info = CertInfo(sha_256_fingerprint=sha_256_fingerprint)
        self.serial_info.data[serial_num] = info

        self.write_serial_file()
        self.load_serial_file()


class CRLHelper:
    def __init__(
        self,
        crl_file: Path,
        crl_update_period_days: int,
        hash_algorithm: _AllowedHashTypes,
        backend: Backend,
    ) -> None:
        self.crl_file = crl_file
        self.crl_update_period_days = crl_update_period_days
        self.backend = backend
        self.hash_algorithm = hash_algorithm

        self.private_key: PrivateKeyTypes | None = None
        self.certificate: Certificate | None = None
        self.crl: CertificateRevocationList | None = None

    def load_crl(self) -> CertificateRevocationList | None:
        if not self.crl_file.exists():
            return None

        self.crl = load_crl(self.crl_file, self.backend)

        logger.debug(
            "Loaded CRL: %r",
            self.crl_file.absolute().as_posix(),
        )

        return self.crl

    def generate_crl(self, revoked_serials: list[int]) -> CertificateRevocationList:
        if not self.certificate:
            logger.error("[%s] Certificate is not found", self)
            exit(1)

        if not self.private_key:
            logger.error("[%s] Private key is not found", self)
            exit(1)

        builder = CertificateRevocationListBuilder()
        builder = builder.issuer_name(self.certificate.subject)
        builder = builder.last_update(datetime.now(UTC) - timedelta(days=1))
        builder = builder.next_update(
            datetime.now(UTC) + timedelta(days=self.crl_update_period_days)
        )

        for serial in revoked_serials:
            revoked_cert = (
                RevokedCertificateBuilder()
                .serial_number(serial)
                .revocation_date(datetime.now(UTC))
                .build()
            )
            builder = builder.add_revoked_certificate(revoked_cert)

            logger.info("Revoked certificate with serial: %d", serial)

        self.crl = builder.sign(self.private_key, self.hash_algorithm)
        write_crl(self.crl, self.crl_file)

        logger.debug(
            "Generated CRL: %r",
            self.crl_file.absolute().as_posix(),
        )

        return self.crl
