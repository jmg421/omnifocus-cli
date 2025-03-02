import logging

def setup_logging(level=logging.INFO):
    """
    Configures Python's logging module with a basic format.
    Call this in main if desired.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

