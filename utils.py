import logging
import logging.handlers
import os

PORJ_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PORJ_DIR, "analysis")


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
    # auto create dir if not exists
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    # 1M max size, 2 backup files
    handler = logging.handlers.RotatingFileHandler(
        log_file_path, maxBytes=1 * 1024 * 1024, backupCount=2
    )
    formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
