from logging import getLogger
from pathlib import Path
from typing import TypeVar

from cryptography.hazmat.backends.openssl.backend import Backend
from cryptography.hazmat.primitives._serialization import (
    Encoding,
    PrivateFormat,
    KeySerializationEncryption,
)
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import (
    CertificateRevocationList,
    Certificate,
    load_pem_x509_crl,
    load_pem_x509_certificate,
)

from pydantic import BaseModel

from core.settings import settings

M = TypeVar("M", bound=BaseModel)
logger = getLogger(__name__)


def write_bytes(data: bytes, file_path: Path) -> Path:
    with file_path.open("wb") as f:
        f.write(data)
        return file_path


def read_bytes(file_path: Path) -> bytes:
    with file_path.open("rb") as f:
        return f.read()


def load_json_as_model(
    file_path: Path,
    model_cls: type[M],
    encoding: str = settings.file_encoding,
) -> M:
    with file_path.open(encoding=encoding) as f:
        model = model_cls.model_validate_json(f.read())

        logger.debug(
            "Loaded %r from %r",
            model_cls,
            file_path.absolute().as_posix(),
        )

        return model


def write_model_as_json(
    file_path: Path,
    model: M,
    indent: int = 4,
    encoding: str = settings.file_encoding,
) -> Path:
    with file_path.open("w", encoding=encoding) as f:
        f.write(model.model_dump_json(indent=indent))

        logger.debug(
            "Saved %r to %r",
            type(model),
            file_path.absolute().as_posix(),
        )

        return file_path


def write_public_bytes(
    item: CertificateRevocationList | Certificate,
    file_path: Path,
    encoding: Encoding = settings.certs_encoding,
) -> Path:
    data = item.public_bytes(encoding)
    return write_bytes(data, file_path)


def write_certificate(
    certificate: Certificate,
    file_path: Path,
    encoding: Encoding = settings.certs_encoding,
) -> Path:
    write_public_bytes(certificate, file_path, encoding)

    logger.debug(
        "Saved %r to %r",
        certificate,
        file_path.absolute().as_posix(),
    )

    return file_path


def write_crl(
    crl: CertificateRevocationList,
    file_path: Path,
    encoding: Encoding = settings.certs_encoding,
) -> Path:
    write_public_bytes(crl, file_path, encoding)

    logger.debug(
        "Saved %r to %r",
        crl,
        file_path.absolute().as_posix(),
    )

    return file_path


def load_crl(
    file_path: Path,
    backend: Backend,
) -> CertificateRevocationList:
    data = read_bytes(file_path)
    crl = load_pem_x509_crl(data, backend)

    logger.debug(
        "Loaded %r from %r",
        crl,
        file_path.absolute().as_posix(),
    )

    return crl


def load_certificate(
    file_path: Path,
    backend: Backend,
) -> Certificate:
    data = read_bytes(file_path)
    certificate = load_pem_x509_certificate(data, backend)

    logger.debug(
        "Loaded %r from %r",
        certificate,
        file_path.absolute().as_posix(),
    )

    return certificate


def write_private_key(
    private_key: RSAPrivateKey,
    file_path: Path,
    encoding: Encoding = settings.certs_encoding,
    private_format: PrivateFormat = settings.private_format,
    encryption_algorithm: KeySerializationEncryption = settings.encryption_algorithm,
) -> Path:
    data = private_key.private_bytes(
        encoding=encoding,
        format=private_format,
        encryption_algorithm=encryption_algorithm,
    )
    write_bytes(data, file_path)

    logger.debug(
        "Saved %r to %r",
        private_key,
        file_path.absolute().as_posix(),
    )

    return file_path


def load_private_key(
    file_path: Path,
    backend: Backend,
    password: bytes | None = None,
) -> RSAPrivateKey:
    data = read_bytes(file_path)
    private_key = load_pem_private_key(data, password, backend)

    logger.debug(
        "Loaded %r from %r",
        private_key,
        file_path.absolute().as_posix(),
    )

    return private_key
