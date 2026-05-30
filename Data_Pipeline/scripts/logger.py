"""
Data_Pipeline/scripts/logger.py

Shared logger for the data pipeline.
Uses Airflow's logging system when available,
falls back to standard Python logging otherwise.
"""

import logging
import sys

formatter = logging.Formatter(
    "[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)


class Logger:
    """
    Logger that uses Airflow's LoggingMixin when running inside Airflow,
    and falls back to standard Python logging otherwise.
    """

    def __init__(self, name: str = "SupplyChainForecasting"):
        self._standard_logger = logging.getLogger(name)
        self._standard_logger.setLevel(logging.INFO)

        if not self._standard_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            self._standard_logger.addHandler(handler)

        try:
            from airflow.utils.log.logging_mixin import LoggingMixin
            self._airflow_logger = LoggingMixin().log
            self._use_airflow = True
        except ImportError:
            self._use_airflow = False

    def _get_logger(self):
        return self._airflow_logger if self._use_airflow else self._standard_logger

    def info(self, msg, *args, **kwargs):
        self._get_logger().info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._get_logger().warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._get_logger().error(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._get_logger().debug(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self._get_logger().critical(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self._get_logger().exception(msg, *args, **kwargs)

    def setLevel(self, level):
        """Set logging level by name or logging constant."""
        if isinstance(level, str):
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL,
            }
            level = level_map.get(level.upper(), logging.INFO)
        self._standard_logger.setLevel(level)


# Single instance imported by all other modules
logger = Logger()
