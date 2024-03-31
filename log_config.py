import logging
import logging.handlers
import os


def setup_logging():

    logger = logging.getLogger()  # set global root logger
    logger.setLevel(logging.INFO)

    # avoid adding multiple handlers
    while logger.handlers:
        handler = logger.handlers[0]
        # close before removing
        handler.close()
        logger.removeHandler(handler)

    # get current dir/logs/outpost.log
    log_file_path = os.path.join(
        os.path.dirname(__file__), "logs", "outpost.log"
    )
    # 1M max size, 2 backup files
    handler = logging.handlers.RotatingFileHandler(
        log_file_path, maxBytes=1 * 1024 * 1024, backupCount=2
    )
    formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
