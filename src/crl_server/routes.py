from bottle import response
from core.io_utils import read_bytes

from core.settings import settings


def crl() -> bytes:
    crl_file = settings.intermediate_ca.crl_file
    response.content_type = "application/pem-certificate-chain"
    response.headers["Content-Disposition"] = f"inline; filename={crl_file.name}"
    return read_bytes(crl_file)
