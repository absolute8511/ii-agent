import logging
import os

logging.basicConfig(level=logging.INFO)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("ii_agent")

if LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    logger.setLevel(LOG_LEVEL)

# Enable httpx logging to debug connection errors
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.DEBUG)
openapi_logger = logging.getLogger("openai")
openapi_logger.setLevel(logging.INFO)
