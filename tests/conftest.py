import logging

import pytest


@pytest.fixture(autouse=True)
def clean_root_logger():
    """setup_logging() mutates the global root logger; undo that after every test
    so handlers/levels from one test don't leak into the next."""
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    yield

    for handler in list(root_logger.handlers):
        if handler not in original_handlers:
            root_logger.removeHandler(handler)
    root_logger.setLevel(original_level)
