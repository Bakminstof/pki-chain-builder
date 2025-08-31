__all__ = ("setup_logging",)

from logging import getLogger

from logging.config import dictConfig
from queue import Queue
from typing import Any

from .settings import LoggingSettings


logger = getLogger(__name__)


def setup_logging(log_settings: LoggingSettings) -> dict:
    if log_settings.coloring_output:
        from colorama import init

        init(autoreset=True)

    handlers = get_handlers(log_settings)
    formatters = get_formatters(log_settings)
    dict_config = get_dict_config(log_settings, handlers, formatters)

    dictConfig(dict_config)

    if log_settings.loki_handler:
        from logging_loki import LokiQueueHandler

        loki_logs_handler = LokiQueueHandler(
            Queue(-1),
            url=log_settings.loki_url,
            tags=log_settings.loki_tags,
            version=log_settings.loki_version,
            auth=log_settings.loki_auth,
        )

        root_logger = getLogger()
        root_logger.addHandler(loki_logs_handler)

        logger.debug("Added Loki handler")

    if log_settings.loglevel == "DEBUG":
        logger.warning("Debug mode on")

    return dict_config


def get_formatters(logging_settings: LoggingSettings) -> dict:
    return {
        "base": {
            "format": logging_settings.log_format,
            "datefmt": logging_settings.log_datetime_format,
        },
        "colour": {
            "()": "logging_settings.formatters.ColourFormatter",
            "fmt": logging_settings.log_format,
            "datefmt": logging_settings.log_datetime_format,
        },
    }


def get_handlers(logging_settings: LoggingSettings) -> dict:
    return {
        "console": {
            "class": "logging.StreamHandler",
            "level": logging_settings.loglevel,
            "formatter": "colour" if logging_settings.coloring_output else "base",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": logging_settings.loglevel,
            "mode": "a",
            "formatter": "base",
            "maxBytes": logging_settings.max_bytes,
            "backupCount": logging_settings.backup_count,
            "filename": logging_settings.filename,
            "encoding": logging_settings.encoding,
        },
    }


def get_dict_config(
    logging_settings: LoggingSettings,
    handlers: dict[str, str],
    formatters: dict[str, str],
) -> dict[str, Any]:
    if not logging_settings.rotating_file_handler:
        handlers.pop("file", None)

    handlers_names = [name for name in handlers.keys()]

    return {
        "version": logging_settings.version,
        "encoding": logging_settings.encoding,
        "disable_existing_loggers": logging_settings.disable_existing_loggers,
        "formatters": formatters,
        "handlers": handlers,
        "root": {
            "level": logging_settings.loglevel,
            "handlers": handlers_names,
        },
    }
