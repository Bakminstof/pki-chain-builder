from pathlib import Path

from pydantic import BaseModel


class Args(BaseModel):
    host: str | None = None
    port: int | None = None
    crl_file: Path | None = None
    debug: bool = False
