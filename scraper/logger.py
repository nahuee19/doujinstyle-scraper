# File: logger.py
# Author: Urpagin
# Date: 2025-08-15
# License: MIT

import logging


def setup_logger() -> logging.Logger:
    """Creates the app's logger."""
    # Our own logger.
    # Change this to logging.WARNING to not bother with all the debug logging.
    logger: logging.Logger = logging.getLogger('scraper')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(name)-15s] [%(levelname)-8s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)
    return logger


# Create one logger instance for the whole app.
log: logging.Logger = setup_logger()
