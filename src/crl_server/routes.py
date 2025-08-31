from bottle import response

import core.io_utils
from core.settings import settings


def crl() -> bytes:
    crl_file = settings.intermediate_ca.crl_file
    response.content_type = "application/pem-certificate-chain"
    response.headers["Content-Disposition"] = f"inline; filename={crl_file.name}"
    return core.io_utils.read_bytes()
