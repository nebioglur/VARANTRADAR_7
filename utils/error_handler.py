import sys
import traceback
from utils.logger import logger

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Catch any unhandled exceptions globally and log them.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Kritik Hata (Uncaught exception)", exc_info=(exc_type, exc_value, exc_traceback))

# Set the global exception handler
sys.excepthook = global_exception_handler
