from pydantic import BaseModel


class Args(BaseModel):
    root_ca_c: str | None = None
    root_ca_o: str | None = None
    root_ca_cn: str | None = None

    intermediate_ca_c: str | None = None
    intermediate_ca_o: str | None = None
    intermediate_ca_cn: str | None = None

    server_cn: str | None = None
    server_san: str | None = None
    crl_server_host: str | None = None
    crl_server_port: int | None = None

    debug: bool = False


type SerialNumber = int


class CertInfo(BaseModel):
    sha_256_fingerprint: str

    revoked: bool = False
    revocation_timestamp: float | None = None


class SerialCertsInfoModel(BaseModel):
    data: dict[SerialNumber, CertInfo] = {}


class CASubject(BaseModel):
    country_name: str
    organization_name: str
    common_name: str
