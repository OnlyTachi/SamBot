import logging
from logging.handlers import RotatingFileHandler
import os
import sys


class Logger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self):
        self.logger = logging.getLogger("SamBot")
        self.logger.setLevel(logging.INFO)

        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(module)-15s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Garantir que a pasta de logs existe
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        max_bytes = 5 * 1024 * 1024
        backup_count = 3

        general_file = os.path.join(log_dir, "sambot_general.log")
        general_handler = RotatingFileHandler(
            general_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        general_handler.setLevel(logging.INFO)
        general_handler.setFormatter(formatter)
        self.logger.addHandler(general_handler)

        error_file = os.path.join(log_dir, "sambot_errors.log")
        error_handler = RotatingFileHandler(
            error_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)  # Filtra para só salvar ERROR ou CRITICAL
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def debug(self, message):
        self.logger.debug(message)

    def critical(self, message):
        self.logger.critical(message)
