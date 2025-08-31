from pathlib import Path
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
    HttpUrl,
)
from pydantic_core.core_schema import ValidationInfo


class LoggingSettings(BaseModel):
    model_config = ConfigDict(validate_default=True)

    version: int = 1
    disable_existing_loggers: bool = False
    encoding: str = "UTF-8"

    add_timestamp: bool = True
    add_logger_name: bool = True

    loglevel: str = "INFO"
    log_format: str | None = None

    @field_validator("loglevel", mode="before")
    @classmethod
    def loglevel_validator(
        cls,
        value: str,
    ) -> str:
        return value.upper()

    @field_validator("log_format", mode="before")
    @classmethod
    def log_format_validator(
        cls,
        value: str | None,
        info: ValidationInfo,
    ) -> str:
        if value:
            return value

        timestamp = " | %(asctime)s" if info.data.get("add_timestamp") else ""
        logger_name = " | %(name)s" if info.data.get("add_logger_name") else ""

        return f"%(levelname)s{timestamp}{logger_name} | %(message)s"

    log_datetime_format: str = "%Y-%m-%d %H:%M:%S"

    coloring_output: bool = True

    rotating_file_handler: bool = False
    logs_dir: Path | str | None = None
    filename: str = "app.log"
    max_bytes: int = 20_971_520
    backup_count: int = 20

    @field_validator("logs_dir", mode="before")
    @classmethod
    def logs_dir_validator(
        cls,
        value: str | Path,
        info: ValidationInfo,
    ) -> Path | None:
        if not info.data.get("rotating_file_handler"):
            return None

        if info.data.get("rotating_file_handler") and not value:
            raise ValueError("If `rotating_file_handler` set, `logs_dir` must be provided")

        if isinstance(value, str):
            logs_dir = Path(value)
        else:
            logs_dir = value

        if not logs_dir.exists():
            logs_dir.mkdir(exist_ok=True, parents=True)

        return logs_dir

    @field_validator("filename", mode="after")
    @classmethod
    def filename_validator(
        cls,
        value: str,
        info: ValidationInfo,
    ) -> str | None:
        if not info.data.get("rotating_file_handler"):
            return None

        logs_dir = info.data.get("logs_dir")

        if not logs_dir:
            raise ValueError("`logs_dir` must be provided")

        log_filename_path: Path = info.data["logs_dir"] / value

        return log_filename_path.absolute().as_posix()

    loki_handler: bool = False
    loki_tags: dict[str, str] = {}
    loki_url: str | HttpUrl | None = None
    loki_version: str | None = None
    loki_auth: Any | None = None

    @field_validator("loki_tags", "loki_url", "loki_version", mode="after")
    @classmethod
    def loki_validator(
        cls,
        value: Any,
        info: ValidationInfo,
    ) -> Any:
        if not info.data.get("loki_handler"):
            return None

        if info.data.get("loki_handler") and not value:
            raise ValueError(
                "If `loki_handler` set, `loki_tags`, `loki_url`, `loki_version` must be provided"
            )

        return value

    @field_validator("loki_url", mode="after")
    @classmethod
    def loki_url_validator(
        cls,
        value: str | HttpUrl | None,
        info: ValidationInfo,
    ) -> str | None:
        if not info.data.get("loki_handler"):
            return None

        if isinstance(value, HttpUrl):
            return value.unicode_string()

        if isinstance(value, str):
            return HttpUrl(value).unicode_string()
