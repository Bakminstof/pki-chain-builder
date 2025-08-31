from datetime import datetime, UTC, timedelta
from ipaddress import IPv4Address
from logging import getLogger
from pathlib import Path
from re import compile as re_compile, match as re_match
from typing import Iterable

from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.backends.openssl.backend import Backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.x509 import (
    CRLDistributionPoints,
    DistributionPoint,
    UniformResourceIdentifier,
    SubjectAlternativeName,
    IPAddress,
    DNSName,
    Certificate,
    Name,
    NameAttribute,
    CertificateBuilder,
    BasicConstraints,
    KeyUsage,
    AuthorityKeyIdentifier,
)
from cryptography.x509.base import _AllowedHashTypes
from pydantic import HttpUrl

from core.helpers import SerialInfoHelper, CRLHelper
from core.mixins import ClassNameReprMixin
from core.settings import settings
from core.io_utils import write_certificates, load_certificate, write_private_key, load_private_key

IP_V4_PATTERN = re_compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")

logger = getLogger(__name__)

type PrivateKeyPath = Path
type CertificatePath = Path
type CertificateChainPath = Path


class BaseEditor(ClassNameReprMixin):
    def __init__(
        self,
        private_key_file: Path,
        certificate_file: Path,
        password: bytes | None = None,
        backend: Backend = settings.backend,
        valid_days: int = settings.root_ca.valid_days,
        *,
        public_exponent: int = settings.public_exponent,
        key_size: int = settings.key_size,
        hash_algorithm: _AllowedHashTypes = settings.hash_algorithm,
    ) -> None:
        self.private_key_file = private_key_file
        self.certificate_file = certificate_file

        self.password = password
        self.backend = backend
        self.valid_days = valid_days

        self.private_key: PrivateKeyTypes | None = None
        self.certificate: Certificate | None = None
        self.subject: Name | None = None

        self.public_exponent = public_exponent
        self.key_size = key_size
        self.hash_algorithm = hash_algorithm

    def load_private_key(self) -> PrivateKeyTypes | None:
        if not self.private_key_file.exists():
            return None

        self.private_key = load_private_key(
            self.private_key_file,
            self.backend,
            self.password,
        )
        return self.private_key

    def load_certificate(self) -> Certificate | None:
        if not self.certificate_file.exists():
            return None

        self.certificate = load_certificate(self.certificate_file, self.backend)
        self.subject = self.certificate.subject
        return self.certificate

    def gen_private_key(self) -> Path:
        self.private_key = rsa.generate_private_key(
            public_exponent=self.public_exponent,
            key_size=self.key_size,
        )

        return write_private_key(self.private_key, self.private_key_file)

    def make_subject(self, *args, **kwargs) -> Name:
        raise NotImplementedError

    def make_certificate(self, *args, **kwargs) -> Certificate:
        raise NotImplementedError


class RootCA(BaseEditor):
    def __init__(
        self,
        private_key_file: Path = settings.root_ca.private_key_file,
        certificate_file: Path = settings.root_ca.certificate_file,
        password: bytes | None = None,
        backend: Backend = settings.backend,
        valid_days: int = settings.root_ca.valid_days,
        *,
        public_exponent: int = settings.public_exponent,
        key_size: int = settings.key_size,
        hash_algorithm: _AllowedHashTypes = settings.hash_algorithm,
    ) -> None:
        super().__init__(
            private_key_file,
            certificate_file,
            password,
            backend,
            valid_days,
            public_exponent=public_exponent,
            key_size=key_size,
            hash_algorithm=hash_algorithm,
        )

    def make_subject(
        self,
        country_name: str,
        organization_name: str,
        common_name: str,
    ) -> Name:
        self.subject = Name(
            [
                NameAttribute(NameOID.COUNTRY_NAME, country_name),
                NameAttribute(NameOID.ORGANIZATION_NAME, organization_name),
                NameAttribute(NameOID.COMMON_NAME, common_name),
            ]
        )

        logger.info("Made root CA subject %r", self.subject)

        return self.subject

    def make_certificate(self) -> Certificate:
        if not self.subject:
            logger.error("Subject is not set")
            exit(1)

        if not self.private_key:
            logger.error("Private key is not found")
            exit(1)

        self.certificate = (
            CertificateBuilder()
            .subject_name(self.subject)
            .issuer_name(self.subject)
            .public_key(self.private_key.public_key())
            .serial_number(1)
            .not_valid_before(datetime.now(UTC) - timedelta(days=1))
            .not_valid_after(datetime.now(UTC) + timedelta(days=self.valid_days))
            .add_extension(BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(
                KeyUsage(
                    key_cert_sign=True,
                    crl_sign=True,
                    digital_signature=False,
                    key_encipherment=False,
                    key_agreement=False,
                    content_commitment=False,
                    data_encipherment=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(self.private_key, self.hash_algorithm)
        )
        write_certificates(self.certificate, file_path=self.certificate_file)

        logger.info(
            "Made root CA certificate %r: %r",
            self.certificate,
            self.private_key_file.absolute().as_posix(),
        )

        return self.certificate

    def gen_private_key(self) -> Path:
        private_key_path = super().gen_private_key()

        logger.info(
            "Made root CA private key %r",
            private_key_path.absolute().as_posix(),
        )

        return private_key_path


class IntimidateCA(BaseEditor, SerialInfoHelper, CRLHelper):
    def __init__(
        self,
        private_key_file: Path = settings.intermediate_ca.private_key_file,
        certificate_file: Path = settings.intermediate_ca.certificate_file,
        crl_file: Path = settings.intermediate_ca.crl_file,
        serial_file: Path = settings.intermediate_ca.serial_file,
        password: bytes | None = None,
        backend: Backend = settings.backend,
        valid_days: int = settings.intermediate_ca.valid_days,
        crl_update_period_days: int = settings.intermediate_ca.crl_update_period_days,
        *,
        public_exponent: int = settings.public_exponent,
        key_size: int = settings.key_size,
        hash_algorithm: _AllowedHashTypes = settings.hash_algorithm,
    ) -> None:
        BaseEditor.__init__(
            self,
            private_key_file,
            certificate_file,
            password,
            backend,
            valid_days,
            public_exponent=public_exponent,
            key_size=key_size,
            hash_algorithm=hash_algorithm,
        )
        SerialInfoHelper.__init__(self, serial_file=serial_file)
        CRLHelper.__init__(
            self,
            crl_file=crl_file,
            crl_update_period_days=crl_update_period_days,
            hash_algorithm=hash_algorithm,
            backend=backend,
        )

    def gen_private_key(self) -> Path:
        private_key_path = super().gen_private_key()

        logger.info(
            "Made intimidate CA private key %r",
            private_key_path.absolute().as_posix(),
        )

        return private_key_path

    def make_subject(
        self,
        country_name: str,
        organization_name: str,
        common_name: str,
    ) -> Name:
        self.subject = Name(
            [
                NameAttribute(NameOID.COUNTRY_NAME, country_name),
                NameAttribute(NameOID.ORGANIZATION_NAME, organization_name),
                NameAttribute(NameOID.COMMON_NAME, common_name),
            ]
        )

        logger.info("Made intimidate CA subject %r", self.subject)

        return self.subject

    def make_certificate(
        self,
        root_private_key: PrivateKeyTypes,
        root_certificate: Certificate,
    ) -> Certificate:
        if not self.subject:
            logger.error("Subject is not set")
            exit(1)

        if not self.private_key:
            logger.error("Private key is not found")
            exit(1)

        self.certificate = (
            CertificateBuilder()
            .subject_name(self.subject)
            .issuer_name(root_certificate.subject)
            .public_key(self.private_key.public_key())
            .serial_number(1)
            .not_valid_before(datetime.now(UTC) - timedelta(days=1))
            .not_valid_after(datetime.now(UTC) + timedelta(days=self.valid_days))
            .add_extension(BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(
                KeyUsage(
                    key_cert_sign=True,
                    crl_sign=True,
                    digital_signature=False,
                    key_encipherment=False,
                    key_agreement=False,
                    content_commitment=False,
                    data_encipherment=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(root_private_key, self.hash_algorithm)
        )

        write_certificates(self.certificate, file_path=self.certificate_file)

        logger.info(
            "Made intimidate CA certificate %r: %r",
            self.certificate,
            self.private_key_file.absolute().as_posix(),
        )

        return self.certificate


class ServerCertsEditor(ClassNameReprMixin):
    def __init__(
        self,
        intermediate_ca: IntimidateCA,
        crl_server_url: HttpUrl = settings.intermediate_ca.crl_server.url,
        certs_dir: Path = settings.server_certs.data_dir,
        valid_days: int = settings.server_certs.valid_days,
        *,
        public_exponent: int = settings.public_exponent,
        key_size: int = settings.key_size,
        hash_algorithm: _AllowedHashTypes = settings.hash_algorithm,
    ) -> None:
        self.intermediate_ca = intermediate_ca

        if not self.intermediate_ca.certificate or not self.intermediate_ca.private_key:
            logger.error("Intermediate CA: don`t have certificate or private key")
            exit(1)

        self.crl_server_url = crl_server_url
        self.certs_dir = certs_dir
        self.valid_days = valid_days

        self.public_exponent = public_exponent
        self.key_size = key_size
        self.hash_algorithm = hash_algorithm

        self.crl_distribution_points: CRLDistributionPoints | None = None

    def gen_private_key(self, name: str) -> type[PrivateKeyTypes, Path]:
        file_path = self.certs_dir / f"{name}.key"

        private_key = rsa.generate_private_key(
            public_exponent=self.public_exponent,
            key_size=self.key_size,
        )

        write_private_key(private_key, file_path)

        logger.info(
            "Made %r server private key %r",
            name,
            file_path.absolute().as_posix(),
        )

        return private_key, file_path

    def make_crl_distribution_points(
        self,
        crl_server_host: str | None = None,
        crl_server_port: int | None = None,
        *,
        scheme: str = settings.intermediate_ca.crl_server.scheme,
        route: str = settings.intermediate_ca.crl_server.route,
    ) -> CRLDistributionPoints:
        if not crl_server_host or not crl_server_port:
            crl_server_url = self.crl_server_url
        else:
            crl_server_url = HttpUrl.build(
                scheme=scheme,
                host=crl_server_host,
                port=crl_server_port,
                path=route,
            )

        self.crl_distribution_points = CRLDistributionPoints(
            [
                DistributionPoint(
                    full_name=[
                        UniformResourceIdentifier(
                            crl_server_url.encoded_string(),
                        ),
                    ],
                    relative_name=None,
                    reasons=None,
                    crl_issuer=None,
                )
            ]
        )

        logger.info(
            "Made server crl distribution points %r",
            self.crl_distribution_points,
        )

        return self.crl_distribution_points

    @classmethod
    def make_subject(cls, common_name: str) -> Name:
        subject = Name(
            [
                NameAttribute(NameOID.COMMON_NAME, common_name),
            ]
        )

        logger.info(
            "Made %r server subject %r",
            common_name,
            subject,
        )

        return subject

    @classmethod
    def make_san(cls, common_name: str, alt_names: Iterable[str]) -> SubjectAlternativeName:
        names = []

        for alt_name in alt_names:
            alt_name = alt_name.strip()

            if re_match(IP_V4_PATTERN, alt_name):
                names.append(IPAddress(IPv4Address(alt_name)))
            else:
                names.append(DNSName(alt_name))

        san = SubjectAlternativeName(names)

        logger.info(
            "Made %r server SAN %r",
            common_name,
            san,
        )

        return san

    def make_certificate(
        self,
        name: str,
        server_private_key: PrivateKeyTypes,
        server_subject: Name,
        san: SubjectAlternativeName,
    ) -> tuple[Certificate, CertificatePath, CertificateChainPath]:
        certificate_file = self.certs_dir / f"{name}.crt"
        chain_file = self.certs_dir / f"{name}-chain.crt"

        serial_number = self.intermediate_ca.next_serial_num

        certificate = (
            CertificateBuilder()
            .subject_name(server_subject)
            .issuer_name(self.intermediate_ca.certificate.subject)
            .public_key(server_private_key.public_key())
            .serial_number(serial_number)
            .not_valid_before(datetime.now(UTC) - timedelta(days=1))
            .not_valid_after(datetime.now(UTC) + timedelta(days=self.valid_days))
            .add_extension(BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    key_cert_sign=False,
                    crl_sign=False,
                    key_agreement=False,
                    content_commitment=False,
                    data_encipherment=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(san, critical=False)
            .add_extension(
                AuthorityKeyIdentifier.from_issuer_public_key(
                    self.intermediate_ca.private_key.public_key()
                ),
                critical=False,
            )
            .add_extension(self.crl_distribution_points, critical=False)
            .sign(self.intermediate_ca.private_key, self.hash_algorithm)
        )

        write_certificates(certificate, file_path=certificate_file)
        write_certificates(certificate, self.intermediate_ca.certificate, file_path=chain_file)

        self.intermediate_ca.save_to_serial_file(
            serial_number,
            certificate.fingerprint(self.hash_algorithm).hex(),
        )

        logger.info(
            "Made %r server certificate %r: %r",
            name,
            certificate,
            certificate_file.absolute().as_posix(),
        )

        return certificate, certificate_file, chain_file


def make_server_pki(
    server_certs_editor: ServerCertsEditor,
    common_name: str,
    alt_names: Iterable[str],
    crl_server_host: str,
    crl_server_port: int,
) -> tuple[
    tuple[PrivateKeyTypes, PrivateKeyPath],
    tuple[Certificate, CertificatePath, CertificateChainPath],
]:
    if server_certs_editor.crl_distribution_points is None:
        server_certs_editor.make_crl_distribution_points(crl_server_host, crl_server_port)

    private_key, private_key_file = server_certs_editor.gen_private_key(common_name)

    subject = server_certs_editor.make_subject(common_name)
    san = server_certs_editor.make_san(common_name, alt_names)

    certificate, certificate_file, chain_file = server_certs_editor.make_certificate(
        common_name,
        private_key,
        subject,
        san,
    )

    return (private_key, private_key_file), (certificate, certificate_file, chain_file)
