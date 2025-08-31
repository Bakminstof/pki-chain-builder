__all__ = ("settings",)

from logging import getLogger
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.backends.openssl.backend import Backend
from cryptography.hazmat.primitives.hashes import HashAlgorithm, SHA256
from pydantic import computed_field, BaseModel, field_validator, ConfigDict, HttpUrl
from pydantic_settings import BaseSettings
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    NoEncryption,
    KeySerializationEncryption,
)

from core.common import get_ip

BASE_DIR = Path(__file__).resolve().parent.parent
DIR_FIELDS = ["certs_data_dir", "data_dir", "revoked_certs_dir"]

logger = getLogger(__name__)


class DirsValidatorsModelMixin(BaseModel):
    @field_validator(*DIR_FIELDS, mode="before", check_fields=False)  # noqa
    @classmethod
    def data_dir_validator(cls, value: Path) -> Path:
        if not value.exists():
            value.mkdir(parents=True, exist_ok=True)

            logger.debug(
                "Created %r",
                value.absolute().as_posix(),
            )

        return value


class RootCASettings(DirsValidatorsModelMixin):
    model_config = ConfigDict(validate_default=True)

    certs_data_dir: Path = BASE_DIR.parent / "certs"
    data_dir: Path = certs_data_dir / "root"

    private_key_file: Path = data_dir / "root.key"
    certificate_file: Path = data_dir / "root.crt"

    valid_days: int = 7300


class CRLServerSettings(BaseModel):
    crl_file: Path

    scheme: str = "http"
    host: str = get_ip()
    port: int = 11080

    refresh_revoked_dir_time_seconds: int = 60

    @computed_field
    @property
    def route(self) -> str:
        return f"/crl/{self.crl_file.name}"

    @computed_field
    @property
    def url(self) -> HttpUrl:
        return HttpUrl.build(
            scheme=self.scheme,
            host=self.host,
            port=self.port,
            path=self.route,
        )


class IntermediateCASettings(DirsValidatorsModelMixin):
    model_config = ConfigDict(validate_default=True)

    certs_data_dir: Path = BASE_DIR.parent / "certs"
    data_dir: Path = certs_data_dir / "intermediate"

    private_key_file: Path = data_dir / "intermediate.key"
    certificate_file: Path = data_dir / "intermediate.crt"

    revoked_certs_dir: Path = data_dir / "revoked"

    serial_file: Path = data_dir / "serial.json"

    crl_file: Path = data_dir / "intermediate.crl"
    crl_update_period_days: int = 1

    crl_server: CRLServerSettings = CRLServerSettings(crl_file=crl_file)

    valid_days: int = 7300


class ServerCertsSettings(DirsValidatorsModelMixin):
    model_config = ConfigDict(validate_default=True)

    certs_data_dir: Path = BASE_DIR.parent / "certs"
    data_dir: Path = certs_data_dir / "server"

    valid_days: int = 3650


class Settings(BaseSettings, DirsValidatorsModelMixin):
    model_config = ConfigDict(validate_default=True)

    base_dir: Path = BASE_DIR

    certs_data_dir: Path = base_dir.parent / "certs"

    public_exponent: int = 65537
    key_size: int = 4096

    file_encoding: str = "UTF-8"
    certs_encoding: Encoding = Encoding.PEM

    private_format: PrivateFormat = PrivateFormat.TraditionalOpenSSL

    backend: Backend = default_backend()

    encryption_algorithm: KeySerializationEncryption = NoEncryption()
    hash_algorithm: HashAlgorithm = SHA256()

    root_ca: RootCASettings = RootCASettings(certs_data_dir=certs_data_dir)
    intermediate_ca: IntermediateCASettings = IntermediateCASettings(certs_data_dir=certs_data_dir)
    server_certs: ServerCertsSettings = ServerCertsSettings(certs_data_dir=certs_data_dir)


settings = Settings()
