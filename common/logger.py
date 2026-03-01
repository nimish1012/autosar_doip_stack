import logging

def setup_logger(name: str) -> logging.Logger:
    """
    Configure and return a logger instance.

    Responsibilities of the Common module:
    - Provide shared utilities, logging, and configuration across all layers.
    - Ensure consistent logging format and level.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger
