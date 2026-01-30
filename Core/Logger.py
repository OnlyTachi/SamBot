import logging
import sys
import os
from datetime import datetime

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
        
        # Evita duplicidade de handlers se re-inicializado
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Formato do log
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(module)-15s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler para Console (Stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Handler para Arquivo (opcional, cria pasta logs se não existir)
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"sambot_{datetime.now().strftime('%Y-%m-%d')}.log"),
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

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

    def get_logger(self):
        return self.logger
    # eu poderia ter removido o método get_logger e usado self.logger diretamente, mas deixei assim para manter a interface limpa... ou preguiça mesmo kkk