"""
Logging configuration for the application
"""

import logging
import sys
from datetime import datetime


def setup_logging(level: str = "INFO"):
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"app_{datetime.now().strftime('%Y%m%d')}.log"),
        ],
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
