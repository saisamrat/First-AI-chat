import logging
import logging.handlers
import os
import queue

from config import Config


def setup_logging(config: Config) -> logging.handlers.QueueListener:
    os.makedirs(os.path.dirname(config.logging_file_path), exist_ok=True)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = logging.FileHandler(config.logging_file_path)
    file_handler.setFormatter(formatter)

    log_queue: queue.Queue = queue.Queue(-1)
    queue_handler = logging.handlers.QueueHandler(log_queue)

    root_logger = logging.getLogger()
    root_logger.setLevel(config.logging_level)
    root_logger.addHandler(queue_handler)

    listener = logging.handlers.QueueListener(log_queue, file_handler)
    listener.start()

    return listener
