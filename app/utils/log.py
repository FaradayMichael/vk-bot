import logging
from logging.config import fileConfig
import os

logger = logging.getLogger(__name__)
LOG_ENV_KEY = "SRVC_LOG"

kafka_logger = logging.getLogger("aiokafka")
kafka_logger.setLevel(logging.CRITICAL)
for handler in kafka_logger.handlers:
    handler.setLevel(kafka_logger.level)

try:
    log_path = os.environ[LOG_ENV_KEY]
    if os.path.exists(log_path):
        fileConfig(log_path)
except:
    logger.error(f"Configuration file path not provided at environment [{LOG_ENV_KEY}]")
