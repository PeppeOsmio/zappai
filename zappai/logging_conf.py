from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
import logging
import logging.handlers
import os
from pathlib import Path
from typing import Any, cast
from pydantic import BaseModel, Field, ByteSize


class BetterDateTimeFormatter(logging.Formatter):
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    DEFAULT_FMT = '%(asctime)s | %(levelname)s | %(process)d | "%(pathname)s:%(lineno)d" in %(funcName)s | %(message)s'

    def __init__(
        self,
        fmt: str | None,
        datefmt: str | None,
        timezone: timezone = timezone.utc,
    ):
        super().__init__(
            fmt=fmt or BetterDateTimeFormatter.DEFAULT_FMT,
            datefmt=(
                datefmt if datefmt is not None else BetterDateTimeFormatter.ISO_FORMAT
            ),
        )
        self.timezone = timezone

    def formatTime(self, record, datefmt=None):
        return datetime.fromtimestamp(record.created, tz=self.timezone).strftime(
            cast(str, self.datefmt)
        )


class LogLevelEnum(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LoggingHelperConfig(BaseModel):
    filename: str
    level: LogLevelEnum = Field(default="info")
    max_bytes: ByteSize = Field(default="10MiB")
    retention: int = Field(default=7)
    datefmt: str | None = Field(default=BetterDateTimeFormatter.ISO_FORMAT)
    fmt: str | None = Field(default=BetterDateTimeFormatter.DEFAULT_FMT)
    log_also_to_stdout: bool = Field(default=False)


def create_logger(
    config: LoggingHelperConfig, logger_name: str | None = None
) -> logging.Logger:
    logger = logging.getLogger(name=logger_name)
    logger.handlers.clear()
    logger.setLevel(config.level.value.upper())

    formatter = BetterDateTimeFormatter(fmt=config.fmt, datefmt=config.datefmt)

    os.makedirs(str(Path(config.filename).parent), exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=config.filename,
        maxBytes=config.max_bytes,
        backupCount=config.retention,
    )
    file_handler.setFormatter(formatter)
    logger.handlers.append(file_handler)

    if config.log_also_to_stdout:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.handlers.append(stream_handler)

    return logger


def get_default_conf() -> LoggingHelperConfig:
    dict_read_from_file = {
        "filename": "logs/zappai.log",
        # "debug", "info", "warning", "error", "critical"
        "level": "info",
        # e.g. "10MiB", "10MB", "3KB"
        "max_bytes": "10MiB",
        "retention": 7,
        # datefmt can be omitted or None and defaults to the following (ISO format)
        # info about the syntax of datetime formats here, since this package uses datetime's syntax instead of logging's
        # for datetimes
        # https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
        "datefmt": "%Y-%m-%dT%H:%M:%S.%fZ",
        # fmt can be omitted or None and default to the following
        # info about the fields and syntax of logs here
        # https://docs.python.org/3/library/logging.html#logrecord-attributes
        "fmt": '%(asctime)s | %(levelname)s | %(process)d | "%(pathname)s:%(lineno)d" in %(funcName)s | %(message)s',
        "log_also_to_stdout": True,
    }

    return LoggingHelperConfig(
        filename=dict_read_from_file["filename"],
        level=dict_read_from_file["level"],
        max_bytes=dict_read_from_file["max_bytes"],
        retention=dict_read_from_file["retention"],
        datefmt=dict_read_from_file["datefmt"],
        fmt=dict_read_from_file["fmt"],
        log_also_to_stdout=dict_read_from_file["log_also_to_stdout"],
    )

    create_logger
